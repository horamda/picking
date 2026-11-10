"""Read-only operational projections from the existing versioned control state."""
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import joinedload, selectinload

from models import User
from services.assistance import helpers
from services.load_control import ControlTruck, court_state, elapsed, selected_loads, timing
from services.pallet_control import assembly_done, pallet_state, physical_pallets
from utils.db import db


def _date(value, field):
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValueError(f'{field} debe tener formato AAAA-MM-DD.') from None


def _check_running(check):
    return check.get('status') == 'active' and bool(check.get('timer_started_at'))


def _time_values(check):
    try:
        values = timing(check)
        return values['active_seconds'], values['paused_seconds']
    except (TypeError, ValueError):
        return None, None


def _load_progress(load):
    pallets = [item for item in physical_pallets(load.truck) if item['load_id'] == load.id]
    if pallets:
        done = sum(1 for item in pallets if assembly_done(load.truck, item))
        return done, len(pallets), 'pallets'
    required = []
    plan = load.truck.state.get('planning') or {}
    for item in plan.get('picking_tasks', []):
        if item.get('load_id') == load.id and (item.get('bultos', 0) or item.get('unidades', 0)):
            required.append((item.get('court'), 0))
    for item in plan.get('full_pallets', []):
        if item.get('load_id') == load.id and item.get('pallets', 0):
            required.append((item.get('court'), 4))
    if not required:
        required = [(court['numero'], 0) for court in load.content.get('canchas', []) if court.get('productos')]
    required = set(required)
    done = sum(1 for court, stage in required
               if court_state(load.truck.state, load.id, court)['checks'].get(str(stage), {}).get('status') == 'done')
    return done, len(required), 'tareas'


def _load_started(load):
    prefix = f'{load.id}:'
    if any(state.get('checks') or state.get('helpers')
           for key, state in load.truck.state.get('courts', {}).items() if key.startswith(prefix)):
        return True
    return any(key.startswith(prefix) and state.get('checks')
               for key, state in load.truck.state.get('pallet_controls', {}).items())


def _load_state(load):
    done, total, unit = _load_progress(load)
    if total and done == total:
        state = 'finalizado'
    elif done or _load_started(load):
        state = 'en_preparacion'
    else:
        state = 'pendiente'
    return state, done, total, unit


def _current_checks(truck):
    seen = set()
    for key, state in truck.state.get('courts', {}).items():
        try:
            load_id = int(key.split(':', 1)[0])
        except (ValueError, TypeError):
            continue
        for check in list(state.get('checks', {}).values()) + helpers(state):
            identity = check.get('id')
            if identity and identity not in seen:
                seen.add(identity)
                yield load_id, check
    for key, state in truck.state.get('pallet_controls', {}).items():
        try:
            load_id = int(key.split(':', 1)[0])
        except (ValueError, TypeError):
            continue
        for check in state.get('checks', {}).values():
            identity = check.get('id')
            if identity and identity not in seen:
                seen.add(identity)
                yield load_id, check
    check = truck.state.get('asset_check')
    if check and check.get('id') not in seen:
        yield None, check


def _answer_amount(answer):
    measurement = answer.get('measurement') or {}
    factor = measurement.get('units_per_case')
    bultos, unidades = answer.get('physical_b'), answer.get('physical_u')
    if type(bultos) not in (int, float) or type(unidades) not in (int, float):
        return None
    if unidades and (type(factor) not in (int, float) or factor <= 0):
        return None
    return float(bultos) + (float(unidades) / factor if unidades else 0)


