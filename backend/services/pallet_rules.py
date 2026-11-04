"""Administrative stacking families and aliases for safe cross-court pallet mixing."""
from datetime import datetime

from utils.db import db


class PalletCaliberFamily(db.Model):
    __tablename__ = 'pallet_caliber_families'
    key = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    must_be_bottom = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    base_priority = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    allowed_above = db.Column(db.JSON, nullable=False, default=list)
    cases_per_layer = db.Column(db.Integer, nullable=True)
    max_layers = db.Column(db.Integer, nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PalletCaliberAlias(db.Model):
    __tablename__ = 'pallet_caliber_aliases'
    caliber = db.Column(db.String(120), primary_key=True)
    family_key = db.Column(db.String(80), db.ForeignKey('pallet_caliber_families.key'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PalletStackingRule(db.Model):
    __tablename__ = 'pallet_stacking_rules'
    business_unit = db.Column(db.String(120), primary_key=True)
    caliber = db.Column(db.String(120), primary_key=True)
    can_be_base = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    stable = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    allow_incomplete_floor = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    size_rank = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


def source_value(article, name):
    wanted = name.casefold()
    for key, value in (article.datos_origen or {}).items() if article else []:
        if str(key).strip().casefold() == wanted:
            return str(value or '').strip()
    return ''


def normalize_key(value):
    import re
    key = re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')
    if not key or len(key) > 80:
        raise ValueError('Ingresá un código de familia válido de hasta 80 caracteres.')
    return key


def validate_family(data, current_key=None):
    key = normalize_key(data.get('key') or current_key)
    name = str(data.get('name') or '').strip()
    if not name or len(name) > 120:
        raise ValueError('Ingresá un nombre de hasta 120 caracteres.')
    if type(data.get('must_be_bottom')) is not bool or type(data.get('enabled')) is not bool:
        raise ValueError('Indicá las opciones de base y estado.')
    priority = data.get('base_priority')
    if type(priority) is not int or priority < 0 or priority > 1000:
        raise ValueError('La prioridad de base debe ser un entero entre 0 y 1000.')
    allowed = data.get('allowed_above')
    if not isinstance(allowed, list) or any(not isinstance(v, str) or (v != '*' and not v.strip()) for v in allowed):
        raise ValueError('Las compatibilidades deben ser una lista de familias o *.')
    allowed = sorted(set('*' if v == '*' else normalize_key(v) for v in allowed))
    for field in ('cases_per_layer', 'max_layers'):
        value = data.get(field)
        if value is not None and (type(value) is not int or value <= 0):
            raise ValueError('Bultos por capa y capas máximas deben ser enteros positivos o quedar vacíos.')
    return dict(key=key, name=name, must_be_bottom=data['must_be_bottom'], base_priority=priority,
        allowed_above=allowed, cases_per_layer=data.get('cases_per_layer'), max_layers=data.get('max_layers'), enabled=data['enabled'])


def rule_catalog():
    stacking = {(r.business_unit, r.caliber): r for r in PalletStackingRule.query.filter_by(enabled=True).all()}
    families = {f.key: f for f in PalletCaliberFamily.query.all()}
    result = {}
    for alias in PalletCaliberAlias.query.all():
        family = families.get(alias.family_key)
        if family and family.enabled:
            result[alias.caliber] = dict(family=family.key, family_name=family.name,
                must_be_bottom=family.must_be_bottom, base_priority=family.base_priority,
                allowed_above=list(family.allowed_above or []), cases_per_layer=family.cases_per_layer,
                max_layers=family.max_layers)
    return result, stacking


def stacking_values(article, rules):
    legacy, stacking = rules if isinstance(rules, tuple) else (rules, {})
    legacy_mode = not stacking
    caliber = (article.calibre or '').strip() if article else ''
    business_unit = source_value(article, 'UNIDAD DE NEGOCIO')
    stack_rule = stacking.get((business_unit, caliber))
    rule = legacy.get(caliber)
    return dict(calibre=caliber or None, stack_family=rule['family'] if rule else None,
        stack_family_name=rule['family_name'] if rule else None,
        must_be_bottom=rule['must_be_bottom'] if rule else False,
        base_priority=rule['base_priority'] if rule else 0,
        allowed_above=rule['allowed_above'] if rule else [],
        cases_per_layer=rule['cases_per_layer'] if rule else None,
        max_layers=rule['max_layers'] if rule else None,
        business_unit=business_unit or None,
        can_be_base=stack_rule.can_be_base if stack_rule else bool(rule) and legacy_mode,
        stable=stack_rule.stable if stack_rule else bool(rule) and legacy_mode,
        allow_incomplete_floor=stack_rule.allow_incomplete_floor if stack_rule else False,
        size_rank=stack_rule.size_rank if stack_rule else (rule['base_priority'] if rule and legacy_mode else 0),
        bultos_por_piso=(article.bultos_por_piso if article else None) or (1 if legacy_mode and rule else None),
        stacking_rule_pending=not legacy_mode and (stack_rule is None or article is None or not article.bultos_por_piso))
