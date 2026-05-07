from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from auth import auth_required, roles_required
from models import Consolidado, ConsolidadoDetalle
from utils.db import db

history_bp = Blueprint('history', __name__)

@history_bp.route('/search', methods=['GET'])
@auth_required
def search():
    args = request.args
    query = Consolidado.query
    if args.get('reparto'):
        query = query.filter(Consolidado.reparto == args.get('reparto'))
    if args.get('camion'):
        query = query.filter(Consolidado.camion == args.get('camion'))
    if args.get('deposito'):
        query = query.filter(Consolidado.deposito == args.get('deposito'))
    if args.get('desde'):
        query = query.filter(Consolidado.processed_at >= datetime.fromisoformat(args.get('desde')))
    if args.get('hasta'):
        query = query.filter(Consolidado.processed_at < datetime.fromisoformat(args.get('hasta')) + timedelta(days=1))
    if args.get('chofer'):
        query = query.filter(Consolidado.chofer == args.get('chofer'))
    if args.get('cancha'):
        query = query.join(ConsolidadoDetalle).filter(ConsolidadoDetalle.cancha == args.get('cancha'))
    results = query.order_by(Consolidado.processed_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'uploaded_file_id': c.uploaded_file_id,
        'filename': c.filename,
        'reparto': c.reparto,
        'camion': c.camion,
        'chofer': c.chofer,
        'deposito': c.deposito,
        'cancha': c.cancha,
        'almacen': c.almacen,
        'processed_at': c.processed_at.isoformat(),
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
    detalles = ConsolidadoDetalle.query.filter_by(consolidado_id=consolidado.id).all()
    return jsonify({
        'id': consolidado.id,
        'uploaded_file_id': consolidado.uploaded_file_id,
        'filename': consolidado.filename,
        'reparto': consolidado.reparto,
        'camion': consolidado.camion,
        'chofer': consolidado.chofer,
        'deposito': consolidado.deposito,
        'cancha': consolidado.cancha,
        'almacen': consolidado.almacen,
        'processed_at': consolidado.processed_at.isoformat(),
        'detalles': [{
            'id': item.id,
            'sku': item.sku,
            'descripcion': item.descripcion,
            'bultos': item.bultos,
            'unidades': item.unidades,
            'pallets_completos': item.pallets_completos,
            'bultos_pickear': item.bultos_pickear,
            'unidades_sueltas': item.unidades_sueltas,
            'almacen': item.almacen,
            'cancha': item.cancha,
            'prioridad': item.prioridad,
            'sku_estado': item.sku_estado,
        } for item in detalles]
    })
