"""Configurable pallet height and weight limits. Prepared; do not auto-apply."""
from alembic import op
import sqlalchemy as sa

revision = '20261111_01'
down_revision = '20261105_01'
branch_labels = None
depends_on = None


def upgrade():
    for name, precision, scale in (
        ('pallet_base_height_cm', 10, 2), ('reference_pallet_height_cm', 10, 2),
        ('max_pallet_height_cm', 10, 2), ('empty_pallet_weight_kg', 12, 3),
        ('max_pallet_weight_kg', 12, 3), ('safety_margin_pct', 5, 2)):
        op.add_column('depot_planning_settings', sa.Column(name, sa.Numeric(precision, scale), nullable=True))
    op.add_column('depot_planning_settings', sa.Column('height_excess_mode', sa.String(20), nullable=False, server_default='inform'))
    op.add_column('depot_planning_settings', sa.Column('pallet_weight_excess_mode', sa.String(20), nullable=False, server_default='inform'))
    op.add_column('depot_planning_settings', sa.Column('truck_weight_excess_mode', sa.String(20), nullable=False, server_default='inform'))
    op.add_column('depot_planning_settings', sa.Column('share_floor_remainders', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('depot_planning_settings', sa.Column('weight_tiebreaker', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('truck_pallet_capacities', sa.Column('max_payload_kg', sa.Numeric(12, 3), nullable=True))
    op.add_column('truck_pallet_capacities', sa.Column('max_height_cm', sa.Numeric(10, 2), nullable=True))
    op.create_check_constraint('ck_depot_pallet_base_height_positive', 'depot_planning_settings', 'pallet_base_height_cm IS NULL OR pallet_base_height_cm > 0')
    op.create_check_constraint('ck_depot_reference_height_positive', 'depot_planning_settings', 'reference_pallet_height_cm IS NULL OR reference_pallet_height_cm > 0')
    op.create_check_constraint('ck_depot_max_height_positive', 'depot_planning_settings', 'max_pallet_height_cm IS NULL OR max_pallet_height_cm > 0')
    op.create_check_constraint('ck_depot_empty_pallet_weight_positive', 'depot_planning_settings', 'empty_pallet_weight_kg IS NULL OR empty_pallet_weight_kg > 0')
    op.create_check_constraint('ck_depot_max_pallet_weight_positive', 'depot_planning_settings', 'max_pallet_weight_kg IS NULL OR max_pallet_weight_kg > 0')
    op.create_check_constraint('ck_depot_margin_range', 'depot_planning_settings', 'safety_margin_pct IS NULL OR (safety_margin_pct >= 0 AND safety_margin_pct <= 50)')
    op.create_check_constraint('ck_depot_reference_above_base', 'depot_planning_settings', 'pallet_base_height_cm IS NULL OR reference_pallet_height_cm IS NULL OR reference_pallet_height_cm > pallet_base_height_cm')
    op.create_check_constraint('ck_depot_max_above_base', 'depot_planning_settings', 'pallet_base_height_cm IS NULL OR max_pallet_height_cm IS NULL OR max_pallet_height_cm > pallet_base_height_cm')
    for field in ('height_excess_mode', 'pallet_weight_excess_mode', 'truck_weight_excess_mode'):
        op.create_check_constraint(f'ck_depot_{field}', 'depot_planning_settings', f"{field} IN ('inform', 'block')")
    op.create_check_constraint('ck_truck_payload_positive', 'truck_pallet_capacities', 'max_payload_kg IS NULL OR max_payload_kg > 0')
    op.create_check_constraint('ck_truck_height_positive', 'truck_pallet_capacities', 'max_height_cm IS NULL OR max_height_cm > 0')


def downgrade():
    raise RuntimeError('La reversa requiere respaldar límites físicos y planes aprobados.')
