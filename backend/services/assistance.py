"""Exclusive whole-product delegations stored with the locked truck document."""
from services.load_control import court_state, selected_loads
from services.staffing import local_day


def helpers(cs, stage=None):
    return [h for h in cs.get('helpers', []) if stage is None or h['stage'] == stage]


def usable(h):
    return h['status'] == 'done' or (h['status'] == 'active' and h['day'] == local_day().isoformat())


def personal_check(cs, stage, user_id, check_id=None):
    candidates = helpers(cs, stage) + [cs.get('checks', {}).get(str(stage), {})]
    if check_id:
        return next((c for c in candidates if c.get('id') == check_id), None)
    helper = next((h for h in helpers(cs, stage) if h['user_id'] == user_id and h['day'] == local_day().isoformat() and h['status'] in ('active', 'done')), None)
    return helper or cs.get('checks', {}).get(str(stage))


def can_access(load, number, user_id, stage):
    cs = court_state(load.truck.state, load.id, number)
    return any(h['user_id'] == user_id and h['day'] == local_day().isoformat() and h['status'] in ('active', 'done') for h in helpers(cs, stage))


def products_for(load, court, stage, user_id, products):
    cs = court_state(load.truck.state, load.id, court['numero'])
    own = next((h for h in helpers(cs, stage) if h['user_id'] == user_id and h['day'] == local_day().isoformat() and h['status'] in ('active', 'done')), None)
    # Expired work stays reserved until explicit reconciliation; never silently duplicate it.
    delegated = {sku for h in helpers(cs, stage) if h['status'] in ('active', 'done') for sku in h['skus']}
    return [p for p in products if p['sku'] in own['skus']] if own else [p for p in products if p['sku'] not in delegated]


def queue_for(trucks, courts, stage, user_id, products):
    def pending(t):
        for load in selected_loads(t):
            for court in load.content['canchas']:
                number = court['numero']
                if number not in courts and not can_access(load, number, user_id, stage):
                    continue
                cs = court_state(t.state, load.id, number)
                check = personal_check(cs, stage, user_id) or {}
                raw = products(load, court, stage) if t.state.get('planning') else court['productos']
                if check.get('status') != 'done' and products_for(load, court, stage, user_id, raw):
                    return True
        return False
    ordered = sorted((t for t in trucks if not t.state.get('released_at')),
        key=lambda t: (t.load_date, t.state.get('dispatch', {}).get('position', 0), t.branch, t.id))
    owned = [t for t in ordered if any(c.get('stage') == stage and c.get('status') == 'active'
        and c.get('user_id') == user_id and (not c.get('day') or usable(c))
        for cs in t.state.get('courts', {}).values() for c in list(cs.get('checks', {}).values()) + helpers(cs))]
    assisted = [t for t in ordered if any(h['user_id'] == user_id and h['stage'] == stage and h['status'] == 'active' and usable(h)
        for cs in t.state.get('courts', {}).values() for h in helpers(cs))]
    return owned or assisted or [t for t in ordered if t.state.get('dispatch', {}).get('load_ids') and pending(t)]


def pause_expired():
    from copy import deepcopy
    from services.staffing import enabled
    from services.load_control import ControlTruck, audit
    from models import User
    from routes.load_control import release_timer
    from utils.db import db
    if not enabled():
        return
    candidates = [t.id for t in ControlTruck.query.filter(ControlTruck.state['released_at'].as_string().is_(None)).all()
        if any(h['status'] == 'active' and not usable(h) and h.get('timer_started_at')
               for cs in t.state.get('courts', {}).values() for h in helpers(cs))]
    db.session.rollback()
    for truck in ControlTruck.query.filter(ControlTruck.id.in_(candidates)).order_by(ControlTruck.id).with_for_update().populate_existing().all():
        state, changed = deepcopy(truck.state), False
        for cs in state.get('courts', {}).values():
            for h in helpers(cs):
                if h['status'] == 'active' and not usable(h) and h.get('timer_started_at'):
                    release_timer(h)
                    h['expired_review_required'] = True
                    audit(db.session.get(User, h['assigned_by']), 'vencer_refuerzo', truck, dict(helper_id=h['id'], user_id=h['user_id']))
                    changed = True
        if changed:
            truck.state = state
    db.session.commit()