def build_operations_dashboard(args):
    desde, hasta = _date(args.get('desde'), 'desde'), _date(args.get('hasta'), 'hasta')
    if desde and hasta and desde > hasta:
        raise ValueError('La fecha desde no puede ser posterior a la fecha hasta.')
    query = ControlTruck.query.options(selectinload(ControlTruck.loads))
    if desde:
        query = query.filter(ControlTruck.load_date >= desde)
    if hasta:
        query = query.filter(ControlTruck.load_date <= hasta)
    if args.get('sucursal'):
        query = query.filter(ControlTruck.branch == args['sucursal'])
    if args.get('camion'):
        query = query.filter(ControlTruck.truck == args['camion'])
    trucks = query.order_by(ControlTruck.load_date, ControlTruck.branch, ControlTruck.truck).all()

    reparto = str(args.get('reparto') or '').strip()
    operator = str(args.get('operario') or '').strip()
    operator_id = int(operator) if operator.isdigit() else None
    state_filter = str(args.get('estado') or '').strip()
    valid_states = {'pendiente', 'en_preparacion', 'finalizado'}
    if state_filter and state_filter not in valid_states:
        raise ValueError('Estado operativo inválido.')

    selected = []
    options = defaultdict(set)
    for truck in trucks:
        options['sucursales'].add(truck.branch)
        options['camiones'].add(truck.truck)
        for load in selected_loads(truck):
            options['repartos'].add(load.reparto)
            if reparto and load.reparto != reparto:
                continue
            state, done, total, unit = _load_state(load)
            if state_filter and state != state_filter:
                continue
            selected.append((truck, load, state, done, total, unit))

    selected_load_ids = {load.id for _, load, *_ in selected}
    selected_truck_ids = {truck.id for truck, *_ in selected}
    if operator_id:
        operator_loads = set()
        for truck in trucks:
            for load_id, check in _current_checks(truck):
                if check.get('user_id') == operator_id:
                    operator_loads.add(load_id)
        selected = [row for row in selected if row[1].id in operator_loads]
        selected_load_ids = {load.id for _, load, *_ in selected}
        selected_truck_ids = {truck.id for truck, *_ in selected}

    states = {key: 0 for key in valid_states}
    progress_done = progress_total = 0
    rows = []
    for truck, load, state, done, total, unit in selected:
        states[state] += 1
        progress_done += done
        progress_total += total
        rows.append(dict(id=load.id, fecha=truck.load_date, sucursal=truck.branch,
            camion=truck.truck, reparto=load.reparto, estado=state,
            avance=round(done / total * 100, 1) if total else None,
            completados=done, total=total, unidad=unit,
            liberada=bool(truck.state.get('released_at'))))

    active_users = set()
    prepared = 0.0
    measured_answers = total_answers = 0
    active_seconds = 0.0
    active_processes = 0
    for truck in trucks:
        if truck.id not in selected_truck_ids:
            continue
        for load_id, check in _current_checks(truck):
            if load_id is not None and load_id not in selected_load_ids:
                continue
            if operator_id and check.get('user_id') != operator_id:
                continue
            if _check_running(check):
                if check.get('user_id') is not None:
                    active_users.add(check.get('user_id'))
                active_processes += 1
            if check.get('stage') not in (0, 4):
                continue
            seconds, _ = _time_values(check)
            if seconds is not None:
                active_seconds += seconds
            for answer in check.get('answers', {}).values():
                total_answers += 1
                amount = _answer_amount(answer)
                if amount is not None:
                    prepared += amount
                    measured_answers += 1

    incidents = []
    pending_authorizations = 0
    preparation_alerts = 0
    for truck in trucks:
        if truck.id not in selected_truck_ids:
            continue
        for incident in truck.state.get('incidents', {}).values():
            assigned = (incident.get('incident') or {}).get('responsible_user_id')
            detected = (incident.get('incident') or {}).get('detected_by')
            if incident.get('load_id') in selected_load_ids and (not operator_id or operator_id in (assigned, detected)):
                incidents.append(incident)
        for key, shortage in truck.state.get('courts', {}).items():
            try:
                load_id = int(key.split(':', 1)[0])
            except (TypeError, ValueError):
                continue
            if load_id in selected_load_ids:
                pending_authorizations += sum(1 for item in shortage.get('shortages', {}).values()
                                              if not item.get('approved_by'))
                preparation_alerts += sum(len(items) for items in shortage.get('preparation_shortages', {}).values())
        for key, pallet in truck.state.get('pallet_controls', {}).items():
            try:
                load_id = int(key.split(':', 1)[0])
            except (TypeError, ValueError):
                continue
            if load_id in selected_load_ids:
                pending_authorizations += sum(1 for item in pallet.get('shortages', {}).values()
                                              if not item.get('approved_by'))

    released_trucks = sum(1 for truck in trucks if truck.id in selected_truck_ids and truck.state.get('released_at'))
    operator_rows = [user for user in User.query.options(joinedload(User.role)).filter(User.active.is_(True)).order_by(User.username).all()
                     if user.role.name in ('operador', 'palletizador', 'controlador')]
    options['operarios'].update((user.id, user.username) for user in operator_rows)
    coverage = round(measured_answers / total_answers * 100, 1) if total_answers else None
    productivity = round(prepared / (active_seconds / 3600), 2) if active_seconds > 0 and measured_answers else None

    return dict(
        generated_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        metrics=dict(planillas_programadas=len(selected), planillas_pendientes=states['pendiente'],
            planillas_en_preparacion=states['en_preparacion'], planillas_finalizadas=states['finalizado'],
            avance_pct=round(progress_done / progress_total * 100, 1) if progress_total else None,
            operarios_en_proceso=len(active_users), operarios_disponibles=None,
            bultos_confirmados=round(prepared, 2) if measured_answers else None,
            bultos_pendientes=None, productividad_bultos_hora=productivity,
            diferencias_detectadas=len(incidents), cargas_liberadas=released_trucks,
            cargas_demoradas=None, alertas_operativas=pending_authorizations + preparation_alerts),
        coverage=dict(respuestas_medibles=measured_answers, respuestas_totales=total_answers,
            respuestas_medibles_pct=coverage,
            bultos_pendientes='Requiere cantidades planificadas con factor histórico para todas las líneas.',
            operarios_disponibles='Requiere presencia o heartbeat operativo.',
            cargas_demoradas='Requiere horario comprometido de despacho.'),
        rows=rows[:100], rows_total=len(rows),
        options=dict(sucursales=sorted(options['sucursales']), camiones=sorted(options['camiones']),
            repartos=sorted(options['repartos']), operarios=[dict(id=i, username=n) for i, n in sorted(options['operarios'])]),
        alert_breakdown=dict(autorizaciones_pendientes=pending_authorizations,
                             diferencias_preparacion=preparation_alerts),
        active_processes=active_processes)


