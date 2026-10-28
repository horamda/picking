import csv
import io
import unicodedata
from decimal import Decimal, InvalidOperation

import sqlalchemy as sa

from models import Article
from utils.db import db


TRUE_VALUES = {'1', 'true', 'si', 'sí', 'yes', 'y', 'activo'}
FALSE_VALUES = {'0', 'false', 'no', 'n', 'inactivo'}

# Manual voice descriptions belong to the operator-facing catalog, never to an
# imported source. Keep this allowlist explicit even if the parser gains fields.
CSV_MANAGED_FIELDS = frozenset({
    'sku', 'descripcion', 'division', 'calibre', 'unidades_por_bulto',
    'bultos_por_pallet', 'activo', 'datos_origen',
})


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value)
    return ''.join(char for char in normalized if not unicodedata.combining(char))


def normalize_key(value: str) -> str:
    return strip_accents(str(value).strip().lower())


def normalize_row(row: dict) -> dict:
    return {normalize_key(key): (value.strip() if isinstance(value, str) else value) for key, value in row.items()}


def get_value(row: dict, *names, default=None):
    for name in names:
        value = row.get(name.lower())
        if value not in [None, '']:
            return value
    return default


def parse_int_field(value, field_name: str, min_value: int = 1) -> int:
    try:
        number = Decimal(str(value).replace(',', '.'))
        if not number.is_finite() or number != number.to_integral_value():
            raise ValueError()
        parsed = int(number)
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError(f'{field_name} invalido')
    if parsed < min_value:
        raise ValueError(f'{field_name} debe ser mayor o igual a {min_value}')
    return parsed


def parse_bool(value, default=True) -> bool:
    if value in [None, '']:
        return default
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def decode_csv_bytes(raw: bytes) -> str:
    for encoding in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass
    return raw.decode('latin-1', errors='replace')


def detect_delimiter(text: str) -> str:
    sample = text[:4096]
    return ';' if sample.count(';') >= sample.count(',') else ','


def parse_article_csv(file_bytes: bytes) -> dict:
    articles = []
    excluded = []
    duplicates = []
    errors = []
    seen = set()

    text = decode_csv_bytes(file_bytes)
    delimiter = detect_delimiter(text)
    csvfile = io.StringIO(text)
    reader = csv.DictReader(csvfile, delimiter=delimiter)

    if not reader.fieldnames:
        return {'articles': [], 'duplicates': [], 'errors': [{'row': 1, 'error': 'CSV sin encabezados'}]}

    normalized_headers = [normalize_key(h) for h in reader.fieldnames]

    sku_cols = {'sku', 'codigo', 'codigo_articulo', 'articulo'}
    upb_cols = {'unidades_por_bulto', 'unidades por bulto', 'uxb', 'unidades'}
    bpp_cols = {'bultos_por_pallet', 'bultos por pallet', 'bxp', 'pallet'}

    missing = []
    for field in ('tipo de producto', 'activo', 'usado en dispositivo movil', 'anulado'):
        if field not in normalized_headers:
            missing.append(field)
    if len(normalized_headers) != len(set(normalized_headers)):
        missing.append('encabezados únicos (hay columnas duplicadas)')
    if not any(c in normalized_headers for c in sku_cols):
        missing.append(f'SKU (ej: sku, codigo)')
    if not any(c in normalized_headers for c in upb_cols):
        missing.append(f'unidades/bulto (ej: unidades_por_bulto, uxb)')
    if not any(c in normalized_headers for c in bpp_cols):
        missing.append(f'bultos/pallet (ej: bultos_por_pallet, bxp)')

    if missing:
        encabezados = ', '.join(normalized_headers)
        return {
            'articles': [],
            'duplicates': [],
            'errors': [{'row': 1, 'error': f'Columnas faltantes: {"; ".join(missing)}. Encabezados detectados: {encabezados}'}],
        }

    for index, raw_row in enumerate(reader, start=2):
        if None in raw_row or any(value is None for value in raw_row.values()):
            errors.append({'row': index, 'error': 'Cantidad de campos distinta al encabezado'})
            continue
        row = normalize_row(raw_row)
        sku = get_value(row, 'sku', 'codigo', 'codigo_articulo', 'articulo')

        if not sku:
            errors.append({'row': index, 'error': 'SKU faltante'})
            continue

        sku = str(sku).strip()
        if sku in seen:
            duplicates.append({'row': index, 'sku': sku})
            continue
        seen.add(sku)

        eligible = (normalize_key(row['tipo de producto']) == 'mercaderia'
                    and normalize_key(row['activo']) == 'si'
                    and normalize_key(row['usado en dispositivo movil']) == 'si'
                    and normalize_key(row['anulado']) == 'no')
        if not eligible:
            excluded.append({'sku': sku, 'datos_origen': dict(raw_row)})
            continue

        try:
            payload = {
                'sku': sku,
                'descripcion': get_value(row, 'descripcion', 'descripcion articulo', 'detalle', 'nombre', default=''),
                'division': get_value(row, 'division', default=''),
                'calibre': get_value(row, 'calibre', default=''),
                'unidades_por_bulto': parse_int_field(
                    get_value(row, 'unidades_por_bulto', 'unidades por bulto', 'uxb', 'unidades'),
                    'unidades_por_bulto',
                    min_value=1,
                ),
                'bultos_por_pallet': parse_int_field(
                    get_value(row, 'bultos_por_pallet', 'bultos por pallet', 'bxp', 'pallet'),
                    'bultos_por_pallet',
                    min_value=0,
                ),
                'activo': True,
                'datos_origen': dict(raw_row),
            }
            articles.append(payload)
        except Exception as exc:
            errors.append({'row': index, 'sku': sku, 'error': str(exc)})

    return {'articles': articles, 'excluded': excluded, 'duplicates': duplicates, 'errors': errors}


