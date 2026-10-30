"""Run as a separate Railway worker after the explicit push migration."""
import time
from datetime import timedelta
from sqlalchemy.orm import selectinload
from app import app
from models import User
from services.load_control import ControlTruck
from services.push import PushDevice, available_tasks, enabled, retry_delay, send_notice, utcnow
from utils.db import db


def process_device(device, tasks, sender=send_notice):
    stamp = utcnow()
    if set(tasks) - set(device.known_tasks or []):
        try:
            sender(device.token)
        except Exception as exc:
            # No token, credential or provider exception text in logs.
            if type(exc).__name__ in ('UnregisteredError', 'SenderIdMismatchError'):
                device.expires_at = stamp
            device.failures += 1
            device.next_attempt = stamp + timedelta(seconds=retry_delay(device.failures))
            return False
    device.known_tasks = tasks
    device.failures = 0
    device.next_attempt = stamp + timedelta(seconds=15)
    return True


def tick():
    stamp = utcnow()
    ids = [r[0] for r in db.session.query(PushDevice.token_hash).filter(
        PushDevice.expires_at > stamp, PushDevice.next_attempt <= stamp).limit(200).all()]
    db.session.remove()  # Also close the read transaction when no devices are registered.
    for device_id in ids:
        try:
            device = PushDevice.query.filter(PushDevice.token_hash == device_id,
                PushDevice.expires_at > utcnow(), PushDevice.next_attempt <= utcnow()).with_for_update(skip_locked=True).first()
            if device is None:
                db.session.rollback()
                continue
            user = db.session.get(User, device.user_id)
            trucks = ControlTruck.query.filter(ControlTruck.state['released_at'].as_string().is_(None)).options(selectinload(ControlTruck.loads)).all()
            tasks = available_tasks(user, trucks) if user else []
            process_device(device, tasks)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.error('No se pudo procesar un aviso de tareas; se reintentará.')
        finally:
            db.session.remove()


if __name__ == '__main__':
    import os
    if not enabled() or not os.getenv('FIREBASE_PROJECT_ID') or not (os.getenv('GOOGLE_APPLICATION_CREDENTIALS') or os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')):
        raise SystemExit('Faltan PUSH_ENABLED=1, FIREBASE_PROJECT_ID o la credencial de servidor.')
    with app.app_context():
        if db.engine.dialect.name != 'postgresql':
            raise SystemExit('El worker requiere PostgreSQL y la migración explícita.')
        from sqlalchemy import inspect
        if not inspect(db.engine).has_table('push_devices'):
            raise SystemExit('Falta aplicar la migración revisada 20261030_01.')
        print('Worker de avisos iniciado; PostgreSQL y migración verificados.', flush=True)
        while True:
            tick()
            time.sleep(15)
