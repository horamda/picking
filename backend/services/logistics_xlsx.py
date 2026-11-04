"""Preview/apply the auxiliary logistics workbook without changing catalog eligibility."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
import unicodedata

from openpyxl import load_workbook
import sqlalchemy as sa

from models import Article, LogEntry
from utils.db import db


POSITIONS = dict(sku=0, description=1, units_per_case=2, voided=5, mobile=6,
                 barcode_case=14, barcode_unit=15, voice=19, hl=22,
                 cases_per_pallet=46, floors=47, stackability=48, merchandise_type=62)


def clean(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def normalized(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(c for c in text if not unicodedata.combining(c) and c.isalnum()).lower()


def positive_int(value, label, row):
    try:
        number = Decimal(str(value))
        if number != number.to_integral_value() or number <= 0:
            raise ValueError()
        return int(number)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f'Fila {row}: {label} debe ser un entero positivo.')


def optional_decimal(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def parse_logistics_xlsx(raw):
    try:
        workbook = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError('El archivo no es una plantilla Excel válida.') from exc
    if not workbook.worksheets:
        raise ValueError('El Excel no contiene hojas.')
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    try:
        next(rows); headers = list(next(rows)); next(rows)
    except StopIteration as exc:
        raise ValueError('La plantilla no contiene encabezados y datos.') from exc
    expected = {0: ('codigo', 'cdigo'), 2: ('unidadxbulto',), 46: ('bultosxpallet',), 47: ('pisos',)}
    for index, tokens in expected.items():
        if index >= len(headers) or not any(token in normalized(headers[index]) for token in tokens):
            raise ValueError('La estructura no coincide con la plantilla de artículos esperada.')
    parsed, duplicates, seen = [], [], set()
    for number, values in enumerate(rows, 4):
        values = list(values)
        if not values or values[0] in (None, ''):
            continue
        if (str(values[POSITIONS['voided']] or '').strip().upper() != 'NO'
                or str(values[POSITIONS['mobile']] or '').strip().upper() != 'SI'):
            continue
        sku = str(values[0]).strip()
        if sku in seen:
            duplicates.append(dict(row=number, sku=sku, error='Código duplicado.'))
            continue
        seen.add(sku)
        try:
            upb = positive_int(values[POSITIONS['units_per_case']], 'Unidad x Bulto', number)
            bpp = positive_int(values[POSITIONS['cases_per_pallet']], 'Bultos x Pallet', number)
        except ValueError as exc:
            parsed.append(dict(row=number, sku=sku, fatal=str(exc)))
            continue
        floors_value = values[POSITIONS['floors']]
        floors = int(floors_value) if isinstance(floors_value, (int, float)) and floors_value > 0 and float(floors_value).is_integer() else None
        warning, cases_floor = None, None
        if not floors:
            warning = 'Pisos faltante o cero; bultos por piso queda pendiente.'
        elif bpp % floors:
            warning = f'{bpp} bultos no son divisibles por {floors} pisos.'
        else:
            cases_floor = bpp // floors
        raw_data = {str(headers[i] or f'Columna {i+1}'): clean(values[i] if i < len(values) else None)
                    for i in range(min(len(headers), len(values))) if headers[i] is not None}
        parsed.append(dict(row=number, sku=sku, unidades_por_bulto=upb, bultos_por_pallet=bpp,
            pisos_por_pallet=floors, bultos_por_piso=cases_floor,
            apilabilidad=optional_decimal(values[POSITIONS['stackability']]),
            hl_por_bulto=optional_decimal(values[POSITIONS['hl']]),
            codigo_barras_bulto=str(values[POSITIONS['barcode_case']] or '').strip() or None,
            codigo_barras_unidad=str(values[POSITIONS['barcode_unit']] or '').strip() or None,
            datos_logisticos=raw_data, warning=warning))
    if duplicates:
        raise ValueError(f'El archivo contiene {len(duplicates)} códigos duplicados; no se aplicaron cambios.')
    return parsed


def import_logistics_xlsx(raw, apply=False, user_id=None):
    rows = parse_logistics_xlsx(raw)
    skus = [r['sku'] for r in rows if not r.get('fatal')]
    query = Article.query.filter(Article.sku.in_(skus)).order_by(Article.sku)
    if apply:
        if db.engine.dialect.name == 'postgresql':
            db.session.execute(sa.text('SELECT pg_advisory_xact_lock(411202601)'))
        query = query.with_for_update().populate_existing()
    existing = {a.sku: a for a in query.all()}
    fields = ('unidades_por_bulto', 'bultos_por_pallet', 'pisos_por_pallet', 'bultos_por_piso',
              'apilabilidad', 'hl_por_bulto', 'codigo_barras_bulto', 'codigo_barras_unidad', 'datos_logisticos')
    changes, unknown, warnings, errors = [], [], [], []
    for item in rows:
        if item.get('fatal'):
            errors.append(dict(row=item['row'], sku=item['sku'], error=item['fatal']))
            continue
        article = existing.get(item['sku'])
        if not article:
            unknown.append(dict(row=item['row'], sku=item['sku']))
            continue
        if item.get('warning'):
            warnings.append(dict(row=item['row'], sku=item['sku'], warning=item['warning']))
        after = {field: item[field] for field in fields}
        before = {field: getattr(article, field) for field in fields}
        if any(before[field] != after[field] for field in fields):
            changes.append(dict(article=article, row=item['row'], sku=item['sku'], before=before, after=after))
    if apply and errors:
        db.session.rollback()
        return dict(applied=False, errors=errors, warnings=warnings, unknown=unknown,
                    matched=len(existing), updated=0, unchanged=len(existing))
    if apply:
        for change in changes:
            for field, value in change['after'].items():
                setattr(change['article'], field, value)
        db.session.add(LogEntry(user_id=user_id, entity='articulos', action='importar_datos_logisticos',
            details=f'actualizados={len(changes)}, desconocidos={len(unknown)}, advertencias={len(warnings)}'))
        db.session.flush()
    return dict(applied=apply, total=len(rows), matched=len(existing), updated=len(changes),
                unchanged=len(existing)-len(changes), unknown=unknown, warnings=warnings, errors=errors)
