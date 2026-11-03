import json

from flask import Blueprint, g, jsonify, request

from auth import roles_required
from models import Article, LogEntry
from services.pallet_rules import PalletCaliberFamily, PalletCaliberAlias, validate_family
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
    return jsonify(families=[family_json(f) for f in PalletCaliberFamily.query.order_by(PalletCaliberFamily.base_priority.desc(), PalletCaliberFamily.name).all()],
        calibers=[dict(caliber=value, family_key=assigned.get(value)) for value in calibers])


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
