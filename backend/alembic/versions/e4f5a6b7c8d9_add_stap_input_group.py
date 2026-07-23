"""add input_group to silk_type_activity_products

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-19 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'e4f5a6b7c8d9'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "silk_type_activity_products",
        sa.Column("input_group", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("silk_type_activity_products", "input_group")
