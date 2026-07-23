"""product silk type

Revision ID: ec8e7733a0d8
Revises: f8cf77a75e0e
Create Date: 2026-07-17 07:59:00.474704

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'ec8e7733a0d8'
down_revision = 'f8cf77a75e0e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("silk_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_products_silk_type_id", "products", "silk_types", ["silk_type_id"], ["id"])
    op.create_index("ix_products_silk_type_id", "products", ["silk_type_id"])


def downgrade() -> None:
    op.drop_index("ix_products_silk_type_id", table_name="products")
    op.drop_constraint("fk_products_silk_type_id", "products", type_="foreignkey")
    op.drop_column("products", "silk_type_id")
