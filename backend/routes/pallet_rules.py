import json

from flask import Blueprint, g, jsonify, request

from auth import roles_required
from models import Article, LogEntry
from services.pallet_rules import (PalletCaliberFamily, PalletCaliberAlias, PalletStackingRule,
                                   source_value, validate_family)
from utils.db import db


pallet_rules_bp = Blueprint('pallet_rules', __name__)


def family_json(row):
    return dict(key=row.key, name=row.name, must_be_bottom=row.must_be_bottom,
        base_priority=row.base_priority, allowed_above=row.allowed_above or [],
        cases_per_layer=row.cases_per_layer, max_layers=row.max_layers, enabled=row.enabled,
        aliases=sorted(a.caliber for a in PalletCaliberAlias.query.filter_by(family_key=row.key).all()))


def validate_references(values):
    known = {key for (key,) in db.session.query(PalletCaliberFamily.key).all()} | {values['key'], '*'}
    unknown = set(values['allowed_above']) - known
    if unknown:
        raise ValueError('Familias permitidas inexistentes: ' + ', '.join(sorted(unknown)) + '.')


@pallet_rules_bp.get('')
@roles_required('administrador')
def list_rules():
    assigned = {a.caliber: a.family_key for a in PalletCaliberAlias.query.all()}
    calibers = [value for (value,) in db.session.query(Article.calibre).distinct().order_by(Article.calibre).all() if value and value.strip()]
    stacking = PalletStackingRule.query.order_by(PalletStackingRule.business_unit, PalletStackingRule.size_rank.desc()).all()
    configured = {(r.business_unit, r.caliber) for r in stacking}
    active_articles = Article.query.filter_by(activo=True).all()
    pending = sorted({(source_value(a, 'UNIDAD DE NEGOCIO') or 'SIN UNIDAD', (a.calibre or '').strip() or 'SIN CALIBRE')
                      for a in active_articles
                      if (source_value(a, 'UNIDAD DE NEGOCIO'), (a.calibre or '').strip()) not in configured
                      or not a.bultos_por_piso})
    return jsonify(families=[family_json(f) for f in PalletCaliberFamily.query.order_by(PalletCaliberFamily.base_priority.desc(), PalletCaliberFamily.name).all()],
        calibers=[dict(caliber=value, family_key=assigned.get(value)) for value in calibers],
        stacking_rules=[dict(business_unit=r.business_unit, caliber=r.caliber, can_be_base=r.can_be_base,
            stable=r.stable, allow_incomplete_floor=r.allow_incomplete_floor, size_rank=r.size_rank,
            enabled=r.enabled) for r in stacking],
        pending_rules=[dict(business_unit=u, caliber=c) for u, c in pending])


@pallet_rules_bp.put('/stacking')
@roles_required('administrador')
def update_stacking_rule():
    data = request.get_json(silent=True) or {}
    business_unit = str(data.get('business_unit') or '').strip()
    caliber = str(data.get('caliber') or '').strip()
    flags = ('can_be_base', 'stable', 'allow_incomplete_floor', 'enabled')
    if not business_unit or not caliber or any(type(data.get(k)) is not bool for k in flags):
        return jsonify(error='Completá unidad de negocio, calibre y todas las opciones.'), 400
    if type(data.get('size_rank')) is not int or data['size_rank'] < 0:
        return jsonify(error='El orden de calibre debe ser un entero positivo o cero.'), 400
    row = db.session.get(PalletStackingRule, (business_unit, caliber))
    before = None if not row else {k: getattr(row, k) for k in flags + ('size_rank',)}
    if not row:
        row = PalletStackingRule(business_unit=business_unit, caliber=caliber)
        db.session.add(row)
    for key in flags + ('size_rank',):
        setattr(row, key, data[key])
    row.updated_by = g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_stacking_rule',
        action='editar_regla_apilado', details=json.dumps(dict(business_unit=business_unit,
        caliber=caliber, before=before, after={k: data[k] for k in flags + ('size_rank',)}))))
    db.session.commit()
    return jsonify(ok=True)


@pallet_rules_bp.post('/families')
@roles_required('administrador')
def create_family():
    try:
        values = validate_family(request.get_json(silent=True) or {})
        validate_references(values)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    if db.session.get(PalletCaliberFamily, values['key']):
        return jsonify(error='Ya existe una familia con ese código.'), 409
    row = PalletCaliberFamily(**values, updated_by=g.current_user.id)
    db.session.add(row)
    db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_caliber_family', action='crear_regla_pallet', details=json.dumps(values)))
    db.session.commit()
    return jsonify(family_json(row)), 201


@pallet_rules_bp.put('/families/<key>')
@roles_required('administrador')
def update_family(key):
    row = db.session.get(PalletCaliberFamily, key)
    if not row:
        return jsonify(error='Familia inexistente.'), 404
    try:
        values = validate_family(request.get_json(silent=True) or {}, key)
        validate_references(values)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    if values['key'] != key:
        return jsonify(error='El código de una familia existente no puede cambiarse.'), 400
    before = family_json(row)
    for field, value in values.items():
        if field != 'key': setattr(row, field, value)
    row.updated_by = g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_caliber_family', action='editar_regla_pallet', details=json.dumps(dict(key=key, before=before, after=values))))
    db.session.commit()
    return jsonify(family_json(row))


@pallet_rules_bp.delete('/families/<key>')
@roles_required('administrador')
def delete_family(key):
    row = db.session.get(PalletCaliberFamily, key)
    if not row:
        return jsonify(error='Familia inexistente.'), 404
    if PalletCaliberAlias.query.filter_by(family_key=key).first():
        return jsonify(error='Desasigná sus calibres antes de eliminar la familia.'), 409
    if any(key in (family.allowed_above or []) for family in PalletCaliberFamily.query.filter(PalletCaliberFamily.key != key).all()):
        return jsonify(error='Otra familia todavía permite este calibre arriba. Editá esa compatibilidad antes de eliminar.'), 409
    db.session.delete(row)
    db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_caliber_family', action='eliminar_regla_pallet', details=json.dumps(dict(key=key))))
    db.session.commit()
    return jsonify(ok=True)


@pallet_rules_bp.put('/aliases')
@roles_required('administrador')
def assign_alias():
    data = request.get_json(silent=True) or {}
    caliber, family_key = str(data.get('caliber') or '').strip(), data.get('family_key')
    known = db.session.query(Article.id).filter(Article.calibre == caliber).first()
    if not caliber or len(caliber) > 120 or not known:
        return jsonify(error='El calibre no existe en el catálogo.'), 400
    if family_key is not None and not db.session.get(PalletCaliberFamily, family_key):
        return jsonify(error='La familia seleccionada no existe.'), 400
    row = db.session.get(PalletCaliberAlias, caliber)
    before = row.family_key if row else None
    if family_key is None:
        if row: db.session.delete(row)
    else:
        if not row:
            row = PalletCaliberAlias(caliber=caliber)
            db.session.add(row)
        row.family_key, row.updated_by = family_key, g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_caliber_alias', action='asignar_calibre_pallet', details=json.dumps(dict(caliber=caliber, before=before, after=family_key))))
    db.session.commit()
    return jsonify(caliber=caliber, family_key=family_key)
