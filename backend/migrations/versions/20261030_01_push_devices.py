"""Device registration and durable notification checkpoints. Apply explicitly."""
from alembic import op
import sqlalchemy as sa

revision = '20261030_01'
down_revision = '20261027_02'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('push_devices',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('known_tasks', sa.JSON(), nullable=False),
        sa.Column('next_attempt', sa.DateTime(timezone=True), nullable=False),
        sa.Column('failures', sa.Integer(), nullable=False))
    op.create_index('ix_push_devices_user_id', 'push_devices', ['user_id'])


def downgrade():
    raise RuntimeError('La reversa elimina asociaciones y comprobantes. Requiere revisión explícita.')
