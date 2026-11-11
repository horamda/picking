"""Warehouse configuration mapped to the explicitly deployed migrations."""
from utils.db import db


class UserCourt(db.Model):
    __tablename__ = 'user_court_assignments'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    court_number = db.Column(db.Integer, primary_key=True)


class DepotSettings(db.Model):
    __tablename__ = 'depot_planning_settings'
    branch = db.Column(db.String(255), primary_key=True)
    mix_courts_default = db.Column(db.Boolean, nullable=False, default=False)
    pallet_base_height_cm = db.Column(db.Numeric(10, 2), nullable=True)
    reference_pallet_height_cm = db.Column(db.Numeric(10, 2), nullable=True)
    max_pallet_height_cm = db.Column(db.Numeric(10, 2), nullable=True)
    empty_pallet_weight_kg = db.Column(db.Numeric(12, 3), nullable=True)
    max_pallet_weight_kg = db.Column(db.Numeric(12, 3), nullable=True)
    safety_margin_pct = db.Column(db.Numeric(5, 2), nullable=True)
    height_excess_mode = db.Column(db.String(20), nullable=False, default='inform', server_default='inform')
    pallet_weight_excess_mode = db.Column(db.String(20), nullable=False, default='inform', server_default='inform')
    truck_weight_excess_mode = db.Column(db.String(20), nullable=False, default='inform', server_default='inform')
    share_floor_remainders = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    weight_tiebreaker = db.Column(db.Boolean, nullable=False, default=False, server_default='false')


class TruckCapacity(db.Model):
    __tablename__ = 'truck_pallet_capacities'
    branch = db.Column(db.String(255), db.ForeignKey('depot_planning_settings.branch'), primary_key=True)
    truck = db.Column(db.String(255), primary_key=True)
    pallet_capacity = db.Column(db.Integer, nullable=False)
    max_payload_kg = db.Column(db.Numeric(12, 3), nullable=True)
    max_height_cm = db.Column(db.Numeric(10, 2), nullable=True)
    depot = db.relationship('DepotSettings', lazy='joined')


def assigned_courts(user_id):
    return sorted(r.court_number for r in UserCourt.query.filter_by(user_id=user_id).all())


def validate_courts(value):
    if not isinstance(value, list) or len(value) > 100 or any(type(n) is not int or n <= 0 for n in value):
        raise ValueError('Indicá una lista de canchas con números enteros positivos (máximo 100).')
    return sorted(set(value))


def depot_key(value):
    """PDF depot codes may arrive as 1, 001 or 001 - CASA CENTRAL."""
    import re
    value = str(value or '').strip()
    match = re.fullmatch(r'(\d+)(?:\s*-\s*.+)?', value)
    return ('code', int(match.group(1))) if match else ('name', value.casefold())


def truck_capacity(branch, truck):
    exact = db.session.get(TruckCapacity, (branch, truck))
    if exact:
        return exact
    candidates = [row for row in TruckCapacity.query.filter_by(truck=truck).all()
                  if depot_key(row.branch) == depot_key(branch)]
    # Ambiguous aliases require explicit correction; never guess a capacity.
    return candidates[0] if len(candidates) == 1 else None


def planning_configuration(branch, truck):
    """Return plain values suitable for deterministic planning and fingerprints."""
    capacity = truck_capacity(branch, truck)
    depot = capacity.depot if capacity else db.session.get(DepotSettings, branch)
    if not depot and not capacity:
        aliases = [row for row in DepotSettings.query.all() if depot_key(row.branch) == depot_key(branch)]
        depot = aliases[0] if len(aliases) == 1 else None
    def value(source, name):
        raw = getattr(source, name, None) if source else None
        return str(raw) if raw is not None else None
    return dict(
        pallet_base_height_cm=value(depot, 'pallet_base_height_cm'),
        reference_pallet_height_cm=value(depot, 'reference_pallet_height_cm'),
        max_pallet_height_cm=value(capacity, 'max_height_cm') or value(depot, 'max_pallet_height_cm'),
        empty_pallet_weight_kg=value(depot, 'empty_pallet_weight_kg'),
        max_pallet_weight_kg=value(depot, 'max_pallet_weight_kg'),
        safety_margin_pct=value(depot, 'safety_margin_pct'),
        height_excess_mode=getattr(depot, 'height_excess_mode', 'inform') if depot else 'inform',
        pallet_weight_excess_mode=getattr(depot, 'pallet_weight_excess_mode', 'inform') if depot else 'inform',
        truck_weight_excess_mode=getattr(depot, 'truck_weight_excess_mode', 'inform') if depot else 'inform',
        share_floor_remainders=bool(getattr(depot, 'share_floor_remainders', False)),
        weight_tiebreaker=bool(getattr(depot, 'weight_tiebreaker', False)),
        max_payload_kg=value(capacity, 'max_payload_kg'),
        truck_height_override=bool(capacity and capacity.max_height_cm is not None),
    )
