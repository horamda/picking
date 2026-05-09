from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from sqlalchemy import func
from auth import auth_required, roles_required
from models import Article, Consolidado, ConsolidadoDetalle
from utils.db import db

history_bp = Blueprint('history', __name__)


def round_metric(value, digits=2):
    return round(float(value or 0), digits)


def row_operational_metrics(item, article):
    pallet_capacity = (article.bultos_por_pallet if article else 0) or 0
    bultos_palletizados = float(item.pallets_completos or 0) * pallet_capacity
    bultos_picking = max(float(item.bultos_equivalentes or 0) - bultos_palletizados, 0)
    return bultos_palletizados, bultos_picking


def reparto_date_expr():
    return func.coalesce(Consolidado.fecha_reparto, Consolidado.processed_at)


def serialize_datetime(value):
    return value.isoformat() if value else None


@history_bp.route('/search', methods=['GET'])
@auth_required
def search():
    args = request.args
    query = Consolidado.query
    fecha = reparto_date_expr()
    if args.get('reparto'):
        query = query.filter(Consolidado.reparto == args.get('reparto'))
    if args.get('camion'):
        query = query.filter(Consolidado.camion == args.get('camion'))
    if args.get('deposito'):
        query = query.filter(Consolidado.deposito == args.get('deposito'))
    if args.get('desde'):
        query = query.filter(fecha >= datetime.fromisoformat(args.get('desde')))
    if args.get('hasta'):
        query = query.filter(fecha < datetime.fromisoformat(args.get('hasta')) + timedelta(days=1))
    if args.get('chofer'):
        query = query.filter(Consolidado.chofer == args.get('chofer'))
    if args.get('cancha'):
        query = query.join(ConsolidadoDetalle).filter(ConsolidadoDetalle.cancha == args.get('cancha'))
    results = query.order_by(fecha.desc()).all()
    return jsonify([{
        'id': c.id,
        'uploaded_file_id': c.uploaded_file_id,
        'filename': c.filename,
        'reparto': c.reparto,
        'fecha_reparto': serialize_datetime(c.fecha_reparto or c.processed_at),
        'camion': c.camion,
        'chofer': c.chofer,
        'deposito': c.deposito,
        'cancha': c.cancha,
        'almacen': c.almacen,
        'processed_at': serialize_datetime(c.processed_at),
    } for c in results])

@history_bp.route('/<int:consolidado_id>', methods=['DELETE'])
@roles_required('administrador', 'supervisor')
def delete(consolidado_id):
    consolidado = Consolidado.query.get_or_404(consolidado_id)
    ConsolidadoDetalle.query.filter_by(consolidado_id=consolidado.id).delete()
    db.session.delete(consolidado)
    db.session.commit()
    return jsonify({'deleted': consolidado_id})


@history_bp.route('/<int:consolidado_id>', methods=['GET'])
@auth_required
def detail(consolidado_id):
    consolidado = Consolidado.query.get_or_404(consolidado_id)
    detalles = (
        db.session.query(ConsolidadoDetalle, Article)
        .outerjoin(Article, Article.sku == ConsolidadoDetalle.sku)
        .filter(ConsolidadoDetalle.consolidado_id == consolidado.id)
        .all()
    )
    return jsonify({
        'id': consolidado.id,
        'uploaded_file_id': consolidado.uploaded_file_id,
        'filename': consolidado.filename,
        'reparto': consolidado.reparto,
        'fecha_reparto': serialize_datetime(consolidado.fecha_reparto or consolidado.processed_at),
        'camion': consolidado.camion,
        'chofer': consolidado.chofer,
        'deposito': consolidado.deposito,
        'cancha': consolidado.cancha,
        'almacen': consolidado.almacen,
        'processed_at': serialize_datetime(consolidado.processed_at),
        'detalles': [
            {
                'id': item.id,
                'sku': item.sku,
                'descripcion': item.descripcion,
                'bultos': item.bultos,
                'unidades': item.unidades,
                'bultos_equivalentes': round_metric(item.bultos_equivalentes),
                'pallets_completos': item.pallets_completos,
                'bultos_palletizados': round_metric(bultos_palletizados),
                'bultos_picking_equivalentes': round_metric(bultos_picking),
                'bultos_pickear': item.bultos_pickear,
                'total_bultos': round_metric(bultos_palletizados + bultos_picking),
                'unidades_sueltas': item.unidades_sueltas,
                'almacen': item.almacen,
                'cancha': item.cancha,
                'prioridad': item.prioridad,
                'sku_estado': item.sku_estado,
            }
            for item, article in detalles
            for bultos_palletizados, bultos_picking in [row_operational_metrics(item, article)]
        ]
    })
