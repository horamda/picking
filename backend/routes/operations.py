from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from auth import auth_required
from models import Article, Consolidado, ConsolidadoDetalle, ExcludedArticle
from utils.db import db

operations_bp = Blueprint('operations', __name__)


def round_metric(value, digits=2):
    return round(float(value or 0), digits)


def row_operational_metrics(detalle, article):
    pallet_capacity = (article.bultos_por_pallet if article else 0) or 0
    bultos_palletizados = float(detalle.pallets_completos or 0) * pallet_capacity
    bultos_picking = max(float(detalle.bultos_equivalentes or 0) - bultos_palletizados, 0)
    return bultos_palletizados, bultos_picking


def operational_sql_expressions():
    bultos_palletizados = ConsolidadoDetalle.pallets_completos * func.coalesce(Article.bultos_por_pallet, 0)
    bultos_picking = ConsolidadoDetalle.bultos_equivalentes - bultos_palletizados
    return bultos_palletizados, bultos_picking


def reparto_date_expr():
    return func.coalesce(Consolidado.fecha_reparto, Consolidado.processed_at)


def serialize_datetime(value):
    return value.isoformat() if value else None


def apply_common_filters(query):
    args = request.args
    fecha = reparto_date_expr()
    if args.get('desde'):
        desde = datetime.fromisoformat(args.get('desde'))
        query = query.filter(fecha >= desde)
    if args.get('hasta'):
        hasta = datetime.fromisoformat(args.get('hasta')) + timedelta(days=1)
        query = query.filter(fecha < hasta)
    if args.get('reparto'):
        query = query.filter(Consolidado.reparto == args.get('reparto'))
    if args.get('camion'):
        query = query.filter(Consolidado.camion == args.get('camion'))
    if args.get('deposito'):
        query = query.filter(Consolidado.deposito == args.get('deposito'))
    if args.get('cancha'):
        query = query.filter(ConsolidadoDetalle.cancha == args.get('cancha'))
    if args.get('division'):
        query = query.filter(Article.division == args.get('division'))
    return query


def serialize_detail(detalle, consolidado, article):
    bultos_palletizados, bultos_picking = row_operational_metrics(detalle, article)
    return {
        'id': detalle.id,
        'reparto': consolidado.reparto,
        'fecha_reparto': serialize_datetime(consolidado.fecha_reparto or consolidado.processed_at),
        'processed_at': serialize_datetime(consolidado.processed_at),
        'camion': consolidado.camion,
        'chofer': consolidado.chofer,
        'deposito': consolidado.deposito,
        'sku': detalle.sku,
        'descripcion': detalle.descripcion,
        'division': article.division if article else None,
        'calibre': article.calibre if article else None,
        'cancha': detalle.cancha,
        'almacen': detalle.almacen,
        'bultos': detalle.bultos,
        'unidades': detalle.unidades,
        'bultos_equivalentes': detalle.bultos_equivalentes,
        'pallets_completos': detalle.pallets_completos,
        'bultos_palletizados': round_metric(bultos_palletizados),
        'bultos_picking_equivalentes': round_metric(bultos_picking),
        'bultos_pickear': detalle.bultos_pickear,
        'total_bultos': round_metric(bultos_palletizados + bultos_picking),
        'unidades_sueltas': detalle.unidades_sueltas,
        'prioridad': detalle.prioridad,
        'sku_estado': detalle.sku_estado,
    }


@operations_bp.route('/trucks', methods=['GET'])
@auth_required
def trucks():
    bultos_palletizados_expr, bultos_picking_expr = operational_sql_expressions()
    fecha_expr = reparto_date_expr()
    query = (
        db.session.query(
            Consolidado.id,
            Consolidado.reparto,
            fecha_expr.label('fecha_reparto'),
            Consolidado.camion,
            Consolidado.chofer,
            Consolidado.deposito,
            Consolidado.processed_at,
            func.count(ConsolidadoDetalle.id).label('skus'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos), 0).label('bultos'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades), 0).label('unidades'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_equivalentes), 0).label('bultos_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets_completos'),
            func.coalesce(func.sum(bultos_palletizados_expr), 0).label('bultos_palletizados'),
            func.coalesce(func.sum(bultos_picking_expr), 0).label('bultos_picking_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('bultos_pickear'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0).label('unidades_sueltas'),
        )
        .join(ConsolidadoDetalle, ConsolidadoDetalle.consolidado_id == Consolidado.id)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
    )
    query = apply_common_filters(query)
    rows = (
        query
        .group_by(
            Consolidado.id,
            Consolidado.reparto,
            Consolidado.fecha_reparto,
            Consolidado.camion,
            Consolidado.chofer,
            Consolidado.deposito,
            Consolidado.processed_at,
        )
        .order_by(fecha_expr.desc())
        .all()
    )
    return jsonify([{
        'id': row.id,
        'reparto': row.reparto,
        'fecha_reparto': serialize_datetime(row.fecha_reparto),
        'camion': row.camion,
        'chofer': row.chofer,
        'deposito': row.deposito,
        'processed_at': serialize_datetime(row.processed_at),
        'skus': row.skus,
        'bultos': row.bultos,
        'unidades': row.unidades,
        'bultos_equivalentes': round_metric(row.bultos_equivalentes),
        'pallets_completos': row.pallets_completos,
        'bultos_palletizados': round_metric(row.bultos_palletizados),
        'bultos_picking_equivalentes': round_metric(row.bultos_picking_equivalentes),
        'bultos_pickear': row.bultos_pickear,
        'total_bultos': round_metric((row.bultos_palletizados or 0) + (row.bultos_picking_equivalentes or 0)),
        'unidades_sueltas': row.unidades_sueltas,
    } for row in rows])


