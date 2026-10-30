from copy import deepcopy
import hashlib
import json
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import text

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import HTTPException

from auth import auth_required, roles_required, current_user_payload
from models import Consolidado, User, LogEntry, Article
from services.pallet_planning import plan_for_capacity
from services.warehouse import UserCourt, DepotSettings, TruckCapacity, assigned_courts, validate_courts
from services.load_control import (ControlTruck, ControlLoad, ControlTimer, ASSET_NAMES, now, truck_name,
    court_state, edit_court, court_done, status, save_state, snapshot, audit, elapsed, timing, stop_timer, selected_loads)
from services.dispatch import totals, truck_summary, worker_queue, selection_preview
from services.pdf_articles import enable_pdf_articles
from utils.db import db
from services.users import create_user as register_user, UserCreationError

load_control_bp = Blueprint('load_control', __name__)
MANAGERS = ('administrador', 'supervisor')


def manager():
    return g.current_user.role.name in MANAGERS


def preparation_worker():
    return g.current_user.role.name in ('operador', 'palletizador')


def current_dispatch_truck():
    if 'picking.dispatch_current' in request.environ:
        return request.environ['picking.dispatch_current']
    stage = 4 if g.current_user.role.name == 'palletizador' else 0
    g.dispatch_configured = db.session.query(ControlTruck.id).filter(
        ControlTruck.state['dispatch']['load_ids'].as_string().isnot(None)).first() is not None
    rows = ControlTruck.query.filter(ControlTruck.state['released_at'].as_string().is_(None)).options(selectinload(ControlTruck.loads)).all()
    # A pre-existing reservation must remain resumable during rollout.
    owned = [t for t in rows if any(ch.get('stage') == stage and ch.get('status') == 'active'
             and ch.get('user_id') == g.current_user.id for c in t.state.get('courts', {}).values()
             for ch in c.get('checks', {}).values())]
    queue = worker_queue(rows, assigned_courts(g.current_user.id), stage, task_products)
    current = (sorted(owned, key=lambda t: (t.load_date, t.id)) or queue or [None])[0]
    request.environ['picking.dispatch_current'] = current
    return current


def require_dispatch(load):
    if load not in selected_loads(load.truck):
        fail('Este reparto no está seleccionado para armar.', 409)
    if preparation_worker():
        current = current_dispatch_truck()
        if g.dispatch_configured and (current is None or current.id != load.truck_id):
            fail('Terminá tus canchas del camión actual antes de pasar al siguiente.', 409)


def dispatch_catalog():
    if 'picking.dispatch_catalog' not in request.environ:
        request.environ['picking.dispatch_catalog'] = {a.sku: a for a in Article.query.all()}
    return request.environ['picking.dispatch_catalog']


def dispatch_versions(trucks):
    # Product confirmations change truck.version, but do not edit the dispatch.
    return {str(t.id): hashlib.sha256(json.dumps(t.state.get('dispatch'), sort_keys=True).encode()).hexdigest() for t in trucks}


@load_control_bp.get('/dispatch')
@roles_required(*MANAGERS)
def dispatch_board():
    date = request.args.get('date', '')
    try:
        day = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        fail('Seleccioná una fecha de reparto válida.')
    sources = Consolidado.query.filter(Consolidado.fecha_reparto >= day, Consolidado.fecha_reparto < day + timedelta(days=1)).options(selectinload(Consolidado.detalles)).order_by(Consolidado.id).all()
    trucks = ControlTruck.query.filter_by(load_date=date).options(selectinload(ControlTruck.loads)).all()
    by_key = {(t.branch, t.truck): t for t in trucks}
    groups = {}
    for source in sources:
        key = ((source.deposito or '').strip(), truck_name(source.camion))
        t = by_key.get(key)
        group = groups.setdefault(key, dict(branch=key[0], truck=key[1], truck_id=t.id if t else None,
            position=(t.state.get('dispatch') or {}).get('position') if t else None,
            planning_status='approved' if t and approved(t) else 'pending', sources=[]))
        try:
            data = snapshot(source)
            rows = [dict(p, load_id=source.id, court=c['numero']) for c in data['canchas'] for p in c['productos']]
            load = next((l for l in t.loads if l.source_id == source.id), None) if t else None
            selected = bool(t and load and load.id in t.state.get('dispatch', {}).get('load_ids', []))
            group['sources'].append(dict(id=source.id, reparto=source.reparto, selected=selected,
                court_numbers=sorted({r['court'] for r in rows}), totals=totals(rows, dispatch_catalog()), error=None))
        except ValueError as exc:
            group['sources'].append(dict(id=source.id, reparto=source.reparto, selected=False, totals=None, error=str(exc)))
    prefix = max((t.state.get('dispatch', {}).get('position', 0) for t in trucks
                  if any(c.get('checks') for c in t.state.get('courts', {}).values())), default=0)
    for group in groups.values():
        t = by_key.get((group['branch'], group['truck']))
        group['locked'] = bool(t and (t.state.get('released_at') or any(c.get('checks') for c in t.state.get('courts', {}).values())
                                     or (group['position'] and group['position'] <= prefix)))
    return jsonify(date=date, versions=dispatch_versions(trucks), groups=sorted(groups.values(), key=lambda x: (x['position'] or 1000000, x['branch'], x['truck'])))


