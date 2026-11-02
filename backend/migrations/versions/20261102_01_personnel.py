"""Personnel identity and revocable sessions; apply only with authorization."""
from alembic import op
import sqlalchemy as sa
revision = '20261102_01'
down_revision = '20261030_02'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('first_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('employee_number', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('session_version', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('uq_users_employee_number', 'users', ['employee_number'], unique=True)


def downgrade():
    raise RuntimeError('La ficha de personal requiere una reversa revisada y respaldada.')
