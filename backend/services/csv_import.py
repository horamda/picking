import csv
import unicodedata

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


def open_csv(file_path: str):
    for encoding in ['utf-8-sig', 'cp1252', 'latin-1']:
        try:
            csvfile = open(file_path, newline='', encoding=encoding)
            csvfile.read()
            csvfile.seek(0)
            return csvfile
        except UnicodeDecodeError:
            csvfile.close()
    return open(file_path, newline='', encoding='latin-1', errors='replace')


def detect_delimiter(csvfile) -> str:
    sample = csvfile.read(4096)
    csvfile.seek(0)
    if sample.count(';') >= sample.count(','):
        return ';'
    return ','


def parse_article_csv(file_path: str) -> dict:
    articles = []
    duplicates = []
    errors = []
    seen = set()

    with open_csv(file_path) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=detect_delimiter(csvfile))
        if not reader.fieldnames:
            return {'articles': [], 'duplicates': [], 'errors': [{'row': 1, 'error': 'CSV sin encabezados'}]}

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
        db.session.bulk_insert_mappings(Article, articles)
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


def import_articles_from_csv(file_path: str, mode: str = 'merge') -> dict:
    parsed = parse_article_csv(file_path)
    articles = parsed['articles']
    duplicates = parsed['duplicates']
    errors = parsed['errors']

    if mode == 'replace':
        return replace_articles(articles, duplicates, errors)
    return merge_articles(articles, duplicates, errors)