@load_control_bp.post('/dispatch')
@roles_required(*MANAGERS)
def save_dispatch():
    data = body()
    date, entries = data.get('date'), data.get('entries')
    if not isinstance(date, str):
        fail('Fecha inválida.')
    try:
        datetime.strptime(date or '', '%Y-%m-%d')
    except ValueError:
        fail('Fecha inválida.')
    if not isinstance(entries, list) or len(entries) > 500:
        fail('La selección de camiones es inválida.')
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text('SELECT pg_advisory_xact_lock(2810202601)'))
    existing = ControlTruck.query.filter_by(load_date=date).order_by(ControlTruck.id).with_for_update().populate_existing().all()
    if data.get('versions') != dispatch_versions(existing):
        fail('Las cargas cambiaron. Actualizá la selección antes de guardarla.', 409)
    wanted, seen = {}, set()
    for position, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or not isinstance(entry.get('source_ids'), list) or not entry['source_ids']:
            fail('Seleccioná al menos un reparto por camión.')
        key = (entry.get('branch'), entry.get('truck'))
        if not all(isinstance(v, str) and v.strip() for v in key):
            fail('Depósito o camión inválido.')
        if key in wanted:
            fail('Camión duplicado en la cola.')
        loads = []
        for source_id in entry['source_ids']:
            if type(source_id) is not int or source_id in seen:
                fail('Reparto inválido o duplicado.')
            seen.add(source_id)
            source = db.session.get(Consolidado, source_id)
            if not source or not source.fecha_reparto or source.fecha_reparto.date().isoformat() != date or ((source.deposito or '').strip(), truck_name(source.camion)) != key:
                fail('El reparto no corresponde al camión y fecha seleccionados.', 409)
            load = ControlLoad.query.filter_by(source_id=source_id).first()
            if load is None:
                try:
                    load = add_load(snapshot(source), source.id)
                except ValueError as exc:
                    fail(str(exc), 422)
            enable_pdf_articles([row.sku for row in source.detalles], g.current_user.id, source.id)
            loads.append(load)
        wanted[key] = dict(truck=loads[0].truck, load_ids=[l.id for l in loads], position=position)
    # Preserve the prefix already in execution. Later trucks can still be appended/reordered.
    started_positions = [t.state['dispatch']['position'] for t in existing if t.state.get('dispatch') and any(c.get('checks') for c in t.state.get('courts', {}).values())]
    prefix = max(started_positions, default=0)
    for t in existing:
        old = t.state.get('dispatch')
        new = wanted.get((t.branch, t.truck))
        started = any(c.get('checks') for c in t.state.get('courts', {}).values()) or t.state.get('released_at')
        if (started or (old and old['position'] <= prefix)) and (old or new):
            if not old or not new or old['load_ids'] != new['load_ids'] or old['position'] != new['position']:
                fail('No se puede cambiar la selección ni el orden de camiones que ya comenzaron.', 409)
    for item in wanted.values():
        t = item['truck']
        old = t.state.get('dispatch')
        if item['position'] <= prefix and (not old or old['position'] != item['position']):
            fail('No se puede insertar un camión antes del trabajo que ya comenzó.', 409)
    all_trucks = {t.id: t for t in existing}
    all_trucks.update({v['truck'].id: v['truck'] for v in wanted.values()})
    for t in all_trucks.values():
        item = wanted.get((t.branch, t.truck))
        if not item and 'dispatch' not in t.state and (t.state.get('released_at') or any(c.get('checks') for c in t.state.get('courts', {}).values())):
            continue
        selection = dict(load_ids=item['load_ids'] if item else [], position=item['position'] if item else 1000000)
        old = t.state.get('dispatch')
        if old and all(old.get(k) == selection[k] for k in selection):
            continue
        state = deepcopy(t.state)
        state['dispatch'] = dict(selection, selected_at=now(), selected_by=g.current_user.id)
        if not old or old.get('load_ids') != selection['load_ids']:
            state.pop('planning', None)
            state.pop('planning_started_at', None)
            state['planning_requested_at'] = now()
        t.state = state
        audit(g.current_user, 'seleccionar_cola_armado', t, selection)
    db.session.commit()
    return jsonify(ok=True, trucks=len(wanted), loads=len(seen))


@load_control_bp.post('/dispatch/preview')
@roles_required(*MANAGERS)
def preview_dispatch():
    ids = body().get('source_ids')
    if not isinstance(ids, list) or not ids or len(ids) > 500 or any(type(i) is not int for i in ids) or len(set(ids)) != len(ids):
        fail('Seleccioná los repartos de un camión.')
    sources = Consolidado.query.filter(Consolidado.id.in_(ids)).options(selectinload(Consolidado.detalles)).order_by(Consolidado.id).all()
    if len(sources) != len(ids):
        fail('Algún reparto ya no está disponible.', 409)
    rows, keys = [], set()
    for source in sources:
        try:
            data = snapshot(source)
        except ValueError as exc:
            fail(str(exc), 422)
        keys.add((data['deposito'], data['camion'], data['fecha']))
        rows.extend(dict(p, load_id=source.id, reparto=data['reparto'], court=c['numero']) for c in data['canchas'] for p in c['productos'])
    if len(keys) != 1:
        fail('La vista previa debe corresponder a un solo camión, depósito y fecha.')
    branch, truck, date = keys.pop()
    capacity = db.session.get(TruckCapacity, (branch, truck))
    depot = db.session.get(DepotSettings, branch)
    existing = ControlTruck.query.filter_by(branch=branch, truck=truck, load_date=date).first()
    saved_plan = existing.state.get('planning', {}) if existing else {}
    mix = saved_plan.get('mix_courts', depot.mix_courts_default if depot else False)
    return jsonify(selection_preview(rows, dispatch_catalog(), capacity.pallet_capacity if capacity else None, mix))


def require_court(number):
    db.session.query(User).filter_by(id=g.current_user.id).with_for_update().first()
    if not manager() and number not in assigned_courts(g.current_user.id):
        fail('Esta cancha no está asignada a tu usuario.', 403)


def require_truck_courts(truck):
    if not manager():
        assigned = assigned_courts(g.current_user.id)
        if any(c['numero'] not in assigned for load in selected_loads(truck) for c in load.content['canchas']):
            fail('Los activos de este camion requieren un supervisor o un controlador asignado a todas sus canchas.', 403)


def require_stage(stage):
    if not manager() and stage not in {'operador': (0,), 'controlador': (1, 2), 'palletizador': (4,)}.get(g.current_user.role.name, ()):
        fail('Este proceso no corresponde a tu rol.', 403)


def plan_fingerprint(truck, capacity, mix):
    value = dict(rows=planning_rows(truck), capacity=capacity, mix=mix,
                 pending=status(truck)['pending_sources'])
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def legacy_in_progress(truck):
    return not truck.state.get('planning') and any(c.get('checks') for c in truck.state.get('courts', {}).values())


def approved(truck):
    plan = truck.state.get('planning', {})
    capacity = db.session.get(TruckCapacity, (truck.branch, truck.truck))
    if not (plan.get('approved_at') and capacity and capacity.pallet_capacity == plan['capacity']):
        return False
    # Once physical work starts, its approved quantities are frozen. Catalog updates
    # affect future plans, never quantities already being prepared by an operator.
    if any(c.get('checks') for c in truck.state.get('courts', {}).values()):
        return True
    return plan.get('fingerprint') == plan_fingerprint(truck, plan['capacity'], plan['mix_courts'])



def voice_products(products):
    skus = {p['sku'] for p in products}
    descriptions = dict(db.session.query(Article.sku, Article.descripcion_voz)
                        .filter(Article.sku.in_(skus)).all()) if skus else {}
    return [dict(p, descripcion_voz=descriptions.get(p['sku']) or p['descripcion']) for p in products]


