"""Caliber stacking families and aliases. Prepared with authorization; do not auto-apply."""
from alembic import op
import sqlalchemy as sa

revision = '20261103_02'
down_revision = '20261103_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('pallet_caliber_families',
        sa.Column('key', sa.String(80), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False, unique=True),
        sa.Column('must_be_bottom', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('base_priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('allowed_above', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('cases_per_layer', sa.Integer(), nullable=True),
        sa.Column('max_layers', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('base_priority >= 0', name='ck_pallet_family_priority'),
        sa.CheckConstraint('cases_per_layer IS NULL OR cases_per_layer > 0', name='ck_pallet_family_cases_layer'),
        sa.CheckConstraint('max_layers IS NULL OR max_layers > 0', name='ck_pallet_family_max_layers'))
    op.create_table('pallet_caliber_aliases',
        sa.Column('caliber', sa.String(120), primary_key=True),
        sa.Column('family_key', sa.String(80), sa.ForeignKey('pallet_caliber_families.key'), nullable=False),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    family = sa.table('pallet_caliber_families', sa.column('key', sa.String), sa.column('name', sa.String),
        sa.column('must_be_bottom', sa.Boolean), sa.column('base_priority', sa.Integer),
        sa.column('allowed_above', sa.JSON), sa.column('enabled', sa.Boolean))
    alias = sa.table('pallet_caliber_aliases', sa.column('caliber', sa.String), sa.column('family_key', sa.String))
    op.bulk_insert(family, [dict(key='litro_vidrio', name='Litro retornable de vidrio', must_be_bottom=True,
        base_priority=100, allowed_above=['*'], enabled=True)])
    op.bulk_insert(alias, [dict(caliber='1000 CC VIDRIO', family_key='litro_vidrio')])


def downgrade():
    op.drop_table('pallet_caliber_aliases')
    op.drop_table('pallet_caliber_families')
