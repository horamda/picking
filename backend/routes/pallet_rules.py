import json
import csv
from io import BytesIO, StringIO
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, g, jsonify, request
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from auth import roles_required
from models import Article, LogEntry
from services.pallet_rules import (PalletCaliberFamily, PalletCaliberAlias, PalletStackingRule,
                                   mixer_article_eligible, source_value, validate_family)
from utils.db import db


pallet_rules_bp = Blueprint('pallet_rules', __name__)

STACKING_FIELDS = ('can_be_base', 'stable', 'allow_incomplete_floor', 'size_rank', 'enabled',
                   'units_per_case', 'length_cm', 'width_cm', 'height_cm')
PHYSICAL_FIELDS = ('units_per_case', 'length_cm', 'width_cm', 'height_cm')
XLSX_COLUMNS = (
    ('UNIDAD_DE_NEGOCIO', 'business_unit'), ('CALIBRE', 'caliber'),
    ('UNIDADES_POR_BULTO', 'units_per_case'), ('LARGO_CM', 'length_cm'),
    ('ANCHO_CM', 'width_cm'), ('ALTO_CM_OPCIONAL', 'height_cm'),
    ('PUEDE_SER_BASE', 'can_be_base'), ('ESTABLE', 'stable'),
    ('PERMITE_PISO_INCOMPLETO', 'allow_incomplete_floor'), ('ORDEN', 'size_rank'),
    ('ACTIVA', 'enabled'), ('ARTICULOS', 'articles'), ('DATOS_FALTANTES', 'missing_data'))


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


def decimal_json(value):
    return float(value) if value is not None else None


def rule_json(row, coverage=None):
    counts = (coverage or {}).get((row.business_unit, row.caliber), {})
    return dict(business_unit=row.business_unit, caliber=row.caliber, can_be_base=row.can_be_base,
        stable=row.stable, allow_incomplete_floor=row.allow_incomplete_floor, size_rank=row.size_rank,
        enabled=row.enabled, units_per_case=row.units_per_case, length_cm=decimal_json(row.length_cm),
        width_cm=decimal_json(row.width_cm), height_cm=decimal_json(row.height_cm),
        articles=counts.get('articles', 0), with_floor=counts.get('with_floor', 0))


def physical_missing(row):
    return [field for field in ('units_per_case', 'length_cm', 'width_cm') if not getattr(row, field, None)]


def optional_positive(value, label, integer=False):
    if value in (None, ''):
        return None
    try:
        number = Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{label} debe ser un número positivo.')
    if not number.is_finite() or number <= 0 or (integer and number != number.to_integral_value()):
        raise ValueError(f'{label} debe ser un {"entero " if integer else ""}positivo.')
    return int(number) if integer else number


def boolean_value(value, label):
    if type(value) is bool:
        return value
    normalized = str(value or '').strip().casefold()
    if normalized in {'si', 'sí', 'true', '1'}:
        return True
    if normalized in {'no', 'false', '0'}:
        return False
    raise ValueError(f'{label} debe indicar SI o NO.')


