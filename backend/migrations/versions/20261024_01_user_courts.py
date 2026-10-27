"""Prepare fixed court assignments per user. Requires explicit deployment approval.

No assignments are inferred from historical picking activity.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261024_01'
down_revision = '20261015_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_court_assignments',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('court_number', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'court_number'),
        sa.CheckConstraint('court_number > 0', name='ck_user_court_positive'),
    )


def downgrade():
    # Dropping this table would discard the assignments used for access control.
    raise RuntimeError('La reversa requiere un respaldo de asignaciones y un plan aprobado.')
