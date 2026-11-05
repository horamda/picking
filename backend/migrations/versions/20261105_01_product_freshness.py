"""Exact product freshness from load-plan PDFs."""
from alembic import op
import sqlalchemy as sa

revision = '20261105_01'
down_revision = '20261104_01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('consolidado_detalle', sa.Column('fecha_frescura', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('consolidado_detalle', 'fecha_frescura')
