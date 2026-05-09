from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from auth import auth_required
from models import Article, ConsolidadoDetalle, Consolidado, ProcessingBatch
from sqlalchemy import distinct, func
from utils.db import db

dashboard_bp = Blueprint('dashboard', __name__)

def to_float(value):
    return float(value or 0)

def round_metric(value, digits=2):
    return round(to_float(value), digits)

def pct(part, total):
    total = to_float(total)
    if total <= 0:
        return 0
    return round((to_float(part) / total) * 100, 1)

def classify_division(division, descripcion):
    text = f'{division or ""} {descripcion or ""}'.upper()
    if any(token in text for token in ['RETORN', 'RETORNABLE']):
        return 'Retornables'
    if any(token in text for token in ['ENVASE', 'ENV ', 'ENV.']):
        return 'Envases'
    if any(token in text for token in ['CERVEZA', 'CERVEZAS', ' CERV ']):
        return 'Cervezas'
    if any(token in text for token in ['GASEOSA', 'GASEOSAS']):
        return 'Gaseosas'
    if any(token in text for token in ['AGUA', 'AGUAS']):
        return 'Aguas'
    return division or 'Otros'

def classify_temporada(processed_at):
    if not processed_at:
        return 'Sin fecha'
    month = processed_at.month
    if month in [11, 12]:
        return 'Alta demanda'
    if month in [1, 2, 3]:
        return 'Verano'
    if month in [6, 7, 8]:
        return 'Invierno'
    return 'Media temporada'

def reparto_date_expr():
    return func.coalesce(Consolidado.fecha_reparto, Consolidado.processed_at)

def reparto_datetime(consolidado):
    return consolidado.fecha_reparto or consolidado.processed_at

def serialize_bar_rows(rows, label_key='label', value_key='bultos_pick'):
    total = sum(to_float(row[value_key]) for row in rows)
    return [
        {
            **row,
            value_key: round_metric(row[value_key]),
            'porcentaje': pct(row[value_key], total),
        }
        for row in rows
    ]

def get_filtered_consolidado_ids():
    base = db.session.query(Consolidado).join(ConsolidadoDetalle)
    base = apply_dashboard_filters(base)
    return [row.id for row in base.with_entities(Consolidado.id).distinct().all()]

def detail_scope(consolidado_ids):
    query = db.session.query(ConsolidadoDetalle)
    if consolidado_ids:
        return query.filter(ConsolidadoDetalle.consolidado_id.in_(consolidado_ids))
    return query.filter(False)

def operational_rows(consolidado_ids):
    query = (
        db.session.query(ConsolidadoDetalle, Consolidado, Article)
        .join(Consolidado, Consolidado.id == ConsolidadoDetalle.consolidado_id)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
    )
    if consolidado_ids:
        query = query.filter(Consolidado.id.in_(consolidado_ids))
    else:
        query = query.filter(False)
    return query.all()

def row_operational_metrics(detalle, article):
    bultos_equivalentes = to_float(detalle.bultos_equivalentes)
    pallet_capacity = (article.bultos_por_pallet if article else 0) or 0
    bultos_palletizados = to_float(detalle.pallets_completos) * pallet_capacity
    bultos_manuales = max(bultos_equivalentes - bultos_palletizados, 0)
    return bultos_palletizados, bultos_manuales