def build_productivity_dashboard(args):
    """Aggregate preparation work by person without mixing controls into output."""
    desde, hasta = _date(args.get('desde'), 'desde'), _date(args.get('hasta'), 'hasta')
    if desde and hasta and desde > hasta:
        raise ValueError('La fecha desde no puede ser posterior a la fecha hasta.')
    query = ControlTruck.query.options(selectinload(ControlTruck.loads))
    if desde:
        query = query.filter(ControlTruck.load_date >= desde)
    if hasta:
        query = query.filter(ControlTruck.load_date <= hasta)
    if args.get('sucursal'):
        query = query.filter(ControlTruck.branch == args['sucursal'])
    if args.get('camion'):
        query = query.filter(ControlTruck.truck == args['camion'])
    trucks = query.order_by(ControlTruck.load_date, ControlTruck.id).all()
    reparto = str(args.get('reparto') or '').strip()
    operator = str(args.get('operario') or '').strip()
    operator_id = int(operator) if operator.isdigit() else None
    state_filter = str(args.get('estado') or '').strip()
    if state_filter and state_filter not in {'pendiente', 'en_preparacion', 'finalizado'}:
        raise ValueError('Estado operativo inválido.')

    selected_load_ids = set()
    selected_truck_ids = set()
    dates_by_load = {}
    for truck in trucks:
        for load in selected_loads(truck):
            if reparto and load.reparto != reparto:
                continue
            state = _load_state(load)[0]
            if state_filter and state != state_filter:
                continue
            if operator_id and not any(load_id == load.id and check.get('user_id') == operator_id
                                       for load_id, check in _current_checks(truck)):
                continue
            selected_load_ids.add(load.id)
            selected_truck_ids.add(truck.id)
            dates_by_load[load.id] = truck.load_date

    def empty(user_id, username):
        return dict(user_id=user_id, username=username, bultos=0.0, lineas=0,
            respuestas_medibles=0, tiempo_efectivo_segundos=0.0, tiempo_pausa_segundos=0.0,
            tareas_finalizadas=0, planillas=set(), planillas_con_tarea_finalizada=set(),
            diferencias_atribuidas=0, modalidades=defaultdict(lambda: dict(
                bultos=0.0, lineas=0, respuestas_medibles=0,
                tiempo_efectivo_segundos=0.0, tiempo_pausa_segundos=0.0,
                tareas_finalizadas=0)), por_dia=defaultdict(lambda: dict(
                    bultos=0.0, lineas=0, respuestas_medibles=0, tiempo_efectivo_segundos=0.0)))

    stats = {}
    for truck in trucks:
        if truck.id not in selected_truck_ids:
            continue
        for load_id, check in _current_checks(truck):
            if load_id not in selected_load_ids or check.get('stage') not in (0, 4):
                continue
            user_id = check.get('user_id')
            if user_id is None or (operator_id and user_id != operator_id):
                continue
            row = stats.setdefault(user_id, empty(user_id, check.get('username') or f'Usuario {user_id}'))
            mode = 'picking' if check.get('stage') == 0 else 'pallets_completos'
            mode_row = row['modalidades'][mode]
            seconds, paused = _time_values(check)
            if seconds is not None:
                row['tiempo_efectivo_segundos'] += seconds
                row['tiempo_pausa_segundos'] += paused
                mode_row['tiempo_efectivo_segundos'] += seconds
                mode_row['tiempo_pausa_segundos'] += paused
            row['planillas'].add(load_id)
            if check.get('status') == 'done':
                row['tareas_finalizadas'] += 1
                row['planillas_con_tarea_finalizada'].add(load_id)
                mode_row['tareas_finalizadas'] += 1
            day = row['por_dia'][dates_by_load[load_id]]
            if seconds is not None:
                day['tiempo_efectivo_segundos'] += seconds
            for answer in check.get('answers', {}).values():
                row['lineas'] += 1
                mode_row['lineas'] += 1
                day['lineas'] += 1
                amount = _answer_amount(answer)
                if amount is not None:
                    row['bultos'] += amount
                    row['respuestas_medibles'] += 1
                    mode_row['bultos'] += amount
                    mode_row['respuestas_medibles'] += 1
                    day['bultos'] += amount
                    day['respuestas_medibles'] += 1

        for incident in truck.state.get('incidents', {}).values():
            if incident.get('load_id') not in selected_load_ids:
                continue
            detail = incident.get('incident') or {}
            responsible = detail.get('responsible_user_id')
            if responsible is None or detail.get('origin') == 'stock' or (operator_id and responsible != operator_id):
                continue
            user = db.session.get(User, responsible)
            row = stats.setdefault(responsible, empty(responsible,
                detail.get('responsible_username') or (user.username if user else f'Usuario {responsible}')))
            row['diferencias_atribuidas'] += int(detail.get('error_count', 1) or 0)

    def rate(bultos, seconds, measured):
        return round(bultos / (seconds / 3600), 2) if seconds > 0 and measured else None

    rows, evolution = [], []
    for row in stats.values():
        modes = {}
        for key, value in row['modalidades'].items():
            modes[key] = dict(bultos=round(value['bultos'], 2), lineas=value['lineas'],
                tiempo_efectivo_segundos=round(value['tiempo_efectivo_segundos'], 1),
                tiempo_pausa_segundos=round(value['tiempo_pausa_segundos'], 1),
                tareas_finalizadas=value['tareas_finalizadas'],
                productividad_bultos_hora=rate(value['bultos'], value['tiempo_efectivo_segundos'], value['respuestas_medibles']),
                cobertura_pct=round(value['respuestas_medibles'] / value['lineas'] * 100, 1) if value['lineas'] else None)
        for day_key, value in row['por_dia'].items():
            evolution.append(dict(fecha=day_key, user_id=row['user_id'], username=row['username'],
                bultos=round(value['bultos'], 2), lineas=value['lineas'],
                tiempo_efectivo_segundos=round(value['tiempo_efectivo_segundos'], 1),
                productividad_bultos_hora=rate(value['bultos'], value['tiempo_efectivo_segundos'], value['respuestas_medibles'])))
        rows.append(dict(user_id=row['user_id'], username=row['username'],
            bultos=round(row['bultos'], 2), lineas=row['lineas'],
            tiempo_efectivo_segundos=round(row['tiempo_efectivo_segundos'], 1),
            tiempo_pausa_segundos=round(row['tiempo_pausa_segundos'], 1),
            tareas_finalizadas=row['tareas_finalizadas'], planillas_participadas=len(row['planillas']),
            planillas_con_tarea_finalizada=len(row['planillas_con_tarea_finalizada']),
            diferencias_atribuidas=row['diferencias_atribuidas'],
            productividad_bultos_hora=rate(row['bultos'], row['tiempo_efectivo_segundos'], row['respuestas_medibles']),
            cobertura_pct=round(row['respuestas_medibles'] / row['lineas'] * 100, 1) if row['lineas'] else None,
            modalidades=modes))
    rows.sort(key=lambda row: (-row['bultos'], row['username']))
    evolution.sort(key=lambda row: (row['fecha'], row['username']))
    return dict(rows=rows, evolution=evolution,
        definitions=dict(bultos='Cantidades físicas confirmadas en preparación con factor medible.',
            lineas='Productos respondidos en tareas de preparación; no son líneas originales del PDF.',
            tiempo='Tiempo activo del servidor. Las pausas son tiempo de pared menos tiempo activo.',
            productividad='Bultos confirmados medibles / horas activas. El total combina modalidades.',
            diferencias='Sólo incidencias atribuibles; diferencias de stock quedan excluidas.'),
        coverage=dict(operators=len(rows), loads=len(selected_load_ids)))


