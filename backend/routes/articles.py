from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from models import Article
from services.csv_import import import_articles_from_csv
from utils.db import db

articles_bp = Blueprint('articles', __name__)


@articles_bp.route('/', methods=['GET'])
def list_articles():
    filters = request.args
    query = Article.query
    if filters.get('activo') is not None:
        query = query.filter_by(activo=filters.get('activo') in ['1', 'true', 'True'])
    if filters.get('division'):
        query = query.filter(Article.division == filters.get('division'))
    if filters.get('q'):
        pattern = f"%{filters.get('q')}%"
        query = query.filter((Article.sku.like(pattern)) | (Article.descripcion.like(pattern)))

    articles = query.order_by(Article.sku.asc()).all()
    return jsonify([{
        'id': a.id,
        'sku': a.sku,
        'descripcion': a.descripcion,
        'division': a.division,
        'calibre': a.calibre,
        'unidades_por_bulto': a.unidades_por_bulto,
        'bultos_por_pallet': a.bultos_por_pallet,
        'activo': a.activo,
    } for a in articles])


@articles_bp.route('/', methods=['POST'])
def create_article():
    data = request.json or {}
    article = Article(
        sku=data.get('sku'),
        descripcion=data.get('descripcion'),
        division=data.get('division'),
        calibre=data.get('calibre'),
        unidades_por_bulto=data.get('unidades_por_bulto', 1),
        bultos_por_pallet=data.get('bultos_por_pallet', 1),
        activo=data.get('activo', True)
    )
    db.session.add(article)
    db.session.commit()
    return jsonify({'message': 'Articulo creado', 'id': article.id}), 201


@articles_bp.route('/import-csv', methods=['POST'])
def import_csv():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No se recibio archivo CSV'}), 400

    mode = request.form.get('mode', request.args.get('mode', 'merge')).lower()
    if mode not in ['merge', 'replace']:
        return jsonify({'error': 'Modo invalido. Usar merge o replace'}), 400

    filename = secure_filename(file.filename or 'articulos.csv')
    if not filename.lower().endswith('.csv'):
        return jsonify({'error': 'El archivo debe ser CSV'}), 400

    try:
        file_bytes = file.read()
        result = import_articles_from_csv(file_bytes, mode=mode)
        status = 200 if result.get('applied') else 422
        return jsonify(result), status
    except Exception as exc:
        return jsonify({
            'applied': False,
            'errors': [{'row': None, 'error': f'Error interno del servidor: {str(exc)}'}],
            'duplicates': [],
            'created': 0, 'updated': 0, 'deleted': 0, 'unchanged': 0, 'inactive': 0,
        }), 500
