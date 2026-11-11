"""Package dimensions on mixer rules. Prepared; do not auto-apply."""
from alembic import op
import sqlalchemy as sa

revision = '20261111_02'
down_revision = '20261111_01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pallet_stacking_rules', sa.Column('units_per_case', sa.Integer(), nullable=True))
    for name in ('length_cm', 'width_cm', 'height_cm'):
        op.add_column('pallet_stacking_rules', sa.Column(name, sa.Numeric(10, 2), nullable=True))
    op.create_check_constraint('ck_stacking_units_per_case_positive', 'pallet_stacking_rules',
                               'units_per_case IS NULL OR units_per_case > 0')
    for name in ('length_cm', 'width_cm', 'height_cm'):
        op.create_check_constraint(f'ck_stacking_{name}_positive', 'pallet_stacking_rules',
                                   f'{name} IS NULL OR {name} > 0')


def downgrade():
    raise RuntimeError('La reversa requiere respaldar las dimensiones cargadas en las reglas del mezclador.')