def xlsx_rows(raw):
    try:
        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = [str(value or '').strip().upper() for value in next(rows)]
    except Exception as exc:
        raise ValueError('El archivo no es un Excel válido.') from exc
    required = [name for name, _ in XLSX_COLUMNS[:11]]
    missing = [name for name in required if name not in headers]
    if missing:
        raise ValueError('Faltan columnas requeridas: ' + ', '.join(missing) + '.')
    indexes = {name: headers.index(name) for name in required}
    result, seen = [], set()
    for number, values in enumerate(rows, 2):
        business_unit = str(values[indexes['UNIDAD_DE_NEGOCIO']] or '').strip()
        caliber = str(values[indexes['CALIBRE']] or '').strip()
        if not business_unit and not caliber:
            continue
        if not business_unit or not caliber:
            raise ValueError(f'Fila {number}: completá unidad de negocio y calibre.')
        key = (business_unit, caliber)
        if key in seen:
            raise ValueError(f'Fila {number}: la combinación está duplicada.')
        seen.add(key)
        current = db.session.get(PalletStackingRule, key)
        values_by_name = {field: values[indexes[name]] for name, field in XLSX_COLUMNS[:11]}
        parsed = dict(business_unit=business_unit, caliber=caliber)
        for field, label, integer in (
                ('units_per_case', 'Unidades por bulto', True), ('length_cm', 'Largo', False),
                ('width_cm', 'Ancho', False), ('height_cm', 'Alto', True)):
            raw_value = values_by_name[field]
            parsed[field] = getattr(current, field) if raw_value in (None, '') and current else optional_positive(raw_value, label, integer)
        for field, label in (('can_be_base', 'Puede ser base'), ('stable', 'Estable'),
                             ('allow_incomplete_floor', 'Permite piso incompleto'), ('enabled', 'Activa')):
            raw_value = values_by_name[field]
            parsed[field] = getattr(current, field) if raw_value in (None, '') and current else boolean_value(raw_value, label)
        raw_rank = values_by_name['size_rank']
        if raw_rank in (None, ''):
            parsed['size_rank'] = current.size_rank if current else 0
        else:
            try:
                rank = Decimal(str(raw_rank).replace(',', '.'))
            except (InvalidOperation, ValueError):
                raise ValueError(f'Fila {number}: Orden debe ser un entero positivo o cero.')
            if not rank.is_finite() or rank < 0 or rank != rank.to_integral_value():
                raise ValueError(f'Fila {number}: Orden debe ser un entero positivo o cero.')
            parsed['size_rank'] = int(rank)
        result.append((number, current, parsed))
    if not result:
        raise ValueError('El Excel no contiene reglas para importar.')
    return result


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
    rules_by_key = {(r.business_unit, r.caliber): r for r in stacking}
    for item in pending:
        row = rules_by_key.get((item['business_unit'], item['caliber']))
        item['missing_physical'] = physical_missing(row) if row else list(PHYSICAL_FIELDS[:3])
    return jsonify(families=[family_json(f) for f in PalletCaliberFamily.query.order_by(PalletCaliberFamily.base_priority.desc(), PalletCaliberFamily.name).all()],
        calibers=[dict(caliber=value, family_key=assigned.get(value)) for value in calibers],
        stacking_rules=[dict(**rule_json(r, coverage), missing_physical=physical_missing(r)) for r in stacking],
        pending_rules=pending, incomplete_articles=incomplete_count)


