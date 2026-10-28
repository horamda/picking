import os
import sys
import threading
import time
import json
from pathlib import Path

# Shared deterministic voice converter lives alongside backend/.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from config import Config
from sqlalchemy import inspect, text

from utils.db import db
from auth import AuthService
from routes.auth import auth_bp
from routes.articles import articles_bp
from routes.uploads import uploads_bp
from routes.dashboard import dashboard_bp
from routes.history import history_bp
from routes.operations import operations_bp
from routes.exclusions import exclusions_bp
from routes.load_control import load_control_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r'/api/*': {'origins': Config.CORS_ORIGINS}})
db.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(articles_bp, url_prefix='/api/articles')
app.register_blueprint(uploads_bp, url_prefix='/api/uploads')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(history_bp, url_prefix='/api/history')
app.register_blueprint(operations_bp, url_prefix='/api/operations')
app.register_blueprint(exclusions_bp, url_prefix='/api/exclusions')
app.register_blueprint(load_control_bp, url_prefix='/api/load-control')

FRONTEND_DIST = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
_db_init_lock = threading.Lock()
_db_initialized = False
_db_init_error = None

@app.before_request
def request_clock():
    g.request_started = time.perf_counter()


@app.after_request
def request_metrics(response):
    duration = round((time.perf_counter() - getattr(g, 'request_started', time.perf_counter())) * 1000, 2)
    response.headers['Server-Timing'] = f'app;dur={duration}'
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    user = getattr(g, 'current_user', None)
    if user and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        from models import LogEntry
        user_id = user.id
        try:
            db.session.rollback()
            db.session.add(LogEntry(user_id=user_id, entity='api_activity', action=request.endpoint or 'api',
                details=json.dumps(dict(method=request.method, route=str(request.url_rule), status=response.status_code,
                    server_ms=duration))))
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.error('No se pudo guardar la metrica de actividad del sistema.')
    return response


@app.route('/')
def index():
    if FRONTEND_DIST.exists():
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return {'status': 'ok', 'service': 'picking-analytics'}

@app.route('/api/runtime-config')
def runtime_config():
    return {'mode': Config.APP_MODE, 'shared_database': not Config.SQLALCHEMY_DATABASE_URI.startswith('sqlite')}

@app.route('/healthz')
def healthz():
    return {'status': 'ok'}

@app.route('/readyz')
def readyz():
    if ensure_database_ready():
        return {'status': 'ready'}
    return {'status': 'degraded', 'database_error': _db_init_error}, 503

@app.before_request
def ensure_database_for_api():
    if not request.path.startswith('/api/'):
        return None

    if ensure_database_ready():
        return None

    return jsonify({
        'error': 'Base de datos no disponible',
        'error_detail': _db_init_error,
    }), 503

@app.route('/assets/<path:filename>')
def frontend_assets(filename):
    return send_from_directory(FRONTEND_DIST / 'assets', filename)

@app.route('/<path:filename>')
def frontend_app(filename):
    if not FRONTEND_DIST.exists():
        return {'error': 'frontend build not found'}, 404

    target = FRONTEND_DIST / filename
    if target.is_file():
        return send_from_directory(FRONTEND_DIST, filename)
    return send_from_directory(FRONTEND_DIST, 'index.html')

def initialize_database():
    global _db_initialized, _db_init_error
    with app.app_context():
        app.logger.info('Inicializando base de datos')
        existing_database = not Config.SQLALCHEMY_DATABASE_URI.startswith('sqlite')
        if existing_database:
            # Shared databases are changed only through reviewed migrations.
            inspector = inspect(db.engine)
            existing = set(inspector.get_table_names())
            missing = set(db.metadata.tables) - existing
            if missing:
                raise RuntimeError('Falta una migracion revisada para: ' + ', '.join(sorted(missing)))
            for name, table in db.metadata.tables.items():
                columns = {column['name'] for column in inspector.get_columns(name)}
                missing_columns = set(table.columns.keys()) - columns
                if missing_columns:
                    raise RuntimeError('Falta una migracion revisada para columnas de ' + name + ': ' + ', '.join(sorted(missing_columns)))
        else:
            db.create_all()
            ensure_runtime_schema()
            backfill_missing_reparto_dates()
            AuthService.initialize_roles()
            seed_default_exclusions()
            seed_admin_user()
        _db_initialized = True
        _db_init_error = None
        app.logger.info('Base de datos inicializada')