def full_pallets_info(load, court):
    plan = load.truck.state.get('planning') or {}
    return [dict(sku=p['sku'], descripcion=p['descripcion'], pallets=p['pallets'], bultos=p['bultos'])
            for p in plan.get('full_pallets', []) if p['load_id'] == load.id and p['court'] == court['numero']]


def task_products(load, court, stage):
    plan = load.truck.state.get('planning')
    if not plan:
        return deepcopy(court['productos']) if stage == 0 and (manager() or legacy_in_progress(load.truck)) else []
    rows = plan['picking_tasks' if stage == 0 else 'full_pallets']
    quantities = {p['sku']: p for p in rows if p['load_id'] == load.id and p['court'] == court['numero']}
    pallet_info = {p['sku']: p for p in full_pallets_info(load, court)} if stage == 0 else {}
    result = []
    for product in court['productos']:
        task = quantities.get(product['sku'])
        if task and (task['bultos'] or task.get('unidades', 0)):
            info = pallet_info.get(product['sku'], {})
            result.append(dict(product, bultos=task['bultos'], unidades=task.get('unidades', 0), pallets=task.get('pallets', 0),
                               full_pallets_count=info.get('pallets', 0), full_pallets_bultos=info.get('bultos', 0)))
    return result


def fail(message, code=400):
    from werkzeug.exceptions import HTTPException
    exc = HTTPException(description=message)
    exc.code = code
    raise exc


@load_control_bp.errorhandler(HTTPException)
def http_error(exc):
    db.session.rollback()
    return jsonify(error=exc.description), exc.code


@load_control_bp.errorhandler(IntegrityError)
@load_control_bp.errorhandler(StaleDataError)
def conflict(exc):
    db.session.rollback()
    return jsonify(error='Otro usuario modificó esta carga o el reparto ya existe. Actualizá y reintentá.'), 409


def body():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        fail('Se requiere un objeto JSON válido.')
    return value


def reserve_timer(check):
    running = db.session.get(ControlTimer, g.current_user.id)
    if running and running.check_id != check['id']:
        fail('Ya tenés un proceso en curso. Pausalo o finalizalo antes de iniciar otro.', 409)
    if not running:
        db.session.add(ControlTimer(user_id=g.current_user.id, check_id=check['id']))


def release_timer(check):
    ControlTimer.query.filter_by(check_id=check['id']).delete()
    stop_timer(check)


def get_truck(truck_id):
    query = ControlTruck.query.filter_by(id=truck_id)
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        query = query.with_for_update().populate_existing()
    truck = query.first()
    if not truck:
        fail('Camión no encontrado.', 404)
    return truck


def get_load(load_id):
    load = db.session.get(ControlLoad, load_id)
    if not load:
        fail('Planilla no encontrada.', 404)
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        get_truck(load.truck_id)
    return load


def ensure_open(truck):
    if truck.state.get('released_at'):
        fail('Camión liberado: no se permiten cambios en los controles.', 409)


def get_court(load, number):
    require_court(number)
    court = next((c for c in load.content['canchas'] if c['numero'] == number), None)
    if not court:
        fail('Cancha inexistente.', 404)
    return court


def serialize_load(load, summary=False):
    result = dict(id=load.id, source_id=load.source_id, **deepcopy(load.content))
    result['canchas'] = [c for c in result['canchas'] if manager() or c['numero'] in assigned_courts(g.current_user.id)]
    for court in result['canchas']:
        pallet_info = full_pallets_info(load, court)
        court['full_pallet_count'] = sum(p['pallets'] for p in pallet_info)
        if not summary:
            court['full_pallets_info'] = pallet_info
        if not manager() and g.current_user.role.name in ('operador', 'palletizador'):
            court['productos'] = task_products(load, court, 0 if g.current_user.role.name == 'operador' else 4)
        cs = court_state(load.truck.state, load.id, court['numero'])
        checks = [dict({k: v for k, v in check.items() if k != 'answers'}, answered=len(check.get('answers', {})), elapsed_seconds=elapsed(check), timing=timing(check)) for check in cs['checks'].values()]
        court['status'] = dict(checks=checks,
                               shortages=list(cs['shortages'].values()), done=court_done(cs))
        if summary:
            court['cantidad'] = len(court.pop('productos'))
        else:
            court['productos'] = voice_products(court['productos'])
    if g.current_user.role.name in ('operador', 'palletizador'):
        result['canchas'] = [c for c in result['canchas'] if c.get('cantidad', len(c.get('productos', []))) > 0
                            or (g.current_user.role.name == 'operador' and c['full_pallet_count'] > 0)]
    return result


def add_load(payload, source_id=None):
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text('SELECT pg_advisory_xact_lock(2810202601)'))
    payload['camion'] = truck_name(payload['camion'])
    payload['deposito'] = payload['deposito'].strip()
    key = dict(branch=payload['deposito'], load_date=payload['fecha'])
    if ControlLoad.query.filter_by(**key, reparto=payload['reparto']).first():
        fail(f"El reparto {payload['reparto']} ya está en Control de cargas.", 409)
    truck = ControlTruck.query.filter_by(**key, truck=payload['camion']).with_for_update().populate_existing().first()
    if truck:
        ensure_open(truck)
        if truck.state.get('assets'):
            fail('El camión ya tiene activos confirmados; no se pueden agregar planillas.', 409)
        # Bump the version even when only adding a snapshot: competes with release.
        state = deepcopy(truck.state)
        if any(c.get('checks') for c in truck.state.get('courts', {}).values()):
            fail('El armado ya comenzo; no se pueden incorporar mas cargas.', 409)
        state.pop('planning', None)
        state['planning_requested_at'] = now()
        state.pop('planning_started_at', None)
        state['updated_at'] = now()
        truck.state = state
    else:
        truck = ControlTruck(**key, truck=payload['camion'], state={'courts': {}, 'planning_requested_at': now()})
        db.session.add(truck)
        db.session.flush()
    load = ControlLoad(**key, reparto=payload['reparto'], truck_id=truck.id,
                       source_id=source_id, content=payload)
    db.session.add(load)
    db.session.flush()
    audit(g.current_user, 'importar_planilla_control', truck, dict(load_id=load.id, source_id=source_id))
    return load