def result_payload(mode: str, applied: bool, deleted=0, created=0, updated=0, unchanged=0, inactive=0, duplicates=None, errors=None):
    return {
        'mode': mode,
        'applied': applied,
        'deleted': deleted,
        'created': created,
        'updated': updated,
        'unchanged': unchanged,
        'inactive': inactive,
        'duplicates': duplicates or [],
        'errors': errors or [],
    }


def import_articles_from_csv(file_bytes: bytes, mode: str = 'merge') -> dict:
    parsed = parse_article_csv(file_bytes)
    articles, excluded = parsed['articles'], parsed.get('excluded', [])
    duplicates, errors = parsed['duplicates'], parsed['errors']
    if mode not in ('merge', 'replace'):
        errors.append({'row': 1, 'error': 'Modo invalido'})
    if not articles and not excluded and not errors:
        errors.append({'row': 1, 'error': 'CSV sin articulos'})
    result = result_payload(mode, False, duplicates=duplicates, errors=errors)
    result.update(eligible=len(articles), excluded=len(excluded))
    if errors or duplicates:
        return result
    try:
        # Serializes imports on PostgreSQL without adding a table or doing startup DDL.
        if db.engine.dialect.name == 'postgresql':
            db.session.execute(sa.text('SELECT pg_advisory_xact_lock(2710202602)'))
        existing = {a.sku: a for a in Article.query.order_by(Article.sku).with_for_update().all()}
        eligible_skus = {p['sku'] for p in articles}
        for payload in articles:
            payload = {key: value for key, value in payload.items() if key in CSV_MANAGED_FIELDS}
            article = existing.get(payload['sku'])
            if article is None:
                db.session.add(Article(**payload))
                result['created'] += 1
            else:
                changed = any(getattr(article, key) != value for key, value in payload.items())
                for key, value in payload.items():
                    setattr(article, key, value)
                result['updated' if changed else 'unchanged'] += 1
        excluded_by_sku = {p['sku']: p for p in excluded}
        for sku, article in existing.items():
            if sku in excluded_by_sku:
                article.datos_origen = excluded_by_sku[sku]['datos_origen']
            if sku in excluded_by_sku or (mode == 'replace' and sku not in eligible_skus):
                if article.activo:
                    result['inactive'] += 1
                article.activo = False
        db.session.commit()
        result['applied'] = True
    except Exception:
        db.session.rollback()
        result = result_payload(mode, False, errors=[{'row': None, 'error': 'No se pudo guardar el maestro. No se aplicaron cambios.'}])
    return result
