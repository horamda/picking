"""Published weekly staffing; future plans never replace today's assignments early."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import os
from utils.db import db


class StaffingWeek(db.Model):
    __tablename__ = 'staffing_weeks'
    week_start = db.Column(db.Date, primary_key=True)
    draft = db.Column(db.JSON, nullable=False, default=dict)
    published = db.Column(db.JSON, nullable=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    activated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    __mapper_args__ = {'version_id_col': version}


def enabled():
    return os.getenv('STAFFING_ENABLED') == '1'


def local_day():
    return datetime.now(timezone(timedelta(hours=-3))).date()


def monday(value):
    day = date.fromisoformat(value)
    if day.weekday() != 0:
        raise ValueError('Seleccioná el lunes de la semana.')
    return day


def release_removed(user_id, courts, actor):
    from services.load_control import ControlTruck, audit, now
    from routes.load_control import release_timer
    from uuid import uuid4
    for truck in ControlTruck.query.order_by(ControlTruck.id).with_for_update().populate_existing().all():
        state, changed = deepcopy(truck.state), False
        for key, cs in state.get('courts', {}).items():
            if int(key.split(':')[1]) in courts:
                continue
            for check in cs.get('checks', {}).values():
                if check.get('user_id') == user_id and check.get('status') == 'active':
                    release_timer(check)
                    state.setdefault('archived_checks', []).append(dict(check, id=uuid4().hex,
                        original_id=check['id'], finished_at=now(), load_id=int(key.split(':')[0]),
                        court=int(key.split(':')[1]), status='reassigned'))
                    check.update(user_id=None, username='Sin asignar', started_at=None, active_seconds=0)
                    changed = True
        if changed:
            truck.state = state
            audit(actor, 'rotacion_semanal', truck, dict(user_id=user_id, courts=courts))


def activate_due_week(today=None):
    if not enabled():
        return False
    from models import User, LogEntry
    from services.warehouse import UserCourt, assigned_courts
    import json
    today = today or local_day()
    start = today - timedelta(days=today.weekday())
    plan = StaffingWeek.query.filter_by(week_start=start).with_for_update().first()
    if not plan or plan.published is None or plan.activated_at:
        db.session.rollback()
        return False
    actor = db.session.get(User, plan.published_by)
    ids = sorted(int(k) for k in plan.published)
    users = User.query.filter(User.id.in_(ids)).order_by(User.id).with_for_update().all()
    for user in users:
        courts = plan.published[str(user.id)] if user.active else []
        if assigned_courts(user.id) == courts:
            continue
        release_removed(user.id, courts, actor)
        UserCourt.query.filter_by(user_id=user.id).delete()
        for number in courts:
            db.session.add(UserCourt(user_id=user.id, court_number=number))
    plan.activated_at = datetime.now(timezone.utc)
    db.session.add(LogEntry(user_id=actor.id, action='activar_semana', entity='planificacion_equipo',
        details=json.dumps(dict(week=start.isoformat(), assignments=plan.published))))
    db.session.commit()
    return True