@load_control_bp.get('/trucks')
@auth_required
def trucks():
    result = []
    query = ControlTruck.query.options(selectinload(ControlTruck.loads))
    current = current_dispatch_truck() if preparation_worker() else None
    queued = preparation_worker() and g.dispatch_configured
    if queued:
        if not current:
            return jsonify([])
        query = query.filter_by(id=current.id)
    elif request.args.get('date'):
        query = query.filter_by(load_date=request.args['date'])
    for t in query.order_by(ControlTruck.load_date.desc(), ControlTruck.id.desc()).all():
        if t.state.get('dispatch') is not None and not selected_loads(t):
            continue
        valid = approved(t)
        if not manager() and not valid and not legacy_in_progress(t) and not queued:
            continue
        loads = [serialize_load(l, summary=True) for l in selected_loads(t)] if valid or manager() or legacy_in_progress(t) else []
        loads = [l for l in loads if l['canchas']]
        if not manager() and not loads and not queued:
            continue
        st = status(t)
        if not manager():
            allowed = assigned_courts(g.current_user.id)
            st['shortages'] = [sh for sh in st['shortages'] if sh['court'] in allowed]
            st['pending_sources'] = []
        result.append(dict(id=t.id, branch=t.branch, load_date=t.load_date, truck=t.truck,
            version=t.version, planning_status='approved' if valid else 'legacy' if legacy_in_progress(t) else 'pending', status=st, loads=loads,
            dispatch=t.state.get('dispatch'), queue_current=queued,
            summary=truck_summary(t, dispatch_catalog(), assigned_courts(g.current_user.id) if preparation_worker() else None,
                                  4 if g.current_user.role.name == 'palletizador' else 0, valid=bool(valid))))
    return jsonify(result)


@load_control_bp.post('/trucks/<int:truck_id>/planning/simulate')
@roles_required(*MANAGERS)
def simulate_truck(truck_id):
    truck = get_truck(truck_id)
    data = body()
    if status(truck)['pending_sources']:
        fail('Hay repartos importados sin incorporar a este camión. Incorporá todas las cargas antes de simular.', 409)
    rows = planning_rows(truck)
    if not rows:
        fail('El camión no tiene productos para simular.')
    try:
        result = plan_for_capacity(rows, data.get('capacity'), data.get('mix_courts', False))
    except ValueError as exc:
        fail(str(exc))
    return jsonify(dict(result, fingerprint=plan_fingerprint(truck, result['capacity'], result['mix_courts']), version=truck.version, truck=truck.truck, branch=truck.branch, date=truck.load_date))


@load_control_bp.get('/loads/<int:load_id>')
@auth_required
def load_detail(load_id):
    load = get_load(load_id)
    if not manager():
        require_dispatch(load)
    if not manager() and not approved(load.truck) and not legacy_in_progress(load.truck):
        fail('La carga espera aprobacion del supervisor.', 409)
    result = serialize_load(load)
    result['truck_summary'] = truck_summary(load.truck, dispatch_catalog(), assigned_courts(g.current_user.id) if preparation_worker() else None,
                                           4 if g.current_user.role.name == 'palletizador' else 0, valid=bool(approved(load.truck)))
    if not manager() and not result['canchas']:
        fail('No tenes canchas asignadas en esta carga.', 403)
    return jsonify(result)


@load_control_bp.get('/sources')
@auth_required
def sources():
    if not manager():
        return jsonify([])
    used = db.session.query(ControlLoad.source_id).filter(ControlLoad.source_id.isnot(None))
    rows = Consolidado.query.filter(~Consolidado.id.in_(used)).order_by(Consolidado.id.desc()).all()
    return jsonify([dict(id=c.id, reparto=c.reparto, camion=c.camion, camion_control=truck_name(c.camion), deposito=c.deposito,
        fecha=c.fecha_reparto.isoformat() if c.fecha_reparto else None) for c in rows])


@load_control_bp.post('/sources/<int:source_id>')
@roles_required(*MANAGERS)
def import_source(source_id):
    source = db.session.get(Consolidado, source_id)
    if not source:
        fail('Reparto no encontrado.', 404)
    try:
        data = snapshot(source)
    except ValueError as exc:
        fail(str(exc), 422)
    load = add_load(data, source.id)
    db.session.commit()
    return jsonify(id=load.id), 201


@load_control_bp.post('/loads/<int:load_id>/courts/<int:number>/start/<int:stage>')
@auth_required
def start(load_id, number, stage):
    require_stage(stage)
    if stage not in (0, 1, 2, 4):
        fail('Etapa inválida.')
    load = get_load(load_id)
    ensure_open(load.truck)
    court = get_court(load, number)
    require_dispatch(load)
    if not approved(load.truck) and not legacy_in_progress(load.truck):
        fail('La carga espera aprobacion del supervisor.', 409)
    if legacy_in_progress(load.truck) and stage in (0, 4) and str(stage) not in court_state(load.truck.state, load.id, number)['checks']:
        fail('Carga anterior en control: no se puede iniciar un armado nuevo.', 409)
    if stage in (0, 4) and not task_products(load, court, stage):
        fail('No hay productos para este proceso.', 409)
    state = deepcopy(load.truck.state)
    cs = edit_court(state, load.id, number)
    if stage in (0, 4) and any(str(n) in cs['checks'] for n in (1, 2)):
        fail('El control ya comenz?; no se puede iniciar picking retroactivamente.', 409)
    if stage == 1 and any(cs['checks'].get(str(n), {}).get('status') == 'active' for n in (0, 4)):
        fail('Primero debe finalizar el picking en curso.', 409)
    if stage == 1 and not legacy_in_progress(load.truck) and any(task_products(load, court, n) and cs['checks'].get(str(n), {}).get('status') != 'done' for n in (0, 4)):
        fail('Primero deben finalizar picking y pallets completos de esta cancha.', 409)
    previous = cs['checks'].get('1')
    if stage == 2:
        if not previous or previous['status'] != 'done':
            fail('Primero debe finalizar el control 1.', 409)
        if previous['user_id'] == g.current_user.id:
            fail('El segundo control debe hacerlo otra persona.', 403)
    check = cs['checks'].get(str(stage))
    if check:
        if check['status'] != 'active':
            fail('El control ya finalizó.', 409)
        if check['user_id'] is None:
            check.update(user_id=g.current_user.id, username=g.current_user.username, started_at=now(), active_seconds=0)
        if check['user_id'] != g.current_user.id:
            fail('Control reservado por otro empleado.', 409)
        if not check.get('timer_started_at'):
            reserve_timer(check)
            check['timer_started_at'] = now()
            save_state(load.truck, state, g.current_user, 'reanudar_proceso', dict(load_id=load.id, court=number, stage=stage))
    else:
        check = dict(id=uuid4().hex, stage=stage, user_id=g.current_user.id,
                     username=g.current_user.username, status='active', started_at=now(),
                     timer_started_at=now(), active_seconds=0, answers={})
        reserve_timer(check)
        cs['checks'][str(stage)] = check
        save_state(load.truck, state, g.current_user, 'iniciar_control', dict(load_id=load.id, court=number, stage=stage))
    return jsonify(dict(check, products=voice_products(task_products(load, court, stage)))) if stage in (0, 4) else jsonify(check)


