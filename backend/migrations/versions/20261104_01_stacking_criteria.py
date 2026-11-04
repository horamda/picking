"""Physical stacking criteria by business unit and caliber. Prepared; do not auto-apply."""
from alembic import op
import sqlalchemy as sa

revision = '20261104_01'
down_revision = '20261103_02'
branch_labels = None
depends_on = None


RULES = [
    ('ADYACENCIAS', '500 CC VD S/R', False, True),
    ('ADYACENCIAS', '720 CC VIDRIO', False, True),
    ('ADYACENCIAS', '750 CC VIDRIO', False, True),
    ('AGUAS ECO', '1000 CC PET', False, False),
    ('AGUAS ECO', '1500 CC PET', False, False),
    ('AGUAS ECO', '2000 CC PET', False, False),
    ('AGUAS ECO', '2250 CC PET', False, False),
    ('AGUAS ECO', '500 CC PET', False, False),
    ('AGUAS ECO', '6.4L CC PET', False, False),
    ('AGUAS ECO', '750 CC PET', False, False),
    ('AGUAS ECO', '850 CC PET', False, False),
    ('CERVEZAS CMQ', '1000 CC VIDRIO', True, True),
    ('CERVEZAS CMQ', '269 CC LATA', True, True),
    ('CERVEZAS CMQ', '330 CC S/R', True, True),
    ('CERVEZAS CMQ', '330 CC VIDRIO', True, True),
    ('CERVEZAS CMQ', '473 CC', True, True),
    ('CERVEZAS CMQ', '473 CC LATAS', True, True),
    ('CERVEZAS CMQ', '710 CC LATAS', True, True),
    ('CERVEZAS CMQ', '710 SIN RETORNO', True, True),
    ('CERVEZAS CMQ', '730 CC', True, True),
    ('CERVEZAS CMQ', '975 CC VIDRIO', True, True),
    ('CERVEZAS CMQ', 'BARRIL 20L', False, False),
    ('CERVEZAS CMQ', 'BARRIL 50 LTS', False, False),
    ('CERVEZAS CMQ', 'BOT VD 275 CC', True, True),
    ('CERVEZAS CMQ', 'BOTELLA 710 CC', True, True),
    ('UNG', '1250 CC PET', False, False),
    ('UNG', '1500 CC PET', True, True),
    ('UNG', '2.25L', True, True),
    ('UNG', '2000 CC PET', True, True),
    ('UNG', '2250 CC PET', True, True),
    ('UNG', '250 CC LATAS', True, True),
    ('UNG', '269 CC LATA', True, True),
    ('UNG', '3000 CC PET', True, True),
    ('UNG', '354 CC', True, True),
    ('UNG', '354 CC LATA', True, True),
    ('UNG', '355 CC LATA', True, True),
    ('UNG', '400CC PET', True, True),
    ('UNG', '473 CC', True, True),
    ('UNG', '500 CC PET', False, False),
    ('UNG', '500 CC VD S/R', False, False),
    ('UNG', '750 CC PET', False, False),
    ('UNG', 'TETRA 200CC', False, False),
    ('VINO', '750 CC VIDRIO', False, False),
]


def size_rank(caliber):
    import re
    text = caliber.upper().replace(',', '.')
    liters = re.search(r'(\d+(?:\.\d+)?)\s*L(?:\b|TS)', text)
    if liters:
        return int(float(liters.group(1)) * 1000)
    cc = re.search(r'(\d+(?:\.\d+)?)\s*CC', text)
    return int(float(cc.group(1))) if cc else 0


def upgrade():
    op.add_column('articulos', sa.Column('bultos_por_piso', sa.Integer(), nullable=True))
    op.add_column('articulos', sa.Column('pisos_por_pallet', sa.Integer(), nullable=True))
    op.add_column('articulos', sa.Column('apilabilidad', sa.Numeric(10, 3), nullable=True))
    op.add_column('articulos', sa.Column('hl_por_bulto', sa.Numeric(12, 6), nullable=True))
    op.add_column('articulos', sa.Column('codigo_barras_bulto', sa.String(120), nullable=True))
    op.add_column('articulos', sa.Column('codigo_barras_unidad', sa.String(120), nullable=True))
    op.add_column('articulos', sa.Column('datos_logisticos', sa.JSON(), nullable=True))
    op.create_check_constraint('ck_articulos_bultos_piso', 'articulos',
                               'bultos_por_piso IS NULL OR bultos_por_piso > 0')
    op.create_table('pallet_stacking_rules',
        sa.Column('business_unit', sa.String(120), primary_key=True),
        sa.Column('caliber', sa.String(120), primary_key=True),
        sa.Column('can_be_base', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('stable', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('allow_incomplete_floor', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('size_rank', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('size_rank >= 0', name='ck_pallet_stacking_size_rank'))
    table = sa.table('pallet_stacking_rules',
        sa.column('business_unit', sa.String), sa.column('caliber', sa.String),
        sa.column('can_be_base', sa.Boolean), sa.column('stable', sa.Boolean),
        sa.column('allow_incomplete_floor', sa.Boolean), sa.column('size_rank', sa.Integer),
        sa.column('enabled', sa.Boolean))
    op.bulk_insert(table, [dict(business_unit=u, caliber=c, can_be_base=b, stable=s,
        allow_incomplete_floor=False, size_rank=size_rank(c), enabled=True) for u, c, b, s in RULES])


def downgrade():
    op.drop_table('pallet_stacking_rules')
    op.drop_constraint('ck_articulos_bultos_piso', 'articulos', type_='check')
    for column in ('datos_logisticos', 'codigo_barras_unidad', 'codigo_barras_bulto', 'hl_por_bulto',
                   'apilabilidad', 'pisos_por_pallet'):
        op.drop_column('articulos', column)
    op.drop_column('articulos', 'bultos_por_piso')
