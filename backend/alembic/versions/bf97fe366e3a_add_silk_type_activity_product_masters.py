"""add silk type activity product masters

Revision ID: bf97fe366e3a
Revises: 30a6b671695c
Create Date: 2026-07-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'bf97fe366e3a'
down_revision = '30a6b671695c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'silk_types',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('silk_type_name', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('silk_type_name'),
    )

    op.create_table(
        'activities',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('activity_name', sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('activity_name'),
    )

    op.create_table(
        'products',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('product_name', sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column('unit_of_measure', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column('is_perishable', sa.Boolean(), nullable=False),
        sa.Column('is_byproduct', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_name'),
    )

    op.create_table(
        'silk_type_activity_products',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('silk_type_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('activity_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('product_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('legacy_stage_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['silk_type_id'], ['silk_types.id']),
        sa.ForeignKeyConstraint(['activity_id'], ['activities.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['legacy_stage_id'], ['stages.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('silk_type_id', 'activity_id', 'product_id'),
    )
    op.create_index(op.f('ix_silk_type_activity_products_silk_type_id'), 'silk_type_activity_products', ['silk_type_id'], unique=False)
    op.create_index(op.f('ix_silk_type_activity_products_activity_id'), 'silk_type_activity_products', ['activity_id'], unique=False)
    op.create_index(op.f('ix_silk_type_activity_products_product_id'), 'silk_type_activity_products', ['product_id'], unique=False)
    op.create_index(op.f('ix_silk_type_activity_products_legacy_stage_id'), 'silk_type_activity_products', ['legacy_stage_id'], unique=False)

    op.add_column('yields', sa.Column('activity_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('yields', sa.Column('product_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key('fk_yields_activity_id', 'yields', 'activities', ['activity_id'], ['id'])
    op.create_foreign_key('fk_yields_product_id', 'yields', 'products', ['product_id'], ['id'])
    op.create_index(op.f('ix_yields_activity_id'), 'yields', ['activity_id'], unique=False)
    op.create_index(op.f('ix_yields_product_id'), 'yields', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_yields_product_id'), table_name='yields')
    op.drop_index(op.f('ix_yields_activity_id'), table_name='yields')
    op.drop_constraint('fk_yields_product_id', 'yields', type_='foreignkey')
    op.drop_constraint('fk_yields_activity_id', 'yields', type_='foreignkey')
    op.drop_column('yields', 'product_id')
    op.drop_column('yields', 'activity_id')

    op.drop_index(op.f('ix_silk_type_activity_products_legacy_stage_id'), table_name='silk_type_activity_products')
    op.drop_index(op.f('ix_silk_type_activity_products_product_id'), table_name='silk_type_activity_products')
    op.drop_index(op.f('ix_silk_type_activity_products_activity_id'), table_name='silk_type_activity_products')
    op.drop_index(op.f('ix_silk_type_activity_products_silk_type_id'), table_name='silk_type_activity_products')
    op.drop_table('silk_type_activity_products')
    op.drop_table('products')
    op.drop_table('activities')
    op.drop_table('silk_types')