def access(load_id, number, stage, check_id):
    require_stage(stage)
    load = get_load(load_id)
    ensure_open(load.truck)
    court = deepcopy(get_court(load, number))
    if not approved(load.truck) and not legacy_in_progress(load.truck) and not request.path.endswith('/pause'):
        fail('La planificacion necesita revision del supervisor.', 409)
    if stage in (0, 4):
        court['productos'] = task_products(load, court, stage)
    state = deepcopy(load.truck.state)
    cs = edit_court(state, load.id, number)
    check = cs['checks'].get(str(stage))
    if not check or check['id'] != check_id:
        fail('El control fue reabierto. Volvé a seleccionar la cancha.', 409)
    if check['user_id'] != g.current_user.id:
        fail('No es tu control.', 403)
    if check['status'] != 'active':
        fail('Control finalizado.', 409)
    return load, court, state, cs, check


@load_control_bp.post('/loads/<int:load_id>/courts/<int:number>/checks/<int:stage>/<check_id>/answer')
@auth_required
def answer(load_id, number, stage, check_id):
    data = body()
    load, court, state, cs, check = access(load_id, number, stage, check_id)
    sku = str(data.get('sku', ''))
    prod = next((p for p in court['productos'] if p['sku'] == sku), None)
    if not prod:
        fail('Producto inexistente.', 404)
    if stage in (0, 4) and data.get('result') == 'corrected':
        fail('En picking solo se registra correcto o faltante.')
    if not check.get('timer_started_at'):
        fail('Reanud? el proceso antes de registrar productos.', 409)
    result = data.get('result')
    note = str(data.get('note') or '').strip()[:2000]
    if result not in ('ok', 'corrected', 'shortage'):
        fail('Resultado inválido.')
    shortages = cs['shortages'] if stage in (1, 2) else cs.setdefault('preparation_shortages', {}).setdefault(str(stage), {})
    shortage = shortages.get(sku)
    confirmation = stage == 2 and result == 'shortage' and shortage is not None
    incident = shortage.get('incident') if confirmation else None
    if result in ('corrected', 'shortage') and not confirmation:
        responsible_id = g.current_user.id if stage in (0, 4) else data.get('responsible_user_id')
        origin = 'picking' if stage in (0, 4) else data.get('origin')
        responsible = db.session.get(User, responsible_id) if type(responsible_id) is int else None
        if not responsible or not responsible.active or origin not in ('picking', 'control'):
            fail('Indic? el responsable del error y si corresponde a picking o control.')
        incident = dict(responsible_user_id=responsible.id, responsible_username=responsible.username,
                        origin=origin, detected_by=g.current_user.id, detected_username=g.current_user.username)
    shortages = cs['shortages'] if stage in (1, 2) else cs.setdefault('preparation_shortages', {}).setdefault(str(stage), {})
    shortage = shortages.get(sku)
    if result == 'shortage':
        b, u = data.get('physical_b'), data.get('physical_u')
        if type(b) is not int or type(u) is not int or min(b, u) < 0:
            fail('Ingresá cantidades físicas enteras y no negativas.')
        if b > prod['bultos'] or u > prod['unidades'] or (b, u) == (prod['bultos'], prod['unidades']):
            fail('El faltante debe ser menor a la cantidad de la planilla.')
        if stage == 2:
            if not shortage or (shortage['actual_b'], shortage['actual_u']) != (b, u):
                fail('La cantidad difiere del primer control. Un supervisor debe reabrir la cancha.', 409)
        else:
            shortages[sku] = dict(sku=sku, descripcion=prod['descripcion'],
                expected_b=prod['bultos'], expected_u=prod['unidades'], actual_b=b, actual_u=u,
                reported_by=g.current_user.id, note=note, created_at=now(), incident=incident)
    else:
        b, u = prod['bultos'], prod['unidades']
        if result == 'corrected' and not note:
            fail('Describí la diferencia corregida.')
        if shortage and stage == 2:
            fail('Este SKU tiene un faltante declarado. Confirmalo o pedí reapertura al supervisor.', 409)
        if shortage:
            del shortages[sku]
    check['answers'][sku] = dict(sku=sku, result=result, physical_b=b, physical_u=u, note=note, incident=incident, saved_at=now(), user_id=g.current_user.id, username=g.current_user.username)
    if incident and not confirmation:
        state.setdefault('incidents', {})[f'{check_id}:{sku}'] = dict(check['answers'][sku],
            load_id=load.id, court=number, stage=stage, process_id=check_id, process_status=check['status'])
    save_state(load.truck, state, g.current_user, 'respuesta_control',
               dict(load_id=load.id, court=number, stage=stage, **check['answers'][sku]))
    return jsonify(check)


@load_control_bp.post('/loads/<int:load_id>/courts/<int:number>/checks/<int:stage>/<check_id>/finish')
@auth_required
def finish(load_id, number, stage, check_id):
    load, court, state, cs, check = access(load_id, number, stage, check_id)
    if stage != 0 and any(p['sku'] not in check['answers'] for p in court['productos']):
        fail('Hay productos pendientes de controlar.', 409)
    release_timer(check)
    check.update(status='done', finished_at=now())
    save_state(load.truck, state, g.current_user, 'finalizar_control', dict(load_id=load.id, court=number, stage=stage))
    return jsonify(ok=True)


@load_control_bp.post('/loads/<int:load_id>/courts/<int:number>/reopen')
@roles_required(*MANAGERS)
def reopen(load_id, number):
    reason = str(body().get('reason') or '').strip()
    if len(reason) < 3:
        fail('Ingresá el motivo de reapertura (mínimo 3 caracteres).')
    load = get_load(load_id)
    ensure_open(load.truck)
    get_court(load, number)
    state = deepcopy(load.truck.state)
    old = deepcopy(edit_court(state, load.id, number))
    for check in old['checks'].values():
        if check['stage'] in (0, 4) and check['status'] == 'done':
            continue
        release_timer(check)
        state.setdefault('archived_checks', []).append(dict(check, load_id=load.id, court=number, status='reopened'))
    keep = {stage: check for stage, check in old['checks'].items() if stage in ('0', '4') and check['status'] == 'done'}
    state['courts'][f'{load.id}:{number}'] = {'checks': keep, 'shortages': {}}
    old_assets = state.pop('assets', None)
    asset_check = state.pop('asset_check', None)
    if asset_check:
        release_timer(asset_check)
        state.setdefault('archived_checks', []).append(dict(asset_check, load_id=None, court=None, status='reopened'))
    save_state(load.truck, state, g.current_user, 'reabrir_cancha',
        dict(load_id=load.id, court=number, reason=reason[:2000], previous=old, invalidated_assets=old_assets))
    return jsonify(ok=True)


