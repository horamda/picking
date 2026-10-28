"""Preserve source CSV fields and a separately maintained voice description."""
from alembic import op
import sqlalchemy as sa

revision = '20261027_02'
down_revision = '20261027_01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('articulos', sa.Column('descripcion_voz', sa.String(255), nullable=True))
    op.add_column('articulos', sa.Column('datos_origen', sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError('Respaldar las descripciones de voz y datos originales antes de una reversa revisada.')