def ensure_database_ready():
    global _db_init_error
    if _db_initialized:
        return True

    with _db_init_lock:
        if _db_initialized:
            return True
        try:
            initialize_database()
            return True
        except Exception as exc:
            _db_init_error = str(exc)
            app.logger.exception('No se pudo inicializar la base de datos')
            return False

def seed_admin_user():
    from models import User, Role
    admin_username = os.getenv('ADMIN_USER', 'admin')
    admin_password = os.getenv('ADMIN_PASSWORD', 'admin1234')
    if not User.query.filter_by(username=admin_username).first():
        role = Role.query.filter_by(name='administrador').first()
        db.session.add(User(
            username=admin_username,
            email=os.getenv('ADMIN_EMAIL', f'{admin_username}@picking.local'),
            password_hash=AuthService.hash_password(admin_password),
            role=role,
            active=True,
        ))
        db.session.commit()

def ensure_runtime_schema():
    inspector = inspect(db.engine)
    if 'consolidado_detalle' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('consolidado_detalle')}
        if 'bultos_equivalentes' not in columns:
            db.session.execute(text('ALTER TABLE consolidado_detalle ADD COLUMN bultos_equivalentes FLOAT NOT NULL DEFAULT 0'))
            db.session.commit()
    if 'consolidados' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('consolidados')}
        if 'uploaded_file_id' not in columns:
            db.session.execute(text('ALTER TABLE consolidados ADD COLUMN uploaded_file_id INTEGER'))
            db.session.commit()
        if 'fecha_reparto' not in columns:
            date_type = 'TIMESTAMP' if db.engine.dialect.name == 'postgresql' else 'DATETIME'
            db.session.execute(text(f'ALTER TABLE consolidados ADD COLUMN fecha_reparto {date_type}'))
            db.session.commit()
    if 'errores_procesamiento' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('errores_procesamiento')}
        if 'uploaded_file_id' not in columns:
            db.session.execute(text('ALTER TABLE errores_procesamiento ADD COLUMN uploaded_file_id INTEGER'))
            db.session.commit()

def backfill_missing_reparto_dates():
    from models import Consolidado
    from routes.uploads import parse_pdf_bytes

    missing = (
        Consolidado.query
        .filter(Consolidado.fecha_reparto.is_(None), Consolidado.uploaded_file_id.isnot(None))
        .all()
    )
    if not missing:
        return

    parsed_by_file = {}
    updated = 0
    for consolidado in missing:
        uploaded_file = consolidado.uploaded_file
        if not uploaded_file or not uploaded_file.data:
            continue

        if uploaded_file.id not in parsed_by_file:
            try:
                parsed = parse_pdf_bytes(uploaded_file.data, uploaded_file.filename or 'archivo.pdf')
                parsed_by_file[uploaded_file.id] = parsed.get('consolidados') or [parsed]
            except Exception as exc:
                app.logger.warning('No se pudo leer fecha de reparto desde %s: %s', uploaded_file.filename, exc)
                parsed_by_file[uploaded_file.id] = []

        for parsed_consolidado in parsed_by_file[uploaded_file.id]:
            same_reparto = str(parsed_consolidado.get('reparto') or '').strip() == str(consolidado.reparto or '').strip()
            if same_reparto and parsed_consolidado.get('fecha_reparto'):
                consolidado.fecha_reparto = parsed_consolidado['fecha_reparto']
                updated += 1
                break

    if updated:
        db.session.commit()

def seed_default_exclusions():
    from models import ExcludedArticle

    defaults = [
        ('2731', 'Envase no operativo para picking/pallets'),
        ('2776', 'Envase no operativo para picking/pallets'),
        ('2777', 'Envase no operativo para picking/pallets'),
    ]
    for sku, motivo in defaults:
        if not ExcludedArticle.query.filter_by(sku=sku).first():
            db.session.add(ExcludedArticle(sku=sku, motivo=motivo, activo=True))
    db.session.commit()

if Config.INIT_DB_ON_STARTUP:
    threading.Thread(target=ensure_database_ready, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5001')), debug=os.getenv('FLASK_DEBUG') == '1')