@load_control_bp.post('/loads/<int:load_id>/courts/<int:number>/shortages/<sku>/<action>')
@roles_required(*MANAGERS)
def shortage_action(load_id, number, sku, action):
    load = get_load(load_id)
    state = deepcopy(load.truck.state)
    cs = edit_court(state, load.id, number)
    sh = cs['shortages'].get(sku)
    if not sh:
        fail('Faltante no encontrado.', 404)
    if action == 'approve':
        if not court_done(cs):
            fail('Completá ambos controles antes de autorizar el faltante.', 409)
        if not sh.get('approved_by'):
            sh.update(approved_by=g.current_user.id, approved_at=now())
    elif action == 'adjusted':
        if not sh.get('approved_by'):
            fail('Primero debe autorizarse el faltante.', 409)
        if not sh.get('adjusted_by'):
            sh.update(adjusted_by=g.current_user.id, adjusted_at=now())
    else:
        fail('Acción inválida.', 404)
    save_state(load.truck, state, g.current_user, 'faltante_' + action, dict(load_id=load.id, court=number, sku=sku))
    return jsonify(ok=True)


@load_control_bp.get('/asset-types')
@auth_required
def asset_types():
    return jsonify(ASSET_NAMES)


@load_control_bp.post('/trucks/<int:truck_id>/assets')
@roles_required('administrador', 'supervisor', 'controlador')
def assets(truck_id):
    truck = get_truck(truck_id)
    require_truck_courts(truck)
    ensure_open(truck)
    quantities = body().get('quantities')
    if not isinstance(quantities, dict) or set(quantities) != set(ASSET_NAMES) or any(type(v) is not int or v < 0 for v in quantities.values()):
        fail('Completá todos los activos con enteros no negativos, incluido cero.')
    if not status(truck)['complete']:
        fail('Primero completá el doble control de todas las planillas.', 409)
    if truck.state.get('assets'):
        fail('Activos ya registrados.', 409)
    state = deepcopy(truck.state)
    check = state.get('asset_check')
    if not check or check['user_id'] != g.current_user.id or check['status'] != 'active':
        fail('Primero inici? el registro de activos con tu usuario.', 409)
    release_timer(check)
    check.update(status='done', finished_at=now())
    state['assets'] = dict(quantities=quantities, user_id=g.current_user.id, created_at=now())
    save_state(truck, state, g.current_user, 'registrar_activos', quantities)
    return jsonify(status(truck))


@load_control_bp.get('/users')
@roles_required(*MANAGERS)
def users():
    return jsonify([dict(**current_user_payload(u), active=u.active, courts=assigned_courts(u.id)) for u in User.query.order_by(User.username).all()])


@load_control_bp.post('/users')
@roles_required('administrador')
def create_user():
    try:
        user = register_user(body(), g.current_user, default_role='controlador')
    except UserCreationError as exc:
        fail(str(exc), exc.status)
    return jsonify(current_user_payload(user)), 201


@load_control_bp.get('/trucks/<int:truck_id>/audit')
@roles_required(*MANAGERS)
def truck_audit(truck_id):
    import json
    get_truck(truck_id)
    rows = db.session.query(LogEntry, User.username).outerjoin(User, User.id == LogEntry.user_id).filter(
        LogEntry.entity == 'control_cargas', LogEntry.entity_id == truck_id).order_by(LogEntry.id.desc()).all()
    return jsonify([dict(id=r.id, action=r.action, username=name, at=r.timestamp.isoformat(),
                         details=json.loads(r.details or '{}')) for r, name in rows])


@load_control_bp.post('/loads/<int:load_id>/courts/<int:number>/checks/<int:stage>/<check_id>/pause')
@auth_required
def pause(load_id, number, stage, check_id):
    load, court, state, cs, check = access(load_id, number, stage, check_id)
    release_timer(check)
    save_state(load.truck, state, g.current_user, 'pausar_proceso', dict(load_id=load.id, court=number, stage=stage))
    return jsonify(check)


@load_control_bp.get('/operators')
@auth_required
def operators():
    return jsonify([dict(id=u.id, username=u.username, role=u.role.name)
                    for u in User.query.filter_by(active=True).order_by(User.username).all() if manager() or g.current_user.role.name == 'controlador' or u.id == g.current_user.id])


@load_control_bp.get('/performance')
@roles_required(*MANAGERS)
def performance():
    processes, incidents = [], []
    query = ControlTruck.query.options(selectinload(ControlTruck.loads))
    if request.args.get('date'):
        query = query.filter_by(load_date=request.args['date'])
    for truck in query.all():
        entries = list(truck.state.get('archived_checks', []))
        if truck.state.get('asset_check'):
            entries.append(dict(truck.state['asset_check'], load_id=None, court=None))
        for load in truck.loads:
            for court in load.content['canchas']:
                cs = court_state(truck.state, load.id, court['numero'])
                entries.extend(dict(c, load_id=load.id, court=court['numero']) for c in cs['checks'].values())
        for check in entries:
            entry = dict(truck=truck.truck, date=truck.load_date, branch=truck.branch,
                         **{k: v for k, v in check.items() if k != 'answers'}, answered=len(check.get('answers', {})), elapsed_seconds=elapsed(check), timing=timing(check))
            processes.append(entry)
        for incident in truck.state.get('incidents', {}).values():
            process = next((c for c in entries if c['id'] == incident['process_id']), {})
            incidents.append(dict(incident, process_status=process.get('status', 'reopened'),
                truck=truck.truck, date=truck.load_date))
    return jsonify(processes=processes, incidents=incidents)


