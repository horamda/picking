import re
import unicodedata
from collections import Counter
from datetime import datetime

import pdfplumber


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value)
    return ''.join(char for char in normalized if not unicodedata.combining(char))


def compact_line(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def parse_int(value) -> int:
    if not value:
        return 0
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return 0


def parse_pdf_date(value: str):
    value = compact_line(value)
    for fmt in ('%d/%m/%y', '%d/%m/%Y'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def most_common_date(items: list[dict]):
    dates = [item.get('fecha_reparto') for item in items if item.get('fecha_reparto')]
    if not dates:
        return None
    return Counter(dates).most_common(1)[0][0]


def get_or_create_consolidado(consolidados: dict, metadata: dict) -> dict:
    reparto = metadata.get('reparto') or 'sin_reparto'
    if reparto not in consolidados:
        consolidados[reparto] = {
            'reparto': metadata.get('reparto'),
            'camion': metadata.get('camion'),
            'chofer': metadata.get('chofer'),
            'deposito': metadata.get('deposito'),
            'fecha_reparto': metadata.get('fecha_reparto'),
            'cancha': None,
            'almacen': None,
            'items': [],
        }
    else:
        consolidados[reparto].update({k: v for k, v in metadata.items() if v})
    return consolidados[reparto]


def parse_metadata(lines: list[str]) -> dict:
    metadata = {}
    for line in lines:
        line = compact_line(line)
        plain = strip_accents(line)

        reparto_match = re.search(r'Reparto\s*(?:\(\s*)?Nro\.?\s*:\s*([^\)|\s]+)', plain, re.IGNORECASE)
        if reparto_match:
            metadata['reparto'] = reparto_match.group(1)

        # "Reparto Nro: 00066447 | Fecha: 11/05/2026" — pipe may or may not be extracted
        if not metadata.get('fecha_reparto'):
            fecha_match = re.search(r'\bFecha:\s*(\d{2}/\d{2}/\d{2,4})\b', plain, re.IGNORECASE)
            if fecha_match:
                parsed = parse_pdf_date(fecha_match.group(1))
                if parsed:
                    metadata['fecha_reparto'] = parsed

        transport_match = re.search(
            r'Transporte:\s*(.*?)\s*\|\s*Chofer:\s*(.*?)\s*\|\s*Deposito:\s*(.*)',
            plain,
            re.IGNORECASE,
        )
        if transport_match:
            metadata['camion'] = transport_match.group(1).strip()
            metadata['chofer'] = transport_match.group(2).strip()
            metadata['deposito'] = transport_match.group(3).strip()
    return metadata


def aggregate_items(items: list[dict]) -> list[dict]:
    grouped = {}
    for item in items:
        key = (item['sku'], item.get('cancha') or '', item.get('almacen') or '')
        if key not in grouped:
            grouped[key] = {
                'sku': item['sku'],
                'descripcion': item.get('descripcion'),
                'bultos': 0,
                'unidades': 0,
                'cancha': item.get('cancha'),
                'almacen': item.get('almacen'),
                'lineas': 0,
            }
        grouped[key]['bultos'] += item.get('bultos', 0)
        grouped[key]['unidades'] += item.get('unidades', 0)
        grouped[key]['lineas'] += 1
    return list(grouped.values())


def rows_from_words(words: list[dict], y_tol: int = 4) -> list[list[dict]]:
    """Group page words into horizontal rows sorted left to right."""
    buckets: dict[int, list[dict]] = {}
    for w in words:
        key = round(w['top'] / y_tol) * y_tol
        buckets.setdefault(key, []).append(w)
    return [
        sorted(row, key=lambda w: w['x0'])
        for row in sorted(buckets.values(), key=lambda r: r[0]['top'])
    ]


def find_column_positions(all_rows: list[list[dict]]):
    """
    Locate the header row containing 'Bultos' and 'Unids' and return
    the x-center of the FIRST Bultos column and FIRST Unids column.
    """
    for row in all_rows:
        texts = [strip_accents(w['text']).upper() for w in row]
        if 'BULTOS' not in texts:
            continue
        if 'UNIDS' not in texts and 'UNIDADES' not in texts:
            continue
        bultos_x = None
        unids_x = None
        for w in row:
            t = strip_accents(w['text']).upper()
            if t == 'BULTOS' and bultos_x is None:
                bultos_x = (w['x0'] + w['x1']) / 2
            elif t in ('UNIDS', 'UNIDADES') and unids_x is None:
                unids_x = (w['x0'] + w['x1']) / 2
            if bultos_x is not None and unids_x is not None:
                return bultos_x, unids_x
    return None, None


def parse_item_row(row: list[dict], bultos_x, unids_x):
    """
    Parse one item row using word x-positions to assign numbers to the
    correct Bultos / Unids column. Falls back to positional order when
    column headers were not found.
    """
    if not row or not re.match(r'^\d{3,}$', row[0]['text']):
        return None

    # Find the date word
    date_idx = None
    for i, w in enumerate(row):
        if re.match(r'^\d{2}/\d{2}/\d{2,4}$', w['text']):
            date_idx = i
            break
    if date_idx is None and (bultos_x is None or unids_x is None):
        return None

    sku = row[0]['text']
    fecha_reparto = parse_pdf_date(row[date_idx]['text']) if date_idx is not None else None
    if bultos_x is not None and unids_x is not None:
        # Restrict to A CARGAR: DESCARGA columns must never count as picking.
        width = unids_x - bultos_x
        start, end = bultos_x - width / 2, unids_x + width / 2
        num_words = [w for w in row[1:] if start <= (w['x0'] + w['x1']) / 2 < end
                     and re.match(r'^\d+$', w['text'])]
        description_words = row[1:date_idx] if date_idx is not None else [w for w in row[1:] if w['x1'] < start]
    else:
        num_words = [w for w in row[date_idx + 1:] if re.match(r'^\d+$', w['text'])]
        description_words = row[1:date_idx]
    if not num_words:
        return None
    descripcion = ' '.join(w['text'] for w in description_words)

    bultos = 0
    unidades = 0

    if bultos_x is not None and unids_x is not None:
        for w in num_words:
            wx = (w['x0'] + w['x1']) / 2
            if abs(wx - bultos_x) <= abs(wx - unids_x):
                bultos += int(w['text'])
            else:
                unidades += int(w['text'])
    else:
        # Fallback: first number = bultos, second = unidades
        if len(num_words) >= 1:
            bultos = int(num_words[0]['text'])
        if len(num_words) >= 2:
            unidades = int(num_words[1]['text'])

    return {
        'sku': sku,
        'descripcion': descripcion,
        'fecha_reparto': fecha_reparto,
        'bultos': bultos,
        'unidades': unidades,
    }


def parse_pdf_file(path: str) -> dict:
    consolidados = {}

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            plain_page = strip_accents(text).upper()

            if 'PLANILLA DE CARGA' not in plain_page:
                continue

            # Metadata still parsed from plain text lines
            lines = [compact_line(line) for line in text.splitlines() if compact_line(line)]
            metadata = parse_metadata(lines)
            consolidado = get_or_create_consolidado(consolidados, metadata)
            current_cancha = consolidado.get('cancha')
            current_almacen = consolidado.get('almacen')

            # Items parsed from word-level extraction for correct column assignment
            words = page.extract_words()
            all_rows = rows_from_words(words)
            bultos_x, unids_x = find_column_positions(all_rows)
            product_table = False

            for row in all_rows:
                row_text = compact_line(' '.join(w['text'] for w in row))
                plain = strip_accents(row_text)
                header = [strip_accents(w['text']).upper() for w in row]
                if 'BULTOS' in header and ('UNIDS' in header or 'UNIDADES' in header):
                    # Empty-container and division totals are separate tables, not products.
                    product_table = any(t.startswith('VENC') for t in header) or header[0] == 'BULTOS'
                    continue

                cancha_match = re.match(r'^(\d+)\s*-\s*(CANCHA\s+.+)$', plain, re.IGNORECASE)
                if cancha_match:
                    current_cancha = cancha_match.group(0).strip()
                    consolidado['cancha'] = consolidado['cancha'] or current_cancha
                    continue

                almacen_match = re.match(r'^Almacen:\s*(.*?)(?:\s+A\s+CARGAR\b.*)?$', plain, re.IGNORECASE)
                if almacen_match:
                    current_almacen = almacen_match.group(1).strip()
                    consolidado['almacen'] = consolidado['almacen'] or current_almacen
                    continue

                if plain.upper().startswith('T O T A L') or plain.upper().startswith('TOTAL '):
                    continue

                if not current_almacen or not product_table:
                    continue

                item = parse_item_row(row, bultos_x, unids_x)
                if item is None:
                    continue

                consolidado['items'].append({
                    **item,
                    'cancha': current_cancha,
                    'almacen': current_almacen,
                })

    parsed_consolidados = []
    for consolidado in consolidados.values():
        if not consolidado.get('items'):
            continue
        consolidado['fecha_reparto'] = consolidado.get('fecha_reparto') or most_common_date(consolidado['items'])
        consolidado['raw_items_count'] = len(consolidado['items'])
        consolidado['items'] = aggregate_items(consolidado['items'])
        parsed_consolidados.append(consolidado)

    first = parsed_consolidados[0] if parsed_consolidados else {'items': []}
    return {
        **first,
        'items': first.get('items', []),
        'consolidados': parsed_consolidados,
    }
