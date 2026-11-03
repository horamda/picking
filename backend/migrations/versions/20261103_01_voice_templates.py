"""Editable voice templates. Prepared with authorization; do not apply automatically."""
from alembic import op
import sqlalchemy as sa

revision = '20261103_01'
down_revision = '20261102_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('voice_templates',
        sa.Column('key', sa.String(80), primary_key=True),
        sa.Column('text', sa.String(1000), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))


def downgrade():
    op.drop_table('voice_templates')
