from copy import deepcopy
from uuid import uuid4

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import HTTPException

from auth import auth_required, roles_required, current_user_payload
from models import Consolidado, User, LogEntry
from services.load_control import (ControlTruck, ControlLoad, ControlTimer, ASSET_NAMES, now, truck_name,
    court_state, edit_court, court_done, status, save_state, snapshot, audit, elapsed, stop_timer)
from utils.db import db
from services.users import create_user as register_user, UserCreationError

load_control_bp = Blueprint('load_control', __name__)
MANAGERS = ('administrador', 'supervisor')


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
    truck = db.session.get(ControlTruck, truck_id)
    if not truck:
        fail('Camión no encontrado.', 404)
    return truck


def get_load(load_id):
    load = db.session.get(ControlLoad, load_id)
    if not load:
        fail('Planilla no encontrada.', 404)
    return load


def ensure_open(truck):
    if truck.state.get('released_at'):
        fail('Camión liberado: no se permiten cambios en los controles.', 409)


def get_court(load, number):
    court = next((c for c in load.content['canchas'] if c['numero'] == number), None)
    if not court:
        fail('Cancha inexistente.', 404)
    return court


def serialize_load(load, summary=False):
    result = dict(id=load.id, source_id=load.source_id, **deepcopy(load.content))
    for court in result['canchas']:
        cs = court_state(load.truck.state, load.id, court['numero'])
        checks = [dict({k: v for k, v in check.items() if k != 'answers'}, elapsed_seconds=elapsed(check)) for check in cs['checks'].values()]
        court['status'] = dict(checks=checks,
                               shortages=list(cs['shortages'].values()), done=court_done(cs))
        if summary:
            court['cantidad'] = len(court.pop('productos'))
    return result


def add_load(payload, source_id=None):
    payload['camion'] = truck_name(payload['camion'])
    payload['deposito'] = payload['deposito'].strip()
    key = dict(branch=payload['deposito'], load_date=payload['fecha'])
    if ControlLoad.query.filter_by(**key, reparto=payload['reparto']).first():
        fail(f"El reparto {payload['reparto']} ya está en Control de cargas.", 409)
    truck = ControlTruck.query.filter_by(**key, truck=payload['camion']).first()
    if truck:
        ensure_open(truck)
        if truck.state.get('assets'):
            fail('El camión ya tiene activos confirmados; no se pueden agregar planillas.', 409)
        # Bump the version even when only adding a snapshot: competes with release.
        state = deepcopy(truck.state)
        state['updated_at'] = now()
        truck.state = state
    else:
        truck = ControlTruck(**key, truck=payload['camion'], state={'courts': {}})
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
    return jsonify([dict(id=t.id, branch=t.branch, load_date=t.load_date, truck=t.truck,
        status=status(t), loads=[serialize_load(l, summary=True) for l in t.loads])
        for t in ControlTruck.query.options(selectinload(ControlTruck.loads)).order_by(ControlTruck.load_date.desc(), ControlTruck.id.desc()).all()])


@load_control_bp.get('/loads/<int:load_id>')
@auth_required
def load_detail(load_id):
    return jsonify(serialize_load(get_load(load_id)))


@load_control_bp.get('/sources')
@auth_required
def sources():
    used = db.session.query(ControlLoad.source_id).filter(ControlLoad.source_id.isnot(None))
    rows = Consolidado.query.filter(~Consolidado.id.in_(used)).order_by(Consolidado.id.desc()).all()
    return jsonify([dict(id=c.id, reparto=c.reparto, camion=c.camion, deposito=c.deposito,
        fecha=c.fecha_reparto.isoformat() if c.fecha_reparto else None) for c in rows])


@load_control_bp.post('/sources/<int:source_id>')
@auth_required
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
    if stage not in (0, 1, 2):
        fail('Etapa inválida.')
    load = get_load(load_id)
    ensure_open(load.truck)
    get_court(load, number)
    state = deepcopy(load.truck.state)
    cs = edit_court(state, load.id, number)
    if stage == 0 and any(str(n) in cs['checks'] for n in (1, 2)):
        fail('El control ya comenz?; no se puede iniciar picking retroactivamente.', 409)
    if stage == 1 and cs['checks'].get('0', {}).get('status') == 'active':
        fail('Primero debe finalizar el picking en curso.', 409)
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
    return jsonify(check)


