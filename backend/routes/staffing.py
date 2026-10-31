"""Registered on the existing role-protected load_control blueprint."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from flask import jsonify, g, request
from auth import roles_required
from models import User, LogEntry
from services.staffing import StaffingWeek, enabled, monday, local_day
from services.warehouse import assigned_courts, validate_courts
from utils.db import db


def register(bp):
    from routes.load_control import fail, body, MANAGERS

    def week(day):
        if not enabled():
            fail('Planificación semanal pendiente de habilitar.', 503)
        try:
            return monday(day)
        except ValueError as error:
            fail(str(error))

    def payload(plan):
        return dict(week=plan.week_start.isoformat(), draft=plan.draft, published=plan.published,
            version=plan.version, published_at=plan.published_at.isoformat() if plan.published_at else None,
            activated_at=plan.activated_at.isoformat() if plan.activated_at else None)

    @bp.get('/staffing/weeks/<day>')
    @roles_required(*MANAGERS)
    def staffing_get(day):
        start = week(day)
        plan = db.session.get(StaffingWeek, start)
        if plan:
            return jsonify(payload(plan))
        users = User.query.filter_by(active=True).all()
        draft = {str(u.id): assigned_courts(u.id) for u in users if u.role.name in ('operador','palletizador','controlador')}
        return jsonify(week=start.isoformat(), draft=draft, published=None, version=0, published_at=None, activated_at=None)

    @bp.put('/staffing/weeks/<day>')
    @roles_required(*MANAGERS)
    def staffing_save(day):
        start, data = week(day), body()
        if start + timedelta(days=7) <= local_day():
            fail('Una semana finalizada no se modifica.', 409)
        plan = StaffingWeek.query.filter_by(week_start=start).with_for_update().first()
        if data.get('version') != (plan.version if plan else 0):
            fail('Otro supervisor modificó la semana. Actualizá antes de guardar.', 409)
        if plan and plan.activated_at:
            fail('La semana ya está activa. Usá refuerzos diarios para cambios temporales.', 409)
        assignments = data.get('assignments')
        if not isinstance(assignments, dict):
            fail('Indicá las asignaciones por operario.')
        valid = {str(u.id): u for u in User.query.filter_by(active=True).all() if u.role.name in ('operador','palletizador','controlador')}
        if set(assignments) != set(valid):
            fail('Incluí a todos los operarios activos, aunque no tengan canchas. Actualizá el equipo.', 409)
        try:
            draft = {key: validate_courts(value) for key,value in assignments.items()}
        except ValueError as error:
            fail(str(error))
        if plan is None:
            plan = StaffingWeek(week_start=start)
            db.session.add(plan)
        plan.draft = deepcopy(draft)
        # Assign a new object and explicit revision even when the draft is unchanged.
        plan.version = (plan.version or 0) + 1
        db.session.add(LogEntry(user_id=g.current_user.id, action='guardar_semana', entity='planificacion_equipo',
            details=json.dumps(dict(week=day, assignments=draft))))
        db.session.commit()
        return jsonify(payload(plan))

    @bp.post('/staffing/weeks/<day>/publish')
    @roles_required(*MANAGERS)
    def staffing_publish(day):
        start = week(day)
        plan = StaffingWeek.query.filter_by(week_start=start).with_for_update().first()
        if not plan or body().get('version') != plan.version:
            fail('Guardá el borrador y actualizá su versión antes de publicar.', 409)
        if plan.activated_at or start + timedelta(days=7) <= local_day():
            fail('No se puede reemplazar una semana activa o finalizada.', 409)
        valid = {str(u.id) for u in User.query.filter_by(active=True).all() if u.role.name in ('operador','palletizador','controlador')}
        if set(plan.draft) != valid:
            fail('El equipo cambió. Actualizá y guardá el borrador.', 409)
        plan.published = deepcopy(plan.draft)
        plan.published_by = g.current_user.id
        plan.published_at = datetime.now(timezone.utc)
        db.session.add(LogEntry(user_id=g.current_user.id, action='publicar_semana', entity='planificacion_equipo',
            details=json.dumps(dict(week=day, assignments=plan.published))))
        db.session.commit()
        return jsonify(payload(plan))
