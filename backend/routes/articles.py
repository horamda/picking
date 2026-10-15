from flask import Blueprint, g, request, jsonify, current_app
from sqlalchemy import inspect
from werkzeug.utils import secure_filename
from werkzeug.exceptions import ServiceUnavailable

from auth import auth_required, roles_required
from models import Article, UploadedFile
from services.csv_import import import_articles_from_csv
from services.file_storage import create_uploaded_file_record, mark_uploaded_file, uploaded_file_to_dict
from utils.db import db

articles_bp = Blueprint('articles', __name__)


def ensure_article_import_schema():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if 'articulos' not in tables or 'archivos_subidos' not in tables:
        raise ServiceUnavailable('Falta una migracion revisada para importar articulos.')


@articles_bp.route('', methods=['GET'])
@articles_bp.route('/', methods=['GET'])
@auth_required
def list_articles():
    filters = request.args
    try:
        page = max(int(filters.get('page', 1)), 1)
        per_page = min(max(int(filters.get('per_page', 50)), 1), 200)
    except ValueError:
        return jsonify({'error': 'Parametros de paginacion invalidos'}), 400

    query = Article.query
    if filters.get('activo') is not None:
        query = query.filter_by(activo=filters.get('activo') in ['1', 'true', 'True'])
    if filters.get('division'):
        query = query.filter(Article.division == filters.get('division'))
    if filters.get('q'):
        pattern = f"%{filters.get('q')}%"
        query = query.filter((Article.sku.like(pattern)) | (Article.descripcion.like(pattern)))

    pagination = query.order_by(Article.sku.asc()).paginate(page=page, per_page=per_page, error_out=False)
    items = [{
        'id': a.id,
        'sku': a.sku,
        'descripcion': a.descripcion,
        'division': a.division,
        'calibre': a.calibre,
        'unidades_por_bulto': a.unidades_por_bulto,
        'bultos_por_pallet': a.bultos_por_pallet,
        'activo': a.activo,
    } for a in pagination.items]

    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


@articles_bp.route('', methods=['POST'])
@articles_bp.route('/', methods=['POST'])
@roles_required('administrador', 'supervisor')
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
@roles_required('administrador', 'supervisor')
def import_csv():
    ensure_article_import_schema()

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
        if not file_bytes:
            return jsonify({'error': 'El archivo CSV esta vacio'}), 400

        uploaded_file = create_uploaded_file_record(
            file_bytes=file_bytes,
            filename=filename,
            original_filename=file.filename or filename,
            category='csv_articulos',
            content_type=file.mimetype,
        )
        db.session.add(uploaded_file)
        db.session.commit()
        uploaded_file_id = uploaded_file.id

        result = import_articles_from_csv(file_bytes, mode=mode)
        result['uploaded_file_id'] = uploaded_file_id
        if result.get('applied'):
            mark_uploaded_file(uploaded_file, 'procesado')
        else:
            first_error = (result.get('errors') or result.get('duplicates') or [{}])[0]
            mark_uploaded_file(uploaded_file, 'rechazado', first_error.get('error', 'CSV rechazado'))
        db.session.commit()
        status = 200 if result.get('applied') else 422
        return jsonify(result), status
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Error importando CSV de articulos')
        if 'uploaded_file_id' in locals() and uploaded_file_id:
            uploaded_file = db.session.get(UploadedFile, uploaded_file_id)
            if uploaded_file:
                mark_uploaded_file(uploaded_file, 'error', str(exc))
                db.session.commit()
        return jsonify({
            'applied': False,
            'error': 'Error interno importando CSV',
            'error_detail': str(exc),
            'errors': [{'row': None, 'error': f'Error interno del servidor: {str(exc)}'}],
            'duplicates': [],
            'created': 0, 'updated': 0, 'deleted': 0, 'unchanged': 0, 'inactive': 0,
        }), 500


@articles_bp.route('/import-diagnostics', methods=['GET'])
@roles_required('administrador', 'supervisor')
def import_diagnostics():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    last_upload = (
        UploadedFile.query
        .filter_by(category='csv_articulos')
        .order_by(UploadedFile.id.desc())
        .first()
        if 'archivos_subidos' in tables else None
    )
    return jsonify({
        'database': {
            'dialect': db.engine.dialect.name,
            'driver': db.engine.driver,
            'is_postgresql': db.engine.dialect.name == 'postgresql',
        },
        'user': {
            'username': g.current_user.username,
            'role': g.current_user.role.name,
        },
        'schema': {
            'articulos_table': 'articulos' in tables,
            'archivos_subidos_table': 'archivos_subidos' in tables,
        },
        'article_count': Article.query.count() if 'articulos' in tables else 0,
        'last_csv_upload': uploaded_file_to_dict(last_upload) if last_upload else None,
    })