def build_quality_dashboard(args):
    """Quality projection with explicit line-based and unavailable unit metrics."""
    desde, hasta = _date(args.get('desde'), 'desde'), _date(args.get('hasta'), 'hasta')
    if desde and hasta and desde > hasta:
        raise ValueError('La fecha desde no puede ser posterior a la fecha hasta.')
    query = ControlTruck.query.options(selectinload(ControlTruck.loads))
    if desde:
        query = query.filter(ControlTruck.load_date >= desde)
    if hasta:
        query = query.filter(ControlTruck.load_date <= hasta)
    if args.get('sucursal'):
        query = query.filter(ControlTruck.branch == args['sucursal'])
    if args.get('camion'):
        query = query.filter(ControlTruck.truck == args['camion'])
    trucks = query.order_by(ControlTruck.load_date, ControlTruck.id).all()
    reparto = str(args.get('reparto') or '').strip()
    operator = str(args.get('operario') or '').strip()
    operator_id = int(operator) if operator.isdigit() else None
    state_filter = str(args.get('estado') or '').strip()
    if state_filter and state_filter not in {'pendiente', 'en_preparacion', 'finalizado'}:
        raise ValueError('Estado operativo inválido.')

    selected = {}
    truck_ids = set()
    for truck in trucks:
        for load in selected_loads(truck):
            if reparto and load.reparto != reparto:
                continue
            if state_filter and _load_state(load)[0] != state_filter:
                continue
            if operator_id and not any(load_id == load.id and check.get('user_id') == operator_id
                                       for load_id, check in _current_checks(truck)):
                continue
            selected[load.id] = (truck, load)
            truck_ids.add(truck.id)

    preparation_lines = control2_lines = 0
    for truck in trucks:
        if truck.id not in truck_ids:
            continue
        for load_id, check in _current_checks(truck):
            if load_id not in selected or (operator_id and check.get('user_id') != operator_id):
                continue
            answers = list(check.get('answers', {}).values())
            if check.get('stage') in (0, 4):
                preparation_lines += len(answers)
            elif check.get('stage') == 2:
                control2_lines += len(answers)

    authorization = {}
    incidents = []
    cause_counts = defaultdict(int)
    picking_errors = stock_differences = control_errors = control2_errors = rework = 0
    for truck in trucks:
        if truck.id not in truck_ids:
            continue
        for key, state in truck.state.get('courts', {}).items():
            try:
                load_id, court = key.split(':', 1)
                load_id = int(load_id)
            except (TypeError, ValueError):
                continue
            if load_id not in selected:
                continue
            for product_key, item in state.get('shortages', {}).items():
                authorization[(load_id, str(court), None, product_key)] = dict(item, authorization_required=True)
            for stage_items in state.get('preparation_shortages', {}).values():
                for product_key, item in stage_items.items():
                    authorization[(load_id, str(court), None, product_key)] = dict(item, authorization_required=False)
        for key, state in truck.state.get('pallet_controls', {}).items():
            try:
                load_id, pallet_id = key.split(':', 1)
                load_id = int(load_id)
            except (TypeError, ValueError):
                continue
            if load_id in selected:
                for product_key, item in state.get('shortages', {}).items():
                    authorization[(load_id, None, pallet_id, product_key)] = dict(item, authorization_required=True)

        for raw in truck.state.get('incidents', {}).values():
            load_id = raw.get('load_id')
            if load_id not in selected:
                continue
            detail = raw.get('incident') or {}
            if operator_id and operator_id not in (detail.get('responsible_user_id'), detail.get('detected_by')):
                continue
            origin = detail.get('origin') or 'unknown'
            error_count = int(detail.get('error_count', 1) or 0)
            if origin == 'picking':
                picking_errors += error_count
            elif origin == 'stock':
                stock_differences += 1
            elif origin == 'control':
                control_errors += error_count
                if raw.get('stage') == 2:
                    control2_errors += error_count
            if raw.get('result') == 'corrected' and origin == 'picking':
                rework += 1
            cause = detail.get('error_type') or raw.get('shortage_reason') or origin
            cause_counts[cause] += 1
            truck_row, load = selected[load_id]
            product_key = str(raw.get('product_key') or raw.get('sku'))
            auth = authorization.get((load_id, str(raw.get('court')), None, product_key))
            if raw.get('pallet_id') is not None:
                auth = authorization.get((load_id, None, str(raw.get('pallet_id')), product_key), auth)
            measurement = raw.get('measurement') or {}
            expected_b = detail.get('expected_b', measurement.get('expected_b'))
            expected_u = detail.get('expected_u', measurement.get('expected_u'))
            actual_b = detail.get('actual_b', raw.get('physical_b'))
            actual_u = detail.get('actual_u', raw.get('physical_u'))
            review_status = (auth or {}).get('review_status')
            if (auth or {}).get('adjusted_by'):
                status = 'ajustado'
            elif (auth or {}).get('approved_by'):
                status = 'autorizado'
            elif review_status:
                status = review_status
            elif (auth or {}).get('authorization_required'):
                status = 'pendiente'
            else:
                status = 'registrado'
            incidents.append(dict(fecha=truck_row.load_date, sucursal=truck_row.branch,
                camion=truck_row.truck, load_id=load_id, reparto=load.reparto,
                court=raw.get('court'), pallet_id=raw.get('pallet_id'), sku=raw.get('sku'),
                product_key=product_key, descripcion=raw.get('descripcion'), result=raw.get('result'),
                origin=origin, cause=cause, expected_b=expected_b, expected_u=expected_u,
                actual_b=actual_b, actual_u=actual_u,
                difference_b=(expected_b - actual_b if isinstance(expected_b, (int, float)) and isinstance(actual_b, (int, float)) else None),
                difference_u=(expected_u - actual_u if isinstance(expected_u, (int, float)) and isinstance(actual_u, (int, float)) else None),
                responsible_username=detail.get('responsible_username'),
                detected_username=detail.get('detected_username'), saved_at=raw.get('saved_at'),
                process_status=raw.get('process_status'), status=status,
                review_history=(auth or {}).get('review_history', []), note=raw.get('note')))

    def percentage(good, total):
        return round(good / total * 100, 1) if total else None

    incidents.sort(key=lambda row: (row['fecha'], row['camion'], row['reparto'], row['sku'] or ''), reverse=True)
    return dict(metrics=dict(
        exactitud_picking_pct=percentage(max(0, preparation_lines - picking_errors), preparation_lines),
        diferencias_stock_pct=percentage(stock_differences, preparation_lines),
        retrabajo_pct=percentage(rework, preparation_lines),
        exactitud_segundo_control_lineas_pct=percentage(max(0, control2_lines - control2_errors), control2_lines),
        exactitud_segundo_control_unidades_pct=None,
        lineas_preparacion=preparation_lines, lineas_segundo_control=control2_lines,
        errores_picking=picking_errors, errores_control=control_errors,
        errores_segundo_control=control2_errors,
        diferencias_stock=stock_differences, lineas_retrabajadas=rework),
        coverage=dict(
            exactitud_picking='Basada en productos respondidos, no en líneas originales del PDF.',
            exactitud_segundo_control_unidades='Requiere unidades esperadas y verificadas consistentes para todo el período.'),
        causes=[dict(cause=key, count=value) for key, value in sorted(cause_counts.items(), key=lambda item: (-item[1], item[0]))],
        incidents=incidents[:100], incidents_total=len(incidents))
