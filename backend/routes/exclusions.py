from flask import Blueprint, jsonify, request

from auth import auth_required, roles_required
from models import ExcludedArticle
from utils.db import db

exclusions_bp = Blueprint('exclusions', __name__)


@exclusions_bp.route('/', methods=['GET'])
@auth_required
def list_exclusions():
    rows = ExcludedArticle.query.order_by(ExcludedArticle.sku.asc()).all()
    return jsonify([{
        'id': row.id,
        'sku': row.sku,
        'descripcion': row.descripcion,
        'motivo': row.motivo,
        'activo': row.activo,
    } for row in rows])


@exclusions_bp.route('/', methods=['POST'])
@roles_required('administrador', 'supervisor')
def create_exclusion():
    data = request.json or {}
    sku = str(data.get('sku', '')).strip()
    if not sku:
        return jsonify({'error': 'SKU requerido'}), 400

    row = ExcludedArticle.query.filter_by(sku=sku).first()
    if row:
        row.descripcion = data.get('descripcion', row.descripcion)
        row.motivo = data.get('motivo', row.motivo)
        row.activo = data.get('activo', True)
    else:
        row = ExcludedArticle(
            sku=sku,
            descripcion=data.get('descripcion'),
            motivo=data.get('motivo'),
            activo=data.get('activo', True),
        )
        db.session.add(row)
    db.session.commit()
    return jsonify({'id': row.id, 'sku': row.sku, 'activo': row.activo}), 201


@exclusions_bp.route('/<int:exclusion_id>', methods=['PUT'])
@roles_required('administrador', 'supervisor')
def update_exclusion(exclusion_id):
    row = ExcludedArticle.query.get_or_404(exclusion_id)
    data = request.json or {}
    row.descripcion = data.get('descripcion', row.descripcion)
    row.motivo = data.get('motivo', row.motivo)
    if 'activo' in data:
        row.activo = bool(data.get('activo'))
    db.session.commit()
    return jsonify({'id': row.id, 'sku': row.sku, 'activo': row.activo})
