"""Weekly staffing drafts and published plans. Requires explicit authorization."""
from alembic import op
import sqlalchemy as sa
revision = '20261030_02'
down_revision = '20261030_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('staffing_weeks',
        sa.Column('week_start', sa.Date(), primary_key=True),
        sa.Column('draft', sa.JSON(), nullable=False),
        sa.Column('published', sa.JSON(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False))


def downgrade():
    raise RuntimeError('El historial de planificación requiere una reversa revisada y respaldada.')
