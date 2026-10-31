"""Durable per-device notification state; no network calls in picking requests."""
from datetime import datetime, timedelta, timezone
import hashlib
import os
import json
from utils.db import db


def utcnow():
    return datetime.now(timezone.utc)


def enabled():
    return os.environ.get('PUSH_ENABLED') == '1'


class PushDevice(db.Model):
    __tablename__ = 'push_devices'
    token_hash = db.Column(db.String(64), primary_key=True)
    token = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    last_seen = db.Column(db.DateTime(timezone=True), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    known_tasks = db.Column(db.JSON, nullable=False, default=list)
    next_attempt = db.Column(db.DateTime(timezone=True), nullable=False)
    failures = db.Column(db.Integer, nullable=False, default=0)


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def retry_delay(failures):
    return min(3600, 30 * 2 ** min(failures, 7))


def available_tasks(user, trucks):
    # Reuse the approved plan, assigned courts and individual truck queue.
    from services.warehouse import assigned_courts
    from services.load_control import selected_loads, court_state
    from routes.load_control import approved, task_products
    from services.assistance import queue_for, can_access, personal_check, products_for, usable
    if not user.active or user.role.name not in ('operador', 'palletizador'):
        return []
    stage = 4 if user.role.name == 'palletizador' else 0
    courts = assigned_courts(user.id)
    queue = queue_for(trucks, courts, stage, user.id, task_products)
    if not queue or not approved(queue[0]):
        return []
    truck = queue[0]
    result = []
    for load in selected_loads(truck):
        for court in load.content['canchas']:
            number = court['numero']
            if (number not in courts and not can_access(load, number, user.id, stage)) or not products_for(load, court, stage, user.id, task_products(load, court, stage)):
                continue
            checks = court_state(truck.state, load.id, number)['checks']
            check = personal_check(court_state(truck.state, load.id, number), stage, user.id) or {}
            if check.get('day') and not usable(check):
                continue
            if check.get('status') == 'done' or (check and check.get('user_id') != user.id):
                continue
            if checks.get('1') or checks.get('2'):
                continue
            result.append(f'{load.id}:{number}:{stage}')
    return sorted(result)


def send_notice(token):
    import firebase_admin
    from firebase_admin import credentials, messaging
    try:
        app = firebase_admin.get_app('picking-push')
    except ValueError:
        raw = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
        credential = credentials.Certificate(json.loads(raw)) if raw else credentials.ApplicationDefault()
        app = firebase_admin.initialize_app(credential,
            {'projectId': os.environ['FIREBASE_PROJECT_ID'], 'httpTimeout': 10}, name='picking-push')
    return messaging.send(messaging.Message(token=token,
        notification=messaging.Notification(title='Del Palacio · Picking',
            body='Tenés tareas habilitadas. Abrí la app para consultar tu próximo trabajo.'),
        android=messaging.AndroidConfig(priority='high', ttl=timedelta(minutes=15),
            collapse_key='picking_tasks', notification=messaging.AndroidNotification(
                channel_id='picking_tasks', tag='picking_tasks'))), app=app)
