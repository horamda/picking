"""CSV editing with signed original values to detect concurrent changes."""
import csv
import io

from flask import current_app
from itsdangerous import URLSafeSerializer, BadSignature

HEADERS = ['Codigo', 'Descripcion original', 'Descripcion para voz', 'Borrar voz', 'Control (no editar)']


def signer():
    return URLSafeSerializer(current_app.config['JWT_SECRET'], salt='voice-csv-v1')


def safe_cell(value):
    value = value or ''
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n', "'")) else value


def export_voice_csv(articles):
    output = io.StringIO(newline='')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(HEADERS)
    for a in articles:
        writer.writerow([safe_cell(a.sku), safe_cell(a.descripcion), safe_cell(a.descripcion_voz), '',
                         signer().dumps([a.sku, a.descripcion_voz or ''])])
    return output.getvalue().encode('utf-8-sig')


def parse_voice_csv(raw):
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('Guardá el archivo como CSV UTF-8.')
    delimiter = ';' if ';' in text.partition('\n')[0] else ','
    reader = csv.DictReader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True)
    if reader.fieldnames != HEADERS:
        raise ValueError('Usá la plantilla exportada y conservá sus cinco encabezados y su orden.')
    items, seen = [], set()
    for row in reader:
        line = reader.line_num
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f'Fila {line}: cantidad de columnas incorrecta.')
        try:
            sku, previous = signer().loads(row[HEADERS[4]])
        except (BadSignature, ValueError, TypeError):
            raise ValueError(f'Fila {line}: control inválido. Volvé a exportar.')
        if row[HEADERS[0]] != safe_cell(sku):
            raise ValueError(f'Fila {line}: el código fue modificado. Conservá los ceros iniciales como texto.')
        if sku in seen:
            raise ValueError(f'Fila {line}: código duplicado {sku}.')
        seen.add(sku)
        value = row[HEADERS[2]].strip()
        if value == safe_cell(previous):
            value = previous
        delete = row[HEADERS[3]].strip().upper()
        if delete not in ('', 'NO', 'SI', 'SÍ'):
            raise ValueError(f'Fila {line}: Borrar voz admite SI, NO o vacío.')
        if delete in ('SI', 'SÍ'):
            value = ''
        elif not value:
            value = previous
        if len(value) > 255 or '\x00' in value:
            raise ValueError(f'Fila {line}: descripción inválida; máximo 255 caracteres.')
        items.append(dict(sku=sku, previous=previous, value=value, row=line))
        if len(items) > 20000:
            raise ValueError('El archivo supera las 20.000 filas.')
    if not items:
        raise ValueError('El archivo no contiene artículos.')
    return items