def access(load_id, number, stage, check_id):
    load = get_load(load_id)
    ensure_open(load.truck)
    court = get_court(load, number)
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
    if stage == 0:
        fail('El picking se finaliza desde su proceso; las respuestas corresponden a controles.')
    if not check.get('timer_started_at'):
        fail('Reanud? el proceso antes de registrar productos.', 409)
    result = data.get('result')
    note = str(data.get('note') or '').strip()[:2000]
    if result not in ('ok', 'corrected', 'shortage'):
        fail('Resultado inválido.')
    shortage = cs['shortages'].get(sku)
    confirmation = stage == 2 and result == 'shortage' and shortage is not None
    incident = shortage.get('incident') if confirmation else None
    if result in ('corrected', 'shortage') and not confirmation:
        responsible_id = data.get('responsible_user_id')
        origin = data.get('origin')
        responsible = db.session.get(User, responsible_id) if type(responsible_id) is int else None
        if not responsible or not responsible.active or origin not in ('picking', 'control'):
            fail('Indic? el responsable del error y si corresponde a picking o control.')
        incident = dict(responsible_user_id=responsible.id, responsible_username=responsible.username,
                        origin=origin, detected_by=g.current_user.id, detected_username=g.current_user.username)
    shortage = cs['shortages'].get(sku)
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
            cs['shortages'][sku] = dict(sku=sku, descripcion=prod['descripcion'],
                expected_b=prod['bultos'], expected_u=prod['unidades'], actual_b=b, actual_u=u,
                reported_by=g.current_user.id, note=note, created_at=now(), incident=incident)
    else:
        b, u = prod['bultos'], prod['unidades']
        if result == 'corrected' and not note:
            fail('Describí la diferencia corregida.')
        if shortage and stage == 2:
            fail('Este SKU tiene un faltante declarado. Confirmalo o pedí reapertura al supervisor.', 409)
        if shortage:
            del cs['shortages'][sku]
    check['answers'][sku] = dict(sku=sku, result=result, physical_b=b, physical_u=u, note=note, incident=incident, saved_at=now())
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
        if check['stage'] == 0 and check['status'] == 'done':
            continue
        release_timer(check)
        state.setdefault('archived_checks', []).append(dict(check, load_id=load.id, court=number, status='reopened'))
    keep = {'0': old['checks']['0']} if old['checks'].get('0', {}).get('status') == 'done' else {}
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
@auth_required
def assets(truck_id):
    truck = get_truck(truck_id)
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
    return jsonify([dict(**current_user_payload(u), active=u.active) for u in User.query.order_by(User.username).all()])


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
                    for u in User.query.filter_by(active=True).order_by(User.username).all()])


@load_control_bp.get('/performance')
@roles_required(*MANAGERS)
def performance():
    processes, incidents = [], []
    for truck in ControlTruck.query.options(selectinload(ControlTruck.loads)).all():
        entries = list(truck.state.get('archived_checks', []))
        if truck.state.get('asset_check'):
            entries.append(dict(truck.state['asset_check'], load_id=None, court=None))
        for load in truck.loads:
            for court in load.content['canchas']:
                cs = court_state(truck.state, load.id, court['numero'])
                entries.extend(dict(c, load_id=load.id, court=court['numero']) for c in cs['checks'].values())
        for check in entries:
            entry = dict(truck=truck.truck, date=truck.load_date, branch=truck.branch,
                         **{k: v for k, v in check.items() if k != 'answers'}, elapsed_seconds=elapsed(check))
            processes.append(entry)
        for incident in truck.state.get('incidents', {}).values():
            process = next((c for c in entries if c['id'] == incident['process_id']), {})
            incidents.append(dict(incident, process_status=process.get('status', 'reopened'),
                truck=truck.truck, date=truck.load_date))
    return jsonify(processes=processes, incidents=incidents)


@load_control_bp.post('/trucks/<int:truck_id>/assets/<action>')
@auth_required
def asset_timer(truck_id, action):
    truck = get_truck(truck_id)
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
