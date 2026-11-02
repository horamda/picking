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


class TruckCapacity(db.Model):
    __tablename__ = 'truck_pallet_capacities'
    branch = db.Column(db.String(255), db.ForeignKey('depot_planning_settings.branch'), primary_key=True)
    truck = db.Column(db.String(255), primary_key=True)
    pallet_capacity = db.Column(db.Integer, nullable=False)


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