@operations_bp.route('/picking', methods=['GET'])
@auth_required
def picking():
    query = (
        db.session.query(ConsolidadoDetalle, Consolidado, Article)
        .join(Consolidado, Consolidado.id == ConsolidadoDetalle.consolidado_id)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
        .filter((ConsolidadoDetalle.bultos_pickear > 0) | (ConsolidadoDetalle.unidades_sueltas > 0))
    )
    query = apply_common_filters(query)
    rows = query.order_by(ConsolidadoDetalle.prioridad.asc(), ConsolidadoDetalle.cancha.asc(), ConsolidadoDetalle.almacen.asc()).all()
    return jsonify([serialize_detail(detalle, consolidado, article) for detalle, consolidado, article in rows])


@operations_bp.route('/pallets', methods=['GET'])
@auth_required
def pallets():
    query = (
        db.session.query(ConsolidadoDetalle, Consolidado, Article)
        .join(Consolidado, Consolidado.id == ConsolidadoDetalle.consolidado_id)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
        .filter(ConsolidadoDetalle.pallets_completos > 0)
    )
    query = apply_common_filters(query)
    rows = query.order_by(Consolidado.camion.asc(), ConsolidadoDetalle.sku.asc()).all()
    return jsonify([serialize_detail(detalle, consolidado, article) for detalle, consolidado, article in rows])


@operations_bp.route('/picking-by-cancha', methods=['GET'])
@auth_required
def picking_by_cancha():
    bultos_palletizados_expr, bultos_picking_expr = operational_sql_expressions()
    query = (
        db.session.query(
            ConsolidadoDetalle.cancha,
            func.count(ConsolidadoDetalle.id).label('skus'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_equivalentes), 0).label('bultos_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets_completos'),
            func.coalesce(func.sum(bultos_palletizados_expr), 0).label('bultos_palletizados'),
            func.coalesce(func.sum(bultos_picking_expr), 0).label('bultos_picking_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('bultos_pickear'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0).label('unidades_sueltas'),
        )
        .join(Consolidado, Consolidado.id == ConsolidadoDetalle.consolidado_id)
        .join(Article, Article.sku == ConsolidadoDetalle.sku)
        .filter(
            (ConsolidadoDetalle.bultos_pickear > 0)
            | (ConsolidadoDetalle.unidades_sueltas > 0)
            | (ConsolidadoDetalle.pallets_completos > 0),
            ConsolidadoDetalle.sku_estado == 'encontrado',
            ~ConsolidadoDetalle.sku.in_(
                db.session.query(ExcludedArticle.sku).filter(ExcludedArticle.activo == True)
            ),
        )
    )
    query = apply_common_filters(query)
    rows = (
        query
        .group_by(ConsolidadoDetalle.cancha)
        .order_by(ConsolidadoDetalle.cancha.asc())
        .all()
    )
    payload = []
    for row in rows:
        bultos_palletizados = float(row.bultos_palletizados or 0)
        bultos_picking = float(row.bultos_picking_equivalentes or 0)
        payload.append({
            'cancha': row.cancha,
            'skus': row.skus,
            'bultos_equivalentes': round(float(row.bultos_equivalentes), 2),
            'pallets_completos': row.pallets_completos,
            'bultos_palletizados': round(bultos_palletizados, 2),
            'bultos_picking_equivalentes': round(bultos_picking, 2),
            'bultos_pickear': row.bultos_pickear,
            'total_bultos': round(bultos_palletizados + bultos_picking, 2),
            'unidades_sueltas': row.unidades_sueltas,
        })
    return jsonify(payload)


@operations_bp.route('/by-court', methods=['GET'])
@auth_required
def by_court():
    bultos_palletizados_expr, bultos_picking_expr = operational_sql_expressions()
    query = (
        db.session.query(
            ConsolidadoDetalle.cancha,
            ConsolidadoDetalle.almacen,
            func.count(ConsolidadoDetalle.id).label('skus'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_equivalentes), 0).label('bultos_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets_completos'),
            func.coalesce(func.sum(bultos_palletizados_expr), 0).label('bultos_palletizados'),
            func.coalesce(func.sum(bultos_picking_expr), 0).label('bultos_picking_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('bultos_pickear'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0).label('unidades_sueltas'),
        )
        .join(Consolidado, Consolidado.id == ConsolidadoDetalle.consolidado_id)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
    )
    query = apply_common_filters(query)
    rows = (
        query
        .group_by(ConsolidadoDetalle.cancha, ConsolidadoDetalle.almacen)
        .order_by(ConsolidadoDetalle.cancha.asc(), ConsolidadoDetalle.almacen.asc())
        .all()
    )
    return jsonify([{
        'cancha': row.cancha,
        'almacen': row.almacen,
        'skus': row.skus,
        'bultos_equivalentes': round(row.bultos_equivalentes, 2),
        'pallets_completos': row.pallets_completos,
        'bultos_palletizados': round_metric(row.bultos_palletizados),
        'bultos_picking_equivalentes': round_metric(row.bultos_picking_equivalentes),
        'bultos_pickear': row.bultos_pickear,
        'total_bultos': round_metric((row.bultos_palletizados or 0) + (row.bultos_picking_equivalentes or 0)),
        'unidades_sueltas': row.unidades_sueltas,
    } for row in rows])
