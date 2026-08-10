"""New conversion_standards table: State-Admin-configured expected input->output conversion
ranges (Silk Type + Input Product + Output Product -> Min%/Max%), independent of any specific
Activity/STAP mapping. Used by the redesigned Yield View to show an "Expected" range next to
each row's Actual output (see services/yield_matrix.py).

Revision ID: 5aac3495e5ca
Revises: f7a8b9c0d1e2
Create Date: 2026-08-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = '5aac3495e5ca'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversion_standards",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), primary_key=True),
        sa.Column("silk_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("input_product_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("output_product_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("min_pct", sa.Float(), nullable=False),
        sa.Column("max_pct", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["silk_type_id"], ["silk_types.id"]),
        sa.ForeignKeyConstraint(["input_product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["output_product_id"], ["products.id"]),
        sa.UniqueConstraint("silk_type_id", "input_product_id", "output_product_id"),
    )
    op.create_index("ix_conversion_standards_silk_type_id", "conversion_standards", ["silk_type_id"])
    op.create_index("ix_conversion_standards_input_product_id", "conversion_standards", ["input_product_id"])
    op.create_index("ix_conversion_standards_output_product_id", "conversion_standards", ["output_product_id"])


def downgrade() -> None:
    op.drop_index("ix_conversion_standards_output_product_id", table_name="conversion_standards")
    op.drop_index("ix_conversion_standards_input_product_id", table_name="conversion_standards")
    op.drop_index("ix_conversion_standards_silk_type_id", table_name="conversion_standards")
    op.drop_table("conversion_standards")
