from copy import deepcopy
from uuid import uuid4
from flask import jsonify, g, request
from auth import roles_required
from models import User
from utils.db import db
from services.staffing import enabled, local_day
from services.warehouse import assigned_courts
from services.assistance import helpers, personal_check, products_for
from services.load_control import ControlTruck, ControlTimer, court_state, edit_court, selected_loads, save_state, now


def register(bp):
    from routes.load_control import (MANAGERS, fail, body, get_load, ensure_open, approved,
        task_products, release_timer, elapsed, timing)

    def require_enabled():
        if not enabled():
            fail('La planificación del equipo todavía no está habilitada.', 503)

    @bp.get('/assistance')
    @roles_required(*MANAGERS)
    def assistance_board():
        require_enabled()
        from datetime import date
        day = request.args.get('date', local_day().isoformat())
        try:
            date.fromisoformat(day)
        except ValueError:
            fail('Fecha inválida.')
        rows = []
        for truck in ControlTruck.query.filter_by(load_date=day).all():
            if truck.state.get('released_at') or not approved(truck):
                continue
            for load in selected_loads(truck):
                for court in load.content['canchas']:
                    cs = court_state(truck.state, load.id, court['numero'])
                    for stage in (0, 4):
                        check = cs['checks'].get(str(stage), {})
                        products = products_for(load, court, stage, check.get('user_id'), task_products(load, court, stage))
                        pending = [p for p in products if p['sku'] not in check.get('answers', {})]
                        team = helpers(cs, stage)
                        if pending or team:
                            rows.append(dict(load_id=load.id, court=court['numero'], stage=stage, truck=truck.truck,
                                reparto=load.reparto, version=truck.version, owner=check.get('username'),
                                running=bool(check.get('timer_started_at')), products=pending,
                                closed=bool(cs['checks'].get('1') or cs['checks'].get('2') or check.get('status') == 'done'),
                                helpers=[dict(h, elapsed_seconds=elapsed(h), timing=timing(h)) for h in team]))
        return jsonify(rows)

    @bp.post('/loads/<int:load_id>/courts/<int:number>/assistance/<int:stage>')
    @roles_required(*MANAGERS)
    def assistance_create(load_id, number, stage):
        require_enabled()
        data = body()
        if stage not in (0, 4) or type(data.get('user_id')) is not int:
            fail('Elegí el operario y el proceso de armado.')
        # User then truck: same order as product confirmations.
        user = User.query.filter_by(id=data['user_id'], active=True).with_for_update().first()
        if not user or user.role.name != ('operador' if stage == 0 else 'palletizador'):
            fail('El operario debe tener el rol correspondiente al proceso.')
        if db.session.get(ControlTimer, user.id):
            fail('El operario tiene trabajo en curso. Debe terminarlo antes de ayudar.', 409)
        for truck in ControlTruck.query.filter(ControlTruck.state['released_at'].as_string().is_(None)).all():
            for other_cs in truck.state.get('courts', {}).values():
                if any(c.get('user_id') == user.id and c.get('status') == 'active'
                       for c in list(other_cs.get('checks', {}).values()) + helpers(other_cs)):
                    fail('El operario tiene un proceso pendiente. Debe terminarlo antes de ayudar.', 409)
        load = get_load(load_id)
        ensure_open(load.truck)
        if data.get('version') != load.truck.version:
            fail('La carga cambió. Actualizá los productos pendientes.', 409)
        if not approved(load.truck) or load not in selected_loads(load.truck):
            fail('La carga debe estar seleccionada y aprobada.', 409)
        court = next((c for c in load.content['canchas'] if c['numero'] == number), None)
        if not court:
            fail('Cancha inexistente.', 404)
        state = deepcopy(load.truck.state)
        cs = edit_court(state, load_id, number)
        primary = cs['checks'].get(str(stage), {})
        if primary.get('timer_started_at'):
            fail('El titular debe pausar antes de ceder productos.', 409)
        if primary.get('status') == 'done' or cs['checks'].get('1') or cs['checks'].get('2'):
            fail('El proceso ya finalizó o está en control.', 409)
        if primary.get('user_id') == user.id:
            fail('El titular ya tiene estos productos asignados.')
        if any(h['user_id'] == user.id and h['status'] in ('active', 'done') for h in helpers(cs, stage)):
            fail('Ese operario ya tiene un refuerzo en esta cancha.', 409)
        # Finished helpers keep their exclusive SKUs; unfinished work cannot be double-assigned.
        available = products_for(load, court, stage, primary.get('user_id'), task_products(load, court, stage))
        pending = {p['sku'] for p in available if p['sku'] not in primary.get('answers', {})}
        skus = data.get('skus')
        if not isinstance(skus, list) or not skus or any(not isinstance(s, str) for s in skus) or not set(skus) <= pending:
            fail('Seleccioná productos pendientes disponibles.', 409)
        own_courts = assigned_courts(user.id)
        for other_load in selected_loads(load.truck):
            for other in other_load.content['canchas']:
                if other['numero'] not in own_courts:
                    continue
                own_cs = court_state(load.truck.state, other_load.id, other['numero'])
                if personal_check(own_cs, stage, user.id) and personal_check(own_cs, stage, user.id).get('user_id') not in (None, user.id):
                    continue
                if (personal_check(own_cs, stage, user.id) or {}).get('status') != 'done' and products_for(other_load, other, stage, user.id, task_products(other_load, other, stage)):
                    fail('El operario todavía tiene canchas pendientes en este camión.', 409)
        helper = dict(id=uuid4().hex, stage=stage, user_id=user.id, username=user.username,
            status='active', started_at=None, timer_started_at=None, active_seconds=0, answers={},
            day=local_day().isoformat(), skus=sorted(set(skus)), assigned_at=now(), assigned_by=g.current_user.id)
        cs.setdefault('helpers', []).append(helper)
        if not primary:
            primary = dict(id=uuid4().hex, stage=stage, user_id=None, username='Sin asignar', status='active',
                started_at=None, timer_started_at=None, active_seconds=0, answers={})
            cs['checks'][str(stage)] = primary
        if set(skus) == pending:
            release_timer(primary)
            primary.update(status='done', finished_at=now(), delegated_remaining=True)
        save_state(load.truck, state, g.current_user, 'asignar_refuerzo', dict(load_id=load_id, court=number, **helper))
        return jsonify(helper), 201

    @bp.post('/loads/<int:load_id>/courts/<int:number>/assistance/<helper_id>/return')
    @roles_required(*MANAGERS)
    def assistance_return(load_id, number, helper_id):
        require_enabled()
        load = get_load(load_id)
        ensure_open(load.truck)
        state = deepcopy(load.truck.state)
        cs = edit_court(state, load_id, number)
        helper = next((h for h in helpers(cs) if h['id'] == helper_id), None)
        if not helper or helper['status'] != 'active':
            fail('Refuerzo no disponible.', 409)
        if helper.get('timer_started_at'):
            fail('El ayudante debe pausar antes de devolver los pendientes.', 409)
        if body().get('physical_review') is not True:
            fail('Revisá físicamente lo preparado sin confirmar antes de devolver los pendientes.')
        if not helper.get('answers'):
            helper['status'] = 'returned'
        else:
            helper['skus'] = list(helper['answers'])
            helper['status'] = 'done'
        release_timer(helper)
        helper['finished_at'] = now()
        helper['returned_by'] = g.current_user.id
        # If the original owner finished their share, reopen only the returned pending products.
        primary = cs['checks'].get(str(helper['stage']))
        if primary and primary['status'] == 'done':
            state.setdefault('archived_checks', []).append(dict(primary, load_id=load.id, court=number))
            cs['checks'][str(helper['stage'])] = dict(id=uuid4().hex, stage=helper['stage'], user_id=None,
                username='Sin asignar', status='active', started_at=None, timer_started_at=None,
                active_seconds=0, answers=deepcopy(primary['answers']))
        save_state(load.truck, state, g.current_user, 'devolver_refuerzo', dict(load_id=load_id, court=number, helper_id=helper_id))
        return jsonify(ok=True)
