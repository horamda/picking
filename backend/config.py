import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

def normalize_database_url(database_url: str) -> str:
    if database_url.startswith('${{') or database_url.startswith('$'):
        raise RuntimeError(
            'DATABASE_URL no fue resuelto por Railway. En Variables usa DATABASE_URL=${{Postgres.DATABASE_URL}} '
            'y verifica que el servicio de PostgreSQL se llame Postgres o ajusta el nombre en la referencia.'
        )
    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    if database_url.startswith('postgresql://'):
        return database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return database_url

def parse_csv_env(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]

def is_railway_environment() -> bool:
    return any(os.getenv(name) for name in ['RAILWAY_ENVIRONMENT', 'RAILWAY_PROJECT_ID', 'RAILWAY_SERVICE_ID'])

def get_database_url() -> str:
    database_url = os.getenv('DATABASE_URL', '').strip()
    isolated_tests = os.getenv('ALLOW_SQLITE_FOR_TESTS') == '1'
    if not database_url:
        raise RuntimeError('Falta DATABASE_URL. Configurá la conexión PostgreSQL de Railway; en local usá su URL pública.')
    if database_url.startswith('sqlite'):
        if not isolated_tests or is_railway_environment():
            raise RuntimeError('SQLite está deshabilitado. Usá la base de Railway; SQLite solo se admite en pruebas automáticas aisladas.')
    elif not database_url.startswith(('postgres://', 'postgresql://', 'postgresql+psycopg://')):
        raise RuntimeError('DATABASE_URL debe apuntar a PostgreSQL de Railway.')
    if not is_railway_environment() and '.railway.internal' in database_url:
        raise RuntimeError('La URL interna de Railway no funciona desde esta PC. Usá DATABASE_PUBLIC_URL del servicio PostgreSQL como DATABASE_URL local.')
    return normalize_database_url(database_url)


def get_engine_options(database_url: str) -> dict:
    options = {'pool_pre_ping': True}
    if database_url.startswith('postgresql'):
        options['connect_args'] = {'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '10'))}
    return options

class Config:
    APP_MODE = os.getenv('APP_MODE', 'produccion' if is_railway_environment() else 'prueba')
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecret')
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwtsecret')
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = get_engine_options(SQLALCHEMY_DATABASE_URI)
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    PDF_PROCESSING_FOLDER = os.getenv('PDF_PROCESSING_FOLDER', 'processed')
    TOKEN_EXPIRATION_MINUTES = int(os.getenv('TOKEN_EXPIRATION_MINUTES', '1440'))
    CORS_ORIGINS = parse_csv_env(os.getenv('CORS_ORIGINS', 'http://localhost:4173,http://127.0.0.1:4173'))
    INIT_DB_ON_STARTUP = os.getenv('INIT_DB_ON_STARTUP', '1').lower() in ['1', 'true', 'yes']
