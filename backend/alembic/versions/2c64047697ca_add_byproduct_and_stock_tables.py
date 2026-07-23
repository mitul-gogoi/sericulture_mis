"""add byproduct and stock tables

Revision ID: 2c64047697ca
Revises: bf97fe366e3a
Create Date: 2026-07-10 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = '2c64047697ca'
down_revision = 'bf97fe366e3a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'byproduct_entries',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('parent_yield_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('farmer_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fig_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('product_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('yield_month', sqlmodel.sql.sqltypes.AutoString(length=7), nullable=False),
        sa.Column('unit_of_measure', sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('sold_quantity', sa.Float(), nullable=False),
        sa.Column('sold_rate', sa.Float(), nullable=False),
        sa.Column('earning', sa.Float(), nullable=False),
        sa.Column('remarks', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('submission_status', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_yield_id'], ['yields.id']),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id']),
        sa.ForeignKeyConstraint(['fig_id'], ['figs.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('parent_yield_id', 'product_id'),
    )
    op.create_index(op.f('ix_byproduct_entries_parent_yield_id'), 'byproduct_entries', ['parent_yield_id'], unique=False)
    op.create_index(op.f('ix_byproduct_entries_farmer_id'), 'byproduct_entries', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_byproduct_entries_fig_id'), 'byproduct_entries', ['fig_id'], unique=False)
    op.create_index(op.f('ix_byproduct_entries_product_id'), 'byproduct_entries', ['product_id'], unique=False)
    op.create_index(op.f('ix_byproduct_entries_yield_month'), 'byproduct_entries', ['yield_month'], unique=False)
    op.create_index('ix_byproduct_farmer_month', 'byproduct_entries', ['farmer_id', 'yield_month'], unique=False)

    op.create_table(
        'stock',
        sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('farmer_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fig_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('product_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('opening_balance', sa.Float(), nullable=False),
        sa.Column('closing_balance', sa.Float(), nullable=False),
        sa.Column('is_perishable', sa.Boolean(), nullable=False),
        sa.Column('last_produced_month', sqlmodel.sql.sqltypes.AutoString(length=7), nullable=True),
        sa.Column('last_entry_at', sa.DateTime(), nullable=False),
        sa.Column('last_source_yield_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('last_source_byproduct_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id']),
        sa.ForeignKeyConstraint(['fig_id'], ['figs.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['last_source_yield_id'], ['yields.id']),
        sa.ForeignKeyConstraint(['last_source_byproduct_id'], ['byproduct_entries.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('farmer_id', 'product_id'),
    )
    op.create_index(op.f('ix_stock_farmer_id'), 'stock', ['farmer_id'], unique=False)
    op.create_index(op.f('ix_stock_fig_id'), 'stock', ['fig_id'], unique=False)
    op.create_index(op.f('ix_stock_product_id'), 'stock', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_stock_product_id'), table_name='stock')
    op.drop_index(op.f('ix_stock_fig_id'), table_name='stock')
    op.drop_index(op.f('ix_stock_farmer_id'), table_name='stock')
    op.drop_table('stock')

    op.drop_index('ix_byproduct_farmer_month', table_name='byproduct_entries')
    op.drop_index(op.f('ix_byproduct_entries_yield_month'), table_name='byproduct_entries')
    op.drop_index(op.f('ix_byproduct_entries_product_id'), table_name='byproduct_entries')
    op.drop_index(op.f('ix_byproduct_entries_fig_id'), table_name='byproduct_entries')
    op.drop_index(op.f('ix_byproduct_entries_farmer_id'), table_name='byproduct_entries')
    op.drop_index(op.f('ix_byproduct_entries_parent_yield_id'), table_name='byproduct_entries')
    op.drop_table('byproduct_entries')
