from datetime import datetime
from utils.db import db

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    users = db.relationship('User', backref='role', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    logs = db.relationship('LogEntry', backref='user', lazy=True)

class Article(db.Model):
    __tablename__ = 'articulos'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(128), unique=True, nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    division = db.Column(db.String(120), nullable=True)
    calibre = db.Column(db.String(120), nullable=True)
    unidades_por_bulto = db.Column(db.Integer, nullable=False, default=1)
    bultos_por_pallet = db.Column(db.Integer, nullable=False, default=1)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExcludedArticle(db.Model):
    __tablename__ = 'articulos_excluidos'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(128), unique=True, nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    motivo = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UploadedFile(db.Model):
    __tablename__ = 'archivos_subidos'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('lotes_procesamiento.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(80), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    checksum_sha256 = db.Column(db.String(64), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    status = db.Column(db.String(80), nullable=False, default='recibido')
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

class ProcessingBatch(db.Model):
    __tablename__ = 'lotes_procesamiento'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    origen = db.Column(db.String(255), nullable=True)
    estado = db.Column(db.String(80), nullable=False, default='pendiente')
    consolidados = db.relationship('Consolidado', backref='batch', lazy=True)
    uploaded_files = db.relationship('UploadedFile', backref='batch', lazy=True)

class Consolidado(db.Model):
    __tablename__ = 'consolidados'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('lotes_procesamiento.id'), nullable=False)
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey('archivos_subidos.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    reparto = db.Column(db.String(120), nullable=True)
    camion = db.Column(db.String(120), nullable=True)
    chofer = db.Column(db.String(120), nullable=True)
    deposito = db.Column(db.String(120), nullable=True)
    cancha = db.Column(db.String(120), nullable=True)
    almacen = db.Column(db.String(120), nullable=True)
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    detalles = db.relationship('ConsolidadoDetalle', backref='consolidado', lazy=True)
    uploaded_file = db.relationship('UploadedFile', backref='consolidados')

class ConsolidadoDetalle(db.Model):
    __tablename__ = 'consolidado_detalle'
    id = db.Column(db.Integer, primary_key=True)
    consolidado_id = db.Column(db.Integer, db.ForeignKey('consolidados.id'), nullable=False)
    sku = db.Column(db.String(128), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    bultos = db.Column(db.Integer, nullable=False, default=0)
    unidades = db.Column(db.Integer, nullable=False, default=0)
    unidades_equivalentes = db.Column(db.Float, nullable=False, default=0.0)
    bultos_equivalentes = db.Column(db.Float, nullable=False, default=0.0)
    pallets_completos = db.Column(db.Integer, nullable=False, default=0)
    bultos_pickear = db.Column(db.Integer, nullable=False, default=0)
    unidades_sueltas = db.Column(db.Integer, nullable=False, default=0)
    almacen = db.Column(db.String(120), nullable=True)
    cancha = db.Column(db.String(120), nullable=True)
    prioridad = db.Column(db.String(50), nullable=True)
    sku_estado = db.Column(db.String(80), nullable=True)

class LogEntry(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    entity = db.Column(db.String(120), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True)

class ProcessingError(db.Model):
    __tablename__ = 'errores_procesamiento'
    id = db.Column(db.Integer, primary_key=True)
    uploaded_file_id = db.Column(db.Integer, db.ForeignKey('archivos_subidos.id'), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    traceback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_file = db.relationship('UploadedFile', backref='processing_errors')
