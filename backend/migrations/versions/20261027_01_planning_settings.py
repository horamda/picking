"""Prepare depot planning defaults and physical truck capacities; do not auto-apply."""
from alembic import op
import sqlalchemy as sa

revision = '20261027_01'
down_revision = '20261024_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'depot_planning_settings',
        sa.Column('branch', sa.String(255), primary_key=True),
        sa.Column('mix_courts_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("length(trim(branch)) > 0", name='ck_planning_branch_not_blank'),
    )
    op.create_table(
        'truck_pallet_capacities',
        sa.Column('branch', sa.String(255), nullable=False),
        sa.Column('truck', sa.String(255), nullable=False),
        sa.Column('pallet_capacity', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('branch', 'truck'),
        sa.ForeignKeyConstraint(['branch'], ['depot_planning_settings.branch']),
        sa.CheckConstraint('pallet_capacity > 0', name='ck_truck_pallet_capacity_positive'),
        sa.CheckConstraint("length(trim(truck)) > 0", name='ck_planning_truck_not_blank'),
    )


def downgrade():
    raise RuntimeError('La reversa requiere respaldo de capacidades y configuraciones y un plan aprobado.')
