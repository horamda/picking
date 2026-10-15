"""Adopt the existing Railway schema, without recreating application tables.

This baseline intentionally requires an existing database (or a restored backup).
It must not be stamped without executing its structural checks.
"""
import json
from pathlib import Path

from alembic import op
from sqlalchemy import inspect

revision = '20261015_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    expected = json.loads(Path(__file__).with_name('20261015_01_schema.json').read_text(encoding='utf-8'))
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for name, specification in expected.items():
        if name not in tables:
            raise RuntimeError(f'Falta la tabla existente {name}; no se creara automaticamente.')
        columns = {c['name']: {'type': str(c['type']), 'nullable': c['nullable']}
                   for c in inspector.get_columns(name)}
        if columns != specification['columns']:
            raise RuntimeError(f'El esquema de {name} difiere de la revision auditada.')
        if inspector.get_pk_constraint(name)['constrained_columns'] != specification['primary_key']:
            raise RuntimeError(f'La clave primaria de {name} difiere de la revision auditada.')
        actual_fk = sorted((tuple(f['constrained_columns']), f['referred_table'], tuple(f['referred_columns']))
                           for f in inspector.get_foreign_keys(name))
        expected_fk = sorted((tuple(f[0]), f[1], tuple(f[2])) for f in specification['foreign_keys'])
        if actual_fk != expected_fk:
            raise RuntimeError(f'Las relaciones de {name} difieren de la revision auditada.')
        actual_unique = sorted(tuple(u['column_names']) for u in inspector.get_unique_constraints(name))
        if actual_unique != sorted(tuple(u) for u in specification['unique']):
            raise RuntimeError(f'Las restricciones unicas de {name} difieren de la revision auditada.')


def downgrade():
    raise RuntimeError('La revision inicial no elimina tablas ni registros. Requiere un plan de reversa revisado.')