@load_control_bp.post('/trucks/<int:truck_id>/assets/<action>')
@roles_required('administrador', 'supervisor', 'controlador')
def asset_timer(truck_id, action):
    truck = get_truck(truck_id)
    require_truck_courts(truck)
    ensure_open(truck)
    if not status(truck)['complete'] or truck.state.get('assets'):
        fail('Los controles deben estar completos y los activos pendientes.', 409)
    state = deepcopy(truck.state)
    check = state.get('asset_check')
    if check and check['user_id'] != g.current_user.id:
        fail('Registro de activos reservado por otro empleado.', 409)
    if action == 'start':
        if not check:
            check = dict(id=uuid4().hex, stage=3, user_id=g.current_user.id, username=g.current_user.username,
                         status='active', started_at=now(), active_seconds=0, answers={})
            state['asset_check'] = check
        reserve_timer(check)
        if not check.get('timer_started_at'):
            check['timer_started_at'] = now()
    elif action == 'pause' and check:
        release_timer(check)
    else:
        fail('Acción inválida.')
    save_state(truck, state, g.current_user, 'activos_' + action, {})
    return jsonify(check)


def planning_rows(truck):
    if not hasattr(request, 'planning_catalog'):
        request.planning_catalog = {a.sku: a for a in Article.query.filter_by(activo=True).all()}
    catalog = request.planning_catalog
    rows = []
    for load in sorted(selected_loads(truck), key=lambda l: (l.source_id or l.id, l.id)):
        for court in load.content['canchas']:
            for product in court['productos']:
                article = catalog.get(product['sku'])
                rows.append(dict(load_id=load.id, reparto=load.reparto, court=court['numero'],
                    sku=product['sku'], descripcion=product['descripcion'], bultos=product['bultos'],
                    unidades=product['unidades'], bultos_por_pallet=article.bultos_por_pallet if article else None,
                    unidades_por_bulto=article.unidades_por_bulto if article else None))
    return rows


@load_control_bp.get('/my-courts')
@auth_required
def my_courts():
    return jsonify(courts=assigned_courts(g.current_user.id))


@load_control_bp.put('/users/<int:user_id>/courts')
@roles_required(*MANAGERS)
def assign_courts(user_id):
    user = db.session.query(User).filter_by(id=user_id).with_for_update().first()
    if not user or user.role.name not in ('operador', 'controlador', 'palletizador'):
        fail('Selecciona un operario o controlador.', 400)
    try:
        numbers = validate_courts(body().get('courts'))
    except ValueError as exc:
        fail(str(exc))
    previous = assigned_courts(user_id)
    # Stop and release unfinished reservations on revoked courts, retaining answers and audit.
    for truck in ControlTruck.query.order_by(ControlTruck.id).with_for_update().populate_existing().all():
        state = deepcopy(truck.state)
        changed = False
        for key, court in state.get('courts', {}).items():
            if int(key.split(':')[1]) in numbers:
                continue
            for stage, check in list(court.get('checks', {}).items()):
                if check['user_id'] == user_id and check['status'] == 'active':
                    release_timer(check)
                    state.setdefault('archived_checks', []).append(dict(check, id=uuid4().hex, original_id=check['id'], finished_at=now(), load_id=int(key.split(':')[0]), court=int(key.split(':')[1]), status='reassigned'))
                    check.update(user_id=None, username='Sin asignar', started_at=None, active_seconds=0)
                    changed = True
        if changed:
            truck.state = state
            audit(g.current_user, 'reasignar_canchas', truck, dict(user_id=user_id, previous=previous, courts=numbers))
    UserCourt.query.filter_by(user_id=user_id).delete()
    for number in numbers:
        db.session.add(UserCourt(user_id=user_id, court_number=number))
    db.session.add(LogEntry(user_id=g.current_user.id, action='asignar_canchas', entity='users', entity_id=user_id,
        details=json.dumps(dict(previous=previous, courts=numbers))))
    db.session.commit()
    return jsonify(courts=numbers)


@load_control_bp.get('/settings')
@roles_required(*MANAGERS)
def warehouse_settings():
    return jsonify(depots=[dict(branch=d.branch, mix_courts_default=d.mix_courts_default) for d in DepotSettings.query.all()],
        trucks=[dict(branch=t.branch, truck=t.truck, capacity=t.pallet_capacity) for t in TruckCapacity.query.all()])


@load_control_bp.put('/settings')
@roles_required('administrador')
def save_settings():
    data = body()
    branch = str(data.get('branch') or '').strip()
    name = truck_name(data.get('truck'))
    capacity, mix = data.get('capacity'), data.get('mix_courts_default')
    if not branch or len(branch) > 255 or not name or len(name) > 255 or type(capacity) is not int or capacity <= 0 or type(mix) is not bool:
        fail('Completa deposito, camion, capacidad entera positiva y preferencia de mezcla.')
    for truck in ControlTruck.query.filter_by(branch=branch, truck=name).all():
        old = truck.state.get('planning')
        if old and old['capacity'] != capacity and not truck.state.get('released_at') and any(c.get('checks') for c in truck.state.get('courts', {}).values()):
            fail('El camion tiene trabajo iniciado. Finalizalo antes de cambiar su capacidad.', 409)
    depot = db.session.get(DepotSettings, branch)
    if not depot:
        depot = DepotSettings(branch=branch)
        db.session.add(depot)
    depot.mix_courts_default = mix
    db.session.flush()
    entry = db.session.get(TruckCapacity, (branch, name))
    if not entry:
        entry = TruckCapacity(branch=branch, truck=name)
        db.session.add(entry)
    entry.pallet_capacity = capacity
    db.session.add(LogEntry(user_id=g.current_user.id, action='configurar_capacidad', entity='camiones',
        details=json.dumps(dict(branch=branch, truck=name, capacity=capacity, mix_courts_default=mix))))
    db.session.commit()
    return jsonify(ok=True)


