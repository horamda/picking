"""Snapshots de carga y estado transaccional del doble control.

El documento de estado se reemplaza completo y se protege con version_id:
dos empleados no pueden sobrescribir reservas, respuestas o liberaciones.
"""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import re

from utils.db import db
from models import LogEntry, Consolidado
from sqlalchemy import func


class ControlTruck(db.Model):
    __tablename__ = 'control_camiones'
    id = db.Column(db.Integer, primary_key=True)
    branch = db.Column(db.String(255), nullable=False)
    load_date = db.Column(db.String(10), nullable=False)
    truck = db.Column(db.String(255), nullable=False)
    state = db.Column(db.JSON, nullable=False, default=dict)
    version = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint('branch', 'load_date', 'truck'),)
    __mapper_args__ = {'version_id_col': version}


class ControlLoad(db.Model):
    __tablename__ = 'control_planillas'
    id = db.Column(db.Integer, primary_key=True)
    truck_id = db.Column(db.Integer, db.ForeignKey('control_camiones.id'), nullable=False)
    branch = db.Column(db.String(255), nullable=False)
    load_date = db.Column(db.String(10), nullable=False)
    reparto = db.Column(db.String(120), nullable=False)
    source_id = db.Column(db.Integer, unique=True, nullable=True)
    content = db.Column(db.JSON, nullable=False)
    truck = db.relationship(ControlTruck, backref='loads')
    __table_args__ = (db.UniqueConstraint('branch', 'load_date', 'reparto'),)


class ControlTimer(db.Model):
    __tablename__ = 'control_temporizadores'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    check_id = db.Column(db.String(32), unique=True, nullable=False)



ASSET_NAMES = ['Esqueletos litro X12', 'Botellas litro X12', 'Barriles 20 L',
               'Barriles 30 L', 'Barriles 50 L', 'Pallets CHEP', 'Pallets BEES',
               'Tuppers', 'Carros', 'Chapadurs']


def now():
    return datetime.now(timezone.utc).isoformat()


def elapsed(check):
    seconds = check.get('active_seconds', 0)
    if check.get('timer_started_at'):
        seconds += max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(check['timer_started_at'])).total_seconds())
    return round(seconds, 1)


def timing(check):
    active = elapsed(check)
    start = check.get('started_at')
    end = check.get('finished_at')
    wall = max(0, ((datetime.fromisoformat(end) if end else datetime.now(timezone.utc)) - datetime.fromisoformat(start)).total_seconds()) if start else 0
    return dict(active_seconds=active, wall_seconds=round(wall, 1), paused_seconds=round(max(0, wall-active), 1))


def stop_timer(check):
    check['active_seconds'] = elapsed(check)
    check['timer_started_at'] = None


def truck_name(value):
    value = str(value or '').strip()
    match = re.search(r'\(([^)]+)\)', value)
    return (match.group(1) if match else value).strip().upper()


def court_key(load_id, court):
    return f'{load_id}:{court}'


def court_state(state, load_id, court):
    return state.get('courts', {}).get(court_key(load_id, court), {'checks': {}, 'shortages': {}})


def edit_court(state, load_id, court):
    return state.setdefault('courts', {}).setdefault(court_key(load_id, court), {'checks': {}, 'shortages': {}})


def court_done(court):
    return all(court['checks'].get(str(stage), {}).get('status') == 'done' for stage in (1, 2))


def status(truck, state=None):
    state = truck.state if state is None else state
    complete = bool(truck.loads) and all(
        court_done(court_state(state, load.id, c['numero']))
        for load in truck.loads for c in load.content['canchas'])
    shortages = [dict(sh, load_id=load.id, reparto=load.reparto, court=c['numero'])
                 for load in truck.loads for c in load.content['canchas']
                 for sh in court_state(state, load.id, c['numero'])['shortages'].values()]
    start_date = datetime.fromisoformat(truck.load_date)
    candidates = Consolidado.query.filter(Consolidado.fecha_reparto >= start_date,
        Consolidado.fecha_reparto < start_date + timedelta(days=1),
        func.trim(Consolidado.deposito) == truck.branch).all()
    included = {l.source_id for l in truck.loads}
    pending = [c.id for c in candidates if truck_name(c.camion) == truck.truck and c.id not in included]
    complete = complete and not pending
    return dict(complete=complete, pending_sources=pending, assets=state.get('assets'), shortages=shortages,
                released_at=state.get('released_at'),
                allowed=complete and bool(state.get('assets')) and all(s.get('approved_by') for s in shortages))


def audit(user, action, truck, details):
    import json
    db.session.add(LogEntry(user_id=user.id, action=action, entity='control_cargas',
                            entity_id=truck.id, details=json.dumps(details, ensure_ascii=False)))


def save_state(truck, state, user, action, details):
    may_release = action in ('finalizar_control', 'faltante_approve', 'registrar_activos')
    if may_release and not state.get('released_at') and status(truck, state)['allowed']:
        state['released_at'] = now()
        audit(user, 'liberacion_en_aplicacion', truck, {})
    truck.state = deepcopy(state)
    audit(user, action, truck, details)
    db.session.commit()


def snapshot(consolidado):
    """Cantidades originales: incluye todos los SKU, sin exclusiones de picking."""
    if not all([consolidado.reparto, consolidado.camion, consolidado.deposito, consolidado.fecha_reparto]):
        raise ValueError('El reparto necesita fecha de reparto, camión y depósito antes de controlar.')
    courts = {}
    for item in sorted(consolidado.detalles, key=lambda x: x.id):
        match = re.fullmatch(r'(?:\d+\s*-\s*)?(?:CANCHA\s*)?(\d+)', str(item.cancha or '').strip(), re.I)
        if not match:
            raise ValueError(f'El SKU {item.sku} no tiene una cancha reconocible. Revisá el PDF original.')
        number = int(match.group(1))
        products = courts.setdefault(number, {})
        product = products.setdefault(item.sku, dict(sku=item.sku, descripcion=item.descripcion,
            almacen=item.almacen, bultos=0, unidades=0, lineas_originales=[]))
        if (item.bultos or 0) < 0 or (item.unidades or 0) < 0:
            raise ValueError('No se admiten cantidades negativas.')
        product['bultos'] += item.bultos or 0
        product['unidades'] += item.unidades or 0
        product['lineas_originales'].append(dict(detalle_id=item.id, almacen=item.almacen,
            bultos=item.bultos or 0, unidades=item.unidades or 0))
    if not courts:
        raise ValueError('El reparto no tiene productos.')
    return dict(reparto=consolidado.reparto, camion=truck_name(consolidado.camion),
        deposito=consolidado.deposito.strip(), fecha=consolidado.fecha_reparto.date().isoformat(),
        chofer=consolidado.chofer, canchas=[dict(numero=n, productos=list(p.values())) for n, p in courts.items()])