@dashboard_bp.route('/summary', methods=['GET'])
@auth_required
def summary():
    consolidado_ids = get_filtered_consolidado_ids()
    detail_query = detail_scope(consolidado_ids)

    total_pdfs = db.session.query(func.count(distinct(Consolidado.filename))).filter(Consolidado.id.in_(consolidado_ids)).scalar() if consolidado_ids else 0
    total_batches = db.session.query(func.count(distinct(Consolidado.batch_id))).filter(Consolidado.id.in_(consolidado_ids)).scalar() if consolidado_ids else 0
    total_repartos = len(consolidado_ids)
    total_camiones = db.session.query(func.count(distinct(Consolidado.camion))).filter(Consolidado.id.in_(consolidado_ids)).scalar() if consolidado_ids else 0
    total_pallets = detail_query.with_entities(func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0)).scalar()
    total_unidades_sueltas = detail_query.with_entities(func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0)).scalar()
    skus_no_encontrados = detail_query.filter_by(sku_estado='no encontrado').count()

    rows = operational_rows(consolidado_ids)
    bultos_palletizados = 0
    bultos_manuales = 0
    division_totals = defaultdict(float)
    for detalle, _, article in rows:
        row_palletizados, row_manuales = row_operational_metrics(detalle, article)
        bultos_palletizados += row_palletizados
        bultos_manuales += row_manuales
        division_totals[classify_division(article.division if article else None, detalle.descripcion)] += row_manuales
    total_operativo = bultos_palletizados + bultos_manuales

    top_division = max(division_totals.items(), key=lambda item: item[1])[0] if division_totals else 'Sin maestro'
    return jsonify({
        'pdfs_procesados': total_pdfs,
        'lotes_procesados': total_batches,
        'repartos_procesados': total_repartos,
        'camiones_procesados': total_camiones,
        'pallets_completos': total_pallets,
        'bultos_pick': round_metric(bultos_manuales),
        'unidades_sueltas': total_unidades_sueltas,
        'bultos_palletizados': round_metric(bultos_palletizados),
        'bultos_manuales': round_metric(bultos_manuales),
        'total_bultos': round_metric(total_operativo),
        'pct_pallets_completos': pct(bultos_palletizados, total_operativo),
        'pct_pickeo_manual': pct(bultos_manuales, total_operativo),
        'skus_no_encontrados': skus_no_encontrados,
        'total_articulos': Article.query.count(),
        'division_mayor_picking': top_division,
        'tiempo_promedio': 0,
        'operacion_ratio': {
            'bultos_palletizados': round_metric(bultos_palletizados),
            'bultos_manuales': round_metric(bultos_manuales),
            'total_bultos': round_metric(total_operativo),
            'pct_pallets': pct(bultos_palletizados, total_operativo),
            'pct_picking': pct(bultos_manuales, total_operativo),
        },
    })

def apply_dashboard_filters(query):
    args = request.args
    fecha = reparto_date_expr()
    if args.get('desde'):
        query = query.filter(fecha >= datetime.fromisoformat(args.get('desde')))
    if args.get('hasta'):
        query = query.filter(fecha < datetime.fromisoformat(args.get('hasta')) + timedelta(days=1))
    if args.get('camion'):
        query = query.filter(Consolidado.camion == args.get('camion'))
    if args.get('reparto'):
        query = query.filter(Consolidado.reparto == args.get('reparto'))
    if args.get('cancha'):
        query = query.filter(ConsolidadoDetalle.cancha == args.get('cancha'))
    return query

