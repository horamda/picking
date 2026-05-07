import csv
import io
import unicodedata

import sqlalchemy as sa

from models import Article
from utils.db import db


TRUE_VALUES = {'1', 'true', 'si', 'sí', 'yes', 'y', 'activo'}
FALSE_VALUES = {'0', 'false', 'no', 'n', 'inactivo'}


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
        parsed = int(float(str(value).replace(',', '.')))
    except (TypeError, ValueError):
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
                'activo': parse_bool(get_value(row, 'activo', 'estado'), True),
            }
            articles.append(payload)
        except Exception as exc:
            errors.append({'row': index, 'sku': sku, 'error': str(exc)})

    return {'articles': articles, 'duplicates': duplicates, 'errors': errors}


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


def replace_articles(articles: list[dict], duplicates: list[dict], errors: list[dict]) -> dict:
    if duplicates or errors:
        return result_payload('replace', False, duplicates=duplicates, errors=errors)

    deleted = Article.query.count()
    try:
        Article.query.delete(synchronize_session=False)
        db.session.execute(sa.insert(Article), articles)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return result_payload('replace', False, duplicates=duplicates, errors=[{'row': None, 'error': str(exc)}])

    inactive = sum(1 for article in articles if not article['activo'])
    return result_payload('replace', True, deleted=deleted, created=len(articles), inactive=inactive)


def merge_articles(articles: list[dict], duplicates: list[dict], errors: list[dict]) -> dict:
    created = 0
    updated = 0
    unchanged = 0
    inactive = 0

    try:
        for payload in articles:
            sku = payload['sku']
            values = {key: value for key, value in payload.items() if key != 'sku'}
            article = Article.query.filter_by(sku=sku).first()
            if article:
                changed = any(getattr(article, key) != value for key, value in values.items())
                for key, value in values.items():
                    setattr(article, key, value)
                updated += 1 if changed else 0
                unchanged += 0 if changed else 1
            else:
                db.session.add(Article(**payload))
                created += 1

            if not values['activo']:
                inactive += 1

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return result_payload('merge', False, duplicates=duplicates, errors=errors + [{'row': None, 'error': str(exc)}])

    return result_payload('merge', True, created=created, updated=updated, unchanged=unchanged, inactive=inactive, duplicates=duplicates, errors=errors)


def import_articles_from_csv(file_bytes: bytes, mode: str = 'merge') -> dict:
    parsed = parse_article_csv(file_bytes)
    articles = parsed['articles']
    duplicates = parsed['duplicates']
    errors = parsed['errors']

    if mode == 'replace':
        return replace_articles(articles, duplicates, errors)
    return merge_articles(articles, duplicates, errors)