@pallet_rules_bp.get('/stacking.xlsx')
@roles_required('administrador')
def export_stacking_rules():
    coverage = {}
    for article in mixer_articles():
        key = (source_value(article, 'UNIDAD DE NEGOCIO'), (article.calibre or '').strip())
        if all(key):
            item = coverage.setdefault(key, {'articles': 0, 'units': set()})
            item['articles'] += 1
            if article.unidades_por_bulto:
                item['units'].add(article.unidades_por_bulto)
    existing = {(r.business_unit, r.caliber): r for r in PalletStackingRule.query.all()}
    keys = set(existing) | set(coverage)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Reglas mezclador'
    sheet.append([name for name, _ in XLSX_COLUMNS])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='0B3D91')
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for key in sorted(keys):
        row = existing.get(key)
        source = coverage.get(key, {'articles': 0, 'units': set()})
        inferred_units = next(iter(source['units'])) if len(source['units']) == 1 else None
        values = dict(business_unit=key[0], caliber=key[1], units_per_case=getattr(row, 'units_per_case', None) or inferred_units,
            length_cm=decimal_json(getattr(row, 'length_cm', None)), width_cm=decimal_json(getattr(row, 'width_cm', None)),
            height_cm=decimal_json(getattr(row, 'height_cm', None)), can_be_base=getattr(row, 'can_be_base', False),
            stable=getattr(row, 'stable', False), allow_incomplete_floor=getattr(row, 'allow_incomplete_floor', False),
            size_rank=getattr(row, 'size_rank', 0), enabled=getattr(row, 'enabled', True), articles=source['articles'])
        missing = [label for field, label in (('units_per_case', 'UNIDADES_POR_BULTO'), ('length_cm', 'LARGO_CM'),
                   ('width_cm', 'ANCHO_CM')) if not values[field]]
        values['missing_data'] = ', '.join(missing)
        sheet.append([('SI' if values[field] else 'NO') if field in ('can_be_base', 'stable', 'allow_incomplete_floor', 'enabled')
                      else values.get(field) for _, field in XLSX_COLUMNS])
    widths = {'A': 24, 'B': 24, 'C': 20, 'D': 14, 'E': 14, 'F': 20, 'G': 18, 'H': 12,
              'I': 25, 'J': 12, 'K': 12, 'L': 12, 'M': 42}
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    for row in sheet.iter_rows(min_row=2, min_col=3, max_col=6):
        for cell in row:
            cell.number_format = '0.00' if cell.column > 3 else '0'
    output = BytesIO()
    workbook.save(output)
    return Response(output.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': 'attachment; filename=reglas-mezclador.xlsx'})


@pallet_rules_bp.post('/stacking.xlsx')
@roles_required('administrador')
def import_stacking_rules():
    uploaded = request.files.get('file')
    apply = str(request.form.get('apply', '')).lower() == 'true'
    if not uploaded or not uploaded.filename.lower().endswith('.xlsx'):
        return jsonify(error='Seleccioná el Excel de reglas del mezclador.'), 400
    try:
        parsed = xlsx_rows(uploaded.read())
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    changes = []
    for number, current, values in parsed:
        before = None if not current else {field: decimal_json(getattr(current, field)) if field in PHYSICAL_FIELDS[1:]
                                            else getattr(current, field) for field in STACKING_FIELDS}
        after = {field: decimal_json(values[field]) if field in PHYSICAL_FIELDS[1:] else values[field]
                 for field in STACKING_FIELDS}
        if before != after:
            changes.append(dict(row=number, business_unit=values['business_unit'], caliber=values['caliber'],
                                before=before, after=after))
        if apply and before != after:
            row = current or PalletStackingRule(business_unit=values['business_unit'], caliber=values['caliber'])
            for field in STACKING_FIELDS:
                setattr(row, field, values[field])
            row.updated_by = g.current_user.id
            db.session.add(row)
    if apply and changes:
        db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_stacking_rule',
            action='importar_reglas_mezclador_excel', details=json.dumps(dict(filename=uploaded.filename, changes=changes))))
        db.session.commit()
    return jsonify(applied=apply, total=len(parsed), updated=len(changes), unchanged=len(parsed) - len(changes),
                   changes=changes[:50])


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
    try:
        physical = {
            'units_per_case': getattr(row, 'units_per_case', None) if 'units_per_case' not in data else optional_positive(data.get('units_per_case'), 'Unidades por bulto', True),
            'length_cm': getattr(row, 'length_cm', None) if 'length_cm' not in data else optional_positive(data.get('length_cm'), 'Largo'),
            'width_cm': getattr(row, 'width_cm', None) if 'width_cm' not in data else optional_positive(data.get('width_cm'), 'Ancho'),
            'height_cm': getattr(row, 'height_cm', None) if 'height_cm' not in data else optional_positive(data.get('height_cm'), 'Alto', True),
        }
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    before = None if not row else {k: decimal_json(getattr(row, k)) if k in PHYSICAL_FIELDS[1:] else getattr(row, k)
                                   for k in STACKING_FIELDS}
    if not row:
        row = PalletStackingRule(business_unit=business_unit, caliber=caliber)
        db.session.add(row)
    for key in flags + ('size_rank',):
        setattr(row, key, data[key])
    for key, value in physical.items():
        setattr(row, key, value)
    row.updated_by = g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='pallet_stacking_rule',
        action='editar_regla_apilado', details=json.dumps(dict(business_unit=business_unit,
        caliber=caliber, before=before, after={**{k: data[k] for k in flags + ('size_rank',)},
                                               **{k: decimal_json(v) if k != 'units_per_case' else v for k, v in physical.items()}}))))
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