@dashboard_bp.route('/charts', methods=['GET'])
@auth_required
def charts():
    consolidado_ids = get_filtered_consolidado_ids()

    day_totals = defaultdict(lambda: {'picking': 0, 'pallets': 0, 'total_bultos': 0})
    division_totals = defaultdict(float)
    division_chart_totals = defaultdict(float)
    sucursal_totals = defaultdict(float)
    sku_totals = defaultdict(lambda: {'descripcion': '', 'picking': 0})
    temporada_totals = defaultdict(lambda: {
        'palletizados': 0,
        'manuales': 0,
        'pallets_completos': 0,
        'repartos': set(),
    })
    total_bultos_palletizados = 0
    total_bultos_manuales = 0

    for detalle, consolidado, article in operational_rows(consolidado_ids):
        bultos_palletizados, bultos_manuales = row_operational_metrics(detalle, article)
        total_bultos_palletizados += bultos_palletizados
        total_bultos_manuales += bultos_manuales

        division = classify_division(article.division if article else None, detalle.descripcion)
        total_detalle = bultos_palletizados + bultos_manuales
        fecha_operativa = reparto_datetime(consolidado)
        fecha = fecha_operativa.date().isoformat() if fecha_operativa else 'Sin fecha'

        day_totals[fecha]['picking'] += bultos_manuales
        day_totals[fecha]['pallets'] += bultos_palletizados
        day_totals[fecha]['total_bultos'] += total_detalle
        division_totals[division] += bultos_manuales
        division_chart_totals[division] += bultos_manuales
        sucursal_totals[consolidado.deposito or 'Sin sucursal'] += bultos_manuales
        sku_totals[detalle.sku]['descripcion'] = detalle.descripcion
        sku_totals[detalle.sku]['picking'] += bultos_manuales

        temporada = classify_temporada(fecha_operativa)
        temporada_totals[temporada]['palletizados'] += bultos_palletizados
        temporada_totals[temporada]['manuales'] += bultos_manuales
        temporada_totals[temporada]['pallets_completos'] += detalle.pallets_completos
        temporada_totals[temporada]['repartos'].add(consolidado.id)

    for category in ['Cervezas', 'Gaseosas', 'Aguas', 'Retornables', 'Envases']:
        division_totals.setdefault(category, 0)
    for temporada in ['Alta demanda', 'Verano', 'Invierno']:
        temporada_totals[temporada]

    total_operativo = total_bultos_palletizados + total_bultos_manuales
    picking_por_division = serialize_bar_rows([
        {'division': key, 'bultos_pick': value}
        for key, value in sorted(division_totals.items(), key=lambda item: item[1], reverse=True)
    ], value_key='bultos_pick')
    picking_por_sucursal = serialize_bar_rows([
        {'sucursal': key, 'bultos_pick': value}
        for key, value in sorted(sucursal_totals.items(), key=lambda item: item[1], reverse=True)
    ], value_key='bultos_pick')
    productividad_por_temporada = []
    for temporada, values in temporada_totals.items():
        total_temporada = values['palletizados'] + values['manuales']
        productividad_por_temporada.append({
            'temporada': temporada,
            'bultos_palletizados': round_metric(values['palletizados']),
            'bultos_manuales': round_metric(values['manuales']),
            'total_bultos': round_metric(total_temporada),
            'pct_pallets': pct(values['palletizados'], total_temporada),
            'pct_picking': pct(values['manuales'], total_temporada),
            'pallets_completos': int(values['pallets_completos']),
            'repartos': len(values['repartos']),
        })
    productividad_por_temporada.sort(key=lambda item: ['Alta demanda', 'Verano', 'Invierno', 'Media temporada', 'Sin fecha'].index(item['temporada']) if item['temporada'] in ['Alta demanda', 'Verano', 'Invierno', 'Media temporada', 'Sin fecha'] else 99)

    return jsonify({
        'por_dia': [
            {
                'fecha': fecha,
                'picking': round_metric(values['picking']),
                'pallets': round_metric(values['pallets']),
                'total_bultos': round_metric(values['total_bultos']),
            }
            for fecha, values in sorted(day_totals.items())
        ],
        'por_division': [
            {'division': division, 'picking': round_metric(value)}
            for division, value in sorted(division_chart_totals.items(), key=lambda item: item[1], reverse=True)
        ],
        'top_skus': [
            {
                'sku': sku,
                'descripcion': values['descripcion'],
                'picking': round_metric(values['picking']),
            }
            for sku, values in sorted(sku_totals.items(), key=lambda item: item[1]['picking'], reverse=True)[:10]
        ],
        'pallets_vs_picking': {
            'bultos_palletizados': round_metric(total_bultos_palletizados),
            'bultos_manuales': round_metric(total_bultos_manuales),
            'total_bultos': round_metric(total_operativo),
            'pct_pallets': pct(total_bultos_palletizados, total_operativo),
            'pct_picking': pct(total_bultos_manuales, total_operativo),
        },
        'picking_por_division': picking_por_division,
        'picking_por_sucursal': picking_por_sucursal,
        'productividad_por_temporada': productividad_por_temporada,
    })
