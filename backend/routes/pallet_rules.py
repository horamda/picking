import json
import csv
from io import StringIO
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, g, jsonify, request

from auth import roles_required
from models import Article, LogEntry
from services.pallet_rules import (PalletCaliberFamily, PalletCaliberAlias, PalletStackingRule,
                                   mixer_article_eligible, source_value, validate_family)
from utils.db import db


pallet_rules_bp = Blueprint('pallet_rules', __name__)


def mixer_articles():
    return [article for article in Article.query.order_by(Article.sku).all()
            if mixer_article_eligible(article)]


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


def missing_article_data(article, configured):
    business_unit = source_value(article, 'UNIDAD DE NEGOCIO') or ''
    caliber = (article.calibre or '').strip()
    missing = []
    if not article.unidades_por_bulto or article.unidades_por_bulto <= 0: missing.append('unidades_por_bulto')
    if not article.bultos_por_pallet or article.bultos_por_pallet <= 0: missing.append('bultos_por_pallet')
    if not article.bultos_por_piso or article.bultos_por_piso <= 0: missing.append('bultos_por_piso')
    if not business_unit: missing.append('unidad_de_negocio')
    if not caliber: missing.append('calibre')
    if business_unit and caliber and (business_unit, caliber) not in configured: missing.append('regla_apilado')
    raw = article.datos_origen or {}
    factor = next((value for key, value in raw.items() if str(key).strip().lower() == 'valor unidad de medida'), None)
    unit = next((value for key, value in raw.items() if str(key).strip().lower() == 'descripcion unidad de medida'), '')
    try:
        has_hl = (article.hl_por_bulto is not None and Decimal(article.hl_por_bulto) > 0) or (str(unit).strip().upper() == 'HECTOLITROS' and Decimal(str(factor).replace(',', '.')) > 0)
    except (InvalidOperation, TypeError, ValueError):
        has_hl = False
    if not has_hl: missing.append('factor_hl')
    return business_unit, caliber, missing


@pallet_rules_bp.get('')
@roles_required('administrador')
def list_rules():
    assigned = {a.caliber: a.family_key for a in PalletCaliberAlias.query.all()}
    calibers = [value for (value,) in db.session.query(Article.calibre).distinct().order_by(Article.calibre).all() if value and value.strip()]
    stacking = PalletStackingRule.query.order_by(PalletStackingRule.business_unit, PalletStackingRule.size_rank.desc()).all()
    configured = {(r.business_unit, r.caliber) for r in stacking if r.enabled}
    active_articles = mixer_articles()
    coverage = {}
    for article in active_articles:
        key = (source_value(article, 'UNIDAD DE NEGOCIO') or 'SIN UNIDAD',
               (article.calibre or '').strip() or 'SIN CALIBRE')
        item = coverage.setdefault(key, dict(articles=0, with_floor=0))
        item['articles'] += 1
        item['with_floor'] += bool(article.bultos_por_piso)
    pending = []
    for key, counts in sorted(coverage.items()):
        lookup = ('' if key[0] == 'SIN UNIDAD' else key[0], '' if key[1] == 'SIN CALIBRE' else key[1])
        missing_rule = lookup not in configured
        missing_floor = counts['articles'] - counts['with_floor']
        if missing_rule or missing_floor:
            pending.append(dict(business_unit=key[0], caliber=key[1], **counts,
                                missing_rule=missing_rule, missing_floor=missing_floor))
    incomplete_count = sum(bool(missing_article_data(article, configured)[2]) for article in active_articles)
    return jsonify(families=[family_json(f) for f in PalletCaliberFamily.query.order_by(PalletCaliberFamily.base_priority.desc(), PalletCaliberFamily.name).all()],
        calibers=[dict(caliber=value, family_key=assigned.get(value)) for value in calibers],
        stacking_rules=[dict(business_unit=r.business_unit, caliber=r.caliber, can_be_base=r.can_be_base,
            stable=r.stable, allow_incomplete_floor=r.allow_incomplete_floor, size_rank=r.size_rank,
            enabled=r.enabled, articles=coverage.get((r.business_unit, r.caliber), {}).get('articles', 0),
            with_floor=coverage.get((r.business_unit, r.caliber), {}).get('with_floor', 0)) for r in stacking],
        pending_rules=pending, incomplete_articles=incomplete_count)


@pallet_rules_bp.get('/incomplete-articles.csv')
@roles_required('administrador')
def export_incomplete_articles():
    configured = {(r.business_unit, r.caliber) for r in PalletStackingRule.query.filter_by(enabled=True).all()}
    output = StringIO()
    writer = csv.writer(output, delimiter=';', lineterminator='\n')
    writer.writerow(['SKU', 'DESCRIPCION', 'UNIDAD_DE_NEGOCIO', 'CALIBRE', 'UNIDADES_POR_BULTO',
                     'BULTOS_POR_PALLET', 'BULTOS_POR_PISO', 'PISOS_POR_PALLET', 'HL_POR_BULTO', 'DATOS_FALTANTES'])
    for article in mixer_articles():
        business_unit, caliber, missing = missing_article_data(article, configured)
        if missing:
            writer.writerow([article.sku, article.descripcion, business_unit, caliber, article.unidades_por_bulto,
                             article.bultos_por_pallet, article.bultos_por_piso or '', article.pisos_por_pallet or '',
                             article.hl_por_bulto or '', ','.join(missing)])
    return Response('\ufeff' + output.getvalue(), mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=articulos-incompletos-mezclador.csv'})


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
