"""Explicit migration connection; importing the Flask app is intentionally avoided."""
import os

from alembic import context
from sqlalchemy import create_engine, pool


def run():
    url = os.environ.get('MIGRATION_DATABASE_URL')
    if not url:
        raise RuntimeError('MIGRATION_DATABASE_URL es obligatoria; no se utiliza .env automaticamente.')
    if context.is_offline_mode():
        raise RuntimeError('La revision inicial requiere verificar el esquema con una conexion.')
    url = url.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run()