@load_control_bp.post('/trucks/<int:truck_id>/planning/approve')
@roles_required(*MANAGERS)
def approve_plan(truck_id):
    truck = get_truck(truck_id)
    ensure_open(truck)
    data = body()
    if data.get('version') != truck.version:
        fail('La carga cambio. Volve a simular antes de aprobar.', 409)
    if any(c.get('checks') for c in truck.state.get('courts', {}).values()):
        fail('El trabajo ya comenzo; no se puede reemplazar el plan.', 409)
    capacity = db.session.get(TruckCapacity, (truck.branch, truck.truck))
    if not capacity or data.get('capacity') != capacity.pallet_capacity:
        fail('La capacidad debe coincidir con la configurada por administracion.', 409)
    mix = data.get('mix_courts')
    fingerprint = plan_fingerprint(truck, capacity.pallet_capacity, mix)
    if status(truck)['pending_sources'] or data.get('fingerprint') != fingerprint:
        fail('Los productos o la configuracion cambiaron. Volve a simular.', 409)
    if data.get('physical_review') is not True:
        fail('Confirma la revision fisica de altura, estabilidad y compatibilidad.')
    try:
        plan = plan_for_capacity(planning_rows(truck), capacity.pallet_capacity, mix)
    except ValueError as exc:
        fail(str(exc))
    if not plan['fits_estimate']:
        fail('El armado excede la capacidad del camion.', 409)
    if plan['mix_courts'] != mix:
        fail('El armado requiere combinar canchas. Volve a simular y revisar la propuesta.', 409)
    plan.update(fingerprint=fingerprint, approved_at=now(), approved_by=g.current_user.id)
    from datetime import datetime
    started = truck.state.get('planning_started_at')
    requested = truck.state.get('planning_requested_at')
    plan['review_seconds'] = (datetime.fromisoformat(plan['approved_at']) - datetime.fromisoformat(started)).total_seconds() if started else None
    plan['waiting_seconds'] = (datetime.fromisoformat(plan['approved_at']) - datetime.fromisoformat(requested)).total_seconds() if requested else None
    state = deepcopy(truck.state)
    state['planning'] = plan
    save_state(truck, state, g.current_user, 'aprobar_planificacion', dict(fingerprint=fingerprint, capacity=capacity.pallet_capacity, mix_courts=mix, review_seconds=plan['review_seconds'], waiting_seconds=plan['waiting_seconds']))
    return jsonify(ok=True, approved_at=plan['approved_at'])


@load_control_bp.get('/monitor')
@roles_required(*MANAGERS)
def warehouse_monitor():
    date = request.args.get('date', now()[:10])
    try:
        from datetime import date as date_type
        date_type.fromisoformat(date)
    except ValueError:
        fail('Fecha invalida.')
    rows = []
    summaries = []
    trucks = ControlTruck.query.filter_by(load_date=date).options(selectinload(ControlTruck.loads)).all()
    for truck in trucks:
        if truck.state.get('dispatch') is not None and not selected_loads(truck):
            continue
        plan = approved(truck)
        assets = truck.state.get('asset_check') or {}
        summaries.append(dict(id=truck.id, truck=truck.truck, branch=truck.branch,
            planning='approved' if plan else 'legacy' if legacy_in_progress(truck) else 'pending',
            released=bool(truck.state.get('released_at')),
            assets_status='done' if assets.get('status') == 'done' else 'running' if assets.get('timer_started_at') else 'paused' if assets else 'pending',
            assets_username=assets.get('username'), position=truck.state.get('dispatch', {}).get('position'),
            summary=truck_summary(truck, dispatch_catalog(), valid=bool(plan))))
        for load in selected_loads(truck):
            for court in load.content['canchas']:
                cs = court_state(truck.state, load.id, court['numero'])
                for stage in (0, 4, 1, 2):
                    products = task_products(load, court, stage) if stage in (0, 4) else court['productos']
                    if not products:
                        continue
                    check = cs['checks'].get(str(stage), {})
                    answers = check.get('answers', {})
                    answered = sum(p['sku'] in answers for p in products)
                    rows.append(dict(id=f'{load.id}:{court["numero"]}:{stage}', load_id=load.id,
                        truck=truck.truck, reparto=load.reparto, branch=truck.branch, court=court['numero'],
                        stage=stage, user_id=check.get('user_id'), username=check.get('username'),
                        status='pending' if not check else 'done' if check['status']=='done' else 'running' if check.get('timer_started_at') else 'paused',
                        answered=answered, personal_answered=sum(a.get('user_id') == check.get('user_id') for a in answers.values() if check.get('user_id')), total=len(products), elapsed_seconds=elapsed(check), timing=timing(check),
                        shortages=sum(a['result']=='shortage' for a in answers.values()),
                        planning='approved' if plan else 'legacy' if legacy_in_progress(truck) else 'pending'))
    from datetime import datetime, timedelta
    # The warehouse day is Argentina (UTC-3); stored audit timestamps are UTC.
    day_start = datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=3)
    latest = db.session.query(LogEntry, User.username).outerjoin(User, LogEntry.user_id == User.id).filter(
        LogEntry.timestamp >= day_start, LogEntry.timestamp < day_start + timedelta(days=1),
        LogEntry.entity != 'api_activity').order_by(LogEntry.id.desc()).limit(12).all()
    return jsonify(date=date, updated_at=now(), processes=rows, trucks=summaries,
        events=[dict(id=event.id, action=event.action, username=username, at=event.timestamp.isoformat()+'Z') for event, username in latest],
        operators=[dict(id=u.id, username=u.username, role=u.role.name, courts=assigned_courts(u.id))
            for u in User.query.filter_by(active=True).all() if u.role.name in ('operador','palletizador','controlador')])


@load_control_bp.post('/trucks/<int:truck_id>/planning/start')
@roles_required(*MANAGERS)
def start_planning(truck_id):
    truck = get_truck(truck_id)
    if truck.state.get('planning_started_at'):
        return jsonify(started_at=truck.state['planning_started_at'])
    ensure_open(truck)
    state = deepcopy(truck.state)
    state['planning_started_at'] = now()
    save_state(truck, state, g.current_user, 'iniciar_planificacion', {})
    return jsonify(started_at=state['planning_started_at'])


@load_control_bp.get('/activity')
@roles_required(*MANAGERS)
def activity():
    date = request.args.get('date', now()[:10])
    from datetime import datetime, timedelta
    try:
        start = datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=3)
    except ValueError:
        fail('Fecha invalida.')
    rows = db.session.query(LogEntry, User.username).outerjoin(User, LogEntry.user_id == User.id).filter(
        LogEntry.timestamp >= start, LogEntry.timestamp < start + timedelta(days=1))
    before = request.args.get('before', type=int)
    if before:
        rows = rows.filter(LogEntry.id < before)
    records = rows.order_by(LogEntry.id.desc()).limit(100).all()
    return jsonify(events=[dict(id=r.id, username=name, action=r.action, entity=r.entity,
        at=r.timestamp.isoformat()+'Z', details=json.loads(r.details or '{}') if (r.details or '').startswith('{') else {}) for r, name in records],
        next_before=records[-1][0].id if len(records) == 100 else None)


@load_control_bp.get('/trucks/<int:truck_id>/planning')
@roles_required(*MANAGERS)
def saved_plan(truck_id):
    truck = get_truck(truck_id)
    return jsonify(plan=truck.state.get('planning'), locked=any(c.get('checks') for c in truck.state.get('courts', {}).values()), version=truck.version)
