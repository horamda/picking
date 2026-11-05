"""Physical-pallet control workflow stored inside the versioned truck state."""
from copy import deepcopy

from services.load_control import court_state, selected_loads


def _group_items(items):
    grouped = {}
    for raw in items:
        identity = raw.get('product_key') or (f'{raw["sku"]}|{raw["fecha_frescura"]}'
            if raw.get('fecha_frescura') else str(raw['sku']))
        item = grouped.setdefault(identity, dict(raw, product_key=identity, bultos=0, unidades=0,
            source_courts=[], pallet_ids=[]))
        item['bultos'] += raw.get('bultos', 0)
        item['unidades'] += raw.get('unidades', 0)
        if raw.get('court') not in item['source_courts']:
            item['source_courts'].append(raw.get('court'))
    return list(grouped.values())


def physical_pallets(truck):
    plan = truck.state.get('planning') or {}
    loads = {load.id: load for load in selected_loads(truck)}
    result = []
    for pallet in plan.get('mixed_pallets', []):
        load = loads.get(pallet.get('load_id'))
        if not load:
            continue
        owner = pallet.get('owner_court', pallet.get('court'))
        result.append(dict(key=f'{load.id}:{pallet["id"]}', id=pallet['id'], load_id=load.id,
            reparto=load.reparto, owner_court=owner, kind='picking', occupancy=pallet.get('occupancy'),
            items=_group_items(pallet.get('items', [])), assembly_stage=0))
    for group in plan.get('full_pallets', []):
        load = loads.get(group.get('load_id'))
        if not load:
            continue
        count = group.get('pallets', 0)
        per_pallet = group.get('bultos_por_pallet') or (group.get('bultos', 0) // count if count else 0)
        for index in range(count):
            pallet_id = f'{group["id"]}-{index + 1:02}' if count > 1 else group['id']
            item = dict(group, bultos=per_pallet, unidades=0, pallets=1)
            result.append(dict(key=f'{load.id}:{pallet_id}', id=pallet_id, load_id=load.id,
                reparto=load.reparto, owner_court=group['court'], kind='full', occupancy=1.0,
                items=_group_items([item]), assembly_stage=4))
    return result


def pallet_state(state, key):
    return state.get('pallet_controls', {}).get(key, {'checks': {}, 'shortages': {}})


def edit_pallet_state(state, key):
    return state.setdefault('pallet_controls', {}).setdefault(key, {'checks': {}, 'shortages': {}})


def assembly_done(truck, pallet):
    check = court_state(truck.state, pallet['load_id'], pallet['owner_court'])['checks'].get(str(pallet['assembly_stage']), {})
    return check.get('status') == 'done'


def picking_alerts(truck, pallet):
    alerts = []
    for item in pallet['items']:
        identity = str(item.get('product_key') or item['sku'])
        for court in item.get('source_courts') or [pallet['owner_court']]:
            preparation = court_state(truck.state, pallet['load_id'], court).get('preparation_shortages', {}).get('0', {})
            alert = preparation.get(identity) or preparation.get(str(item['sku']))
            if alert and not any(existing.get('product_key') == identity for existing in alerts):
                alerts.append(dict(deepcopy(alert), product_key=identity, source_court=court))
    return alerts


def effective_check(truck, pallet, stage):
    check = pallet_state(truck.state, pallet['key'])['checks'].get(str(stage))
    if check:
        return check
    # Preserve completed controls made before the pallet workflow was introduced.
    legacy = court_state(truck.state, pallet['load_id'], pallet['owner_court'])['checks'].get(str(stage), {})
    return legacy if legacy.get('status') == 'done' else {}


def board(truck):
    assignments = truck.state.get('pallet_control_assignments', {})
    rows = []
    for pallet in physical_pallets(truck):
        first, second = effective_check(truck, pallet, 1), effective_check(truck, pallet, 2)
        ready = assembly_done(truck, pallet)
        assembly = court_state(truck.state, pallet['load_id'], pallet['owner_court'])['checks'].get(str(pallet['assembly_stage']), {})
        alerts = picking_alerts(truck, pallet)
        rows.append(dict(deepcopy(pallet), assembly_done=ready,
            assembly=_check_summary(assembly),
            picking_alerts=alerts, picking_alert_count=len(alerts),
            controls={'1': _check_summary(first), '2': _check_summary(second)},
            control1_available=ready and first.get('status') != 'done',
            control2_available=first.get('status') == 'done' and second.get('status') != 'done'))
    return dict(assignments=assignments, pallets=rows,
        control1_complete=bool(rows) and all(row['controls']['1'].get('status') == 'done' for row in rows),
        control2_complete=bool(rows) and all(row['controls']['2'].get('status') == 'done' for row in rows))


def user_control_progress(board_data, user_id):
    """Summarize one controller's work without hiding the truck audit trail."""
    assignments = board_data.get('assignments') or {}
    first, second = assignments.get('1'), assignments.get('2')
    stage = 1 if first and first.get('user_id') == user_id else 2 if second and second.get('user_id') == user_id else 0
    rows = board_data.get('pallets') or []
    if stage:
        done = sum(1 for row in rows if row.get('controls', {}).get(str(stage), {}).get('status') == 'done')
        completed = bool(rows) and done == len(rows)
        return dict(stage=stage, assigned=True, completed=completed, done=done, total=len(rows),
                    available=not completed,
                    label=(f'Tu Control {stage} finalizado' if completed
                           else f'Tu Control {stage}: {done} de {len(rows)} pallets'))
    if board_data.get('control2_complete'):
        return dict(stage=0, assigned=False, completed=True, done=len(rows), total=len(rows),
                    available=False, label='Camión totalmente controlado')
    if first is None:
        return dict(stage=1, assigned=False, completed=False, done=0, total=len(rows),
                    available=True, label='Control 1 disponible')
    if second is None and first.get('user_id') != user_id:
        done = sum(1 for row in rows if row.get('controls', {}).get('1', {}).get('status') == 'done')
        return dict(stage=2, assigned=False, completed=False, done=0, total=len(rows),
                    available=True, label=f'Control 2 disponible · Control 1: {done} de {len(rows)} pallets')
    return dict(stage=0, assigned=False, completed=False, done=0, total=len(rows),
                available=False, label='Controles asignados a otros operadores')


def _check_summary(check):
    return {key: check.get(key) for key in ('id', 'stage', 'user_id', 'username', 'status',
        'started_at', 'timer_started_at', 'finished_at') if check.get(key) is not None}


def claim_assignment(state, stage, user):
    assignments = state.setdefault('pallet_control_assignments', {})
    own = assignments.get(str(stage))
    other = assignments.get(str(2 if stage == 1 else 1))
    if own and own['user_id'] != user.id:
        raise ValueError(f'El Control {stage} de este camión está asignado a {own["username"]}.')
    if other and other['user_id'] == user.id:
        raise PermissionError('Los dos controles del camión deben realizarlos personas diferentes.')
    if not own:
        assignments[str(stage)] = {'user_id': user.id, 'username': user.username}
    return assignments[str(stage)]
