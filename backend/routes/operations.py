from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from auth import auth_required
from models import Article, Consolidado, ConsolidadoDetalle, ExcludedArticle
from utils.db import db

operations_bp = Blueprint('operations', __name__)


def apply_common_filters(query):
    args = request.args
    if args.get('desde'):
        desde = datetime.fromisoformat(args.get('desde'))
        query = query.filter(Consolidado.processed_at >= desde)
    if args.get('hasta'):
        hasta = datetime.fromisoformat(args.get('hasta')) + timedelta(days=1)
        query = query.filter(Consolidado.processed_at < hasta)
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
    return {
        'id': detalle.id,
        'reparto': consolidado.reparto,
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
        'bultos_pickear': detalle.bultos_pickear,
        'unidades_sueltas': detalle.unidades_sueltas,
        'prioridad': detalle.prioridad,
        'sku_estado': detalle.sku_estado,
    }


@operations_bp.route('/trucks', methods=['GET'])
@auth_required
def trucks():
    query = (
        db.session.query(
            Consolidado.id,
            Consolidado.reparto,
            Consolidado.camion,
            Consolidado.chofer,
            Consolidado.deposito,
            Consolidado.processed_at,
            func.count(ConsolidadoDetalle.id).label('skus'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos), 0).label('bultos'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades), 0).label('unidades'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets_completos'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('bultos_pickear'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0).label('unidades_sueltas'),
        )
        .join(ConsolidadoDetalle, ConsolidadoDetalle.consolidado_id == Consolidado.id)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
    )
    query = apply_common_filters(query)
    rows = (
        query
        .group_by(Consolidado.id)
        .order_by(Consolidado.processed_at.desc())
        .all()
    )
    return jsonify([{
        'id': row.id,
        'reparto': row.reparto,
        'camion': row.camion,
        'chofer': row.chofer,
        'deposito': row.deposito,
        'processed_at': row.processed_at.isoformat(),
        'skus': row.skus,
        'bultos': row.bultos,
        'unidades': row.unidades,
        'pallets_completos': row.pallets_completos,
        'bultos_pickear': row.bultos_pickear,
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
    query = (
        db.session.query(
            ConsolidadoDetalle.cancha,
            func.count(ConsolidadoDetalle.id).label('skus'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_equivalentes), 0).label('bultos_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets_completos'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_pickear), 0).label('bultos_pickear'),
            func.coalesce(func.sum(ConsolidadoDetalle.unidades_sueltas), 0).label('unidades_sueltas'),
        )
        .join(Consolidado, Consolidado.id == ConsolidadoDetalle.consolidado_id)
        .join(Article, Article.sku == ConsolidadoDetalle.sku)
        .filter(
            (ConsolidadoDetalle.bultos_pickear > 0) | (ConsolidadoDetalle.unidades_sueltas > 0),
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
    return jsonify([{
        'cancha': row.cancha,
        'skus': row.skus,
        'bultos_equivalentes': round(float(row.bultos_equivalentes), 2),
        'pallets_completos': row.pallets_completos,
        'bultos_pickear': row.bultos_pickear,
        'unidades_sueltas': row.unidades_sueltas,
    } for row in rows])


@operations_bp.route('/by-court', methods=['GET'])
@auth_required
def by_court():
    query = (
        db.session.query(
            ConsolidadoDetalle.cancha,
            ConsolidadoDetalle.almacen,
            func.count(ConsolidadoDetalle.id).label('skus'),
            func.coalesce(func.sum(ConsolidadoDetalle.bultos_equivalentes), 0).label('bultos_equivalentes'),
            func.coalesce(func.sum(ConsolidadoDetalle.pallets_completos), 0).label('pallets_completos'),
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
        'bultos_pickear': row.bultos_pickear,
        'unidades_sueltas': row.unidades_sueltas,
    } for row in rows])
