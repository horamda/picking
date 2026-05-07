from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from auth import auth_required
from models import Article, ConsolidadoDetalle, Consolidado, ProcessingBatch
from sqlalchemy import distinct, func
from utils.db import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/summary', methods=['GET'])
@auth_required
def summary():
    base = db.session.query(Consolidado).join(ConsolidadoDetalle)
    base = apply_dashboard_filters(base)
    consolidado_ids = [row.id for row in base.with_entities(Consolidado.id).distinct().all()]
    detail_query = ConsolidadoDetalle.query
    if consolidado_ids:
        detail_query = detail_query.filter(ConsolidadoDetalle.consolidado_id.in_(consolidado_ids))
    else:
        detail_query = detail_query.filter(False)

    total_pdfs = db.session.query(func.count(distinct(Consolidado.filename))).filter(Consolidado.id.in_(consolidado_ids)).scalar() if consolidado_ids else 0
    total_batches = db.session.query(func.count(distinct(Consolidado.batch_id))).filter(Consolidado.id.in_(consolidado_ids)).scalar() if consolidado_ids else 0
    total_repartos = len(consolidado_ids)
    total_camiones = db.session.query(func.count(distinct(Consolidado.camion))).filter(Consolidado.id.in_(consolidado_ids)).scalar() if consolidado_ids else 0
    total_pallets = detail_query.with_entities(func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0)).scalar()
    total_bultos_pick = detail_query.with_entities(func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0)).scalar()
    total_unidades_sueltas = detail_query.with_entities(func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0)).scalar()
    skus_no_encontrados = detail_query.filter_by(sku_estado='no encontrado').count()
    top_division = (
        db.session.query(Article.division, func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('pick'))
        .join(ConsolidadoDetalle, ConsolidadoDetalle.sku == Article.sku)
        .group_by(Article.division)
        .order_by(func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).desc())
        .first()
    )
    return jsonify({
        'pdfs_procesados': total_pdfs,
        'lotes_procesados': total_batches,
        'repartos_procesados': total_repartos,
        'camiones_procesados': total_camiones,
        'pallets_completos': total_pallets,
        'bultos_pick': total_bultos_pick,
        'unidades_sueltas': total_unidades_sueltas,
        'skus_no_encontrados': skus_no_encontrados,
        'division_mayor_picking': top_division.division if top_division else 'Sin maestro',
        'tiempo_promedio': 0,
    })

def apply_dashboard_filters(query):
    args = request.args
    if args.get('desde'):
        query = query.filter(Consolidado.processed_at >= datetime.fromisoformat(args.get('desde')))
    if args.get('hasta'):
        query = query.filter(Consolidado.processed_at < datetime.fromisoformat(args.get('hasta')) + timedelta(days=1))
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
    by_day = (
        db.session.query(
            func.date(Consolidado.processed_at).label('fecha'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('picking'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets'),
        )
        .join(ConsolidadoDetalle, ConsolidadoDetalle.consolidado_id == Consolidado.id)
        .group_by(func.date(Consolidado.processed_at))
        .order_by(func.date(Consolidado.processed_at))
        .all()
    )
    by_division = (
        db.session.query(
            func.coalesce(Article.division, 'Sin maestro').label('division'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('picking'),
        )
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
        .group_by(func.coalesce(Article.division, 'Sin maestro'))
        .order_by(func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).desc())
        .all()
    )
    top_skus = (
        db.session.query(
            ConsolidadoDetalle.sku,
            func.max(ConsolidadoDetalle.descripcion).label('descripcion'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('picking'),
        )
        .group_by(ConsolidadoDetalle.sku)
        .order_by(func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).desc())
        .limit(10)
        .all()
    )
    return jsonify({
        'por_dia': [{'fecha': str(row.fecha), 'picking': row.picking, 'pallets': row.pallets} for row in by_day],
        'por_division': [{'division': row.division, 'picking': row.picking} for row in by_division],
        'top_skus': [{'sku': row.sku, 'descripcion': row.descripcion, 'picking': row.picking} for row in top_skus],
    })
