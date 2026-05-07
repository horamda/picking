import os
from pathlib import Path

from flask import Flask, send_from_directory
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

FRONTEND_DIST = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'

@app.route('/')
def index():
    if FRONTEND_DIST.exists():
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return {'status': 'ok', 'service': 'picking-analytics'}

@app.route('/healthz')
def healthz():
    return {'status': 'ok'}

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
    with app.app_context():
        db.create_all()
        ensure_runtime_schema()
        AuthService.initialize_roles()
        seed_default_exclusions()
        seed_admin_user()

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
    if 'errores_procesamiento' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('errores_procesamiento')}
        if 'uploaded_file_id' not in columns:
            db.session.execute(text('ALTER TABLE errores_procesamiento ADD COLUMN uploaded_file_id INTEGER'))
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
    initialize_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=os.getenv('FLASK_DEBUG') == '1')
