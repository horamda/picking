import os
from dotenv import load_dotenv

load_dotenv()

def normalize_database_url(database_url: str) -> str:
    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    if database_url.startswith('postgresql://'):
        return database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return database_url

def parse_csv_env(value: str) -> list[str]:
    return [item.strip() for item in value.split(',') if item.strip()]

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecret')
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwtsecret')
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv('DATABASE_URL', 'sqlite:///picking.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    PDF_PROCESSING_FOLDER = os.getenv('PDF_PROCESSING_FOLDER', 'processed')
    TOKEN_EXPIRATION_MINUTES = int(os.getenv('TOKEN_EXPIRATION_MINUTES', '1440'))
    CORS_ORIGINS = parse_csv_env(os.getenv('CORS_ORIGINS', 'http://localhost:4173,http://127.0.0.1:4173'))
    INIT_DB_ON_STARTUP = os.getenv('INIT_DB_ON_STARTUP', '1').lower() in ['1', 'true', 'yes']
