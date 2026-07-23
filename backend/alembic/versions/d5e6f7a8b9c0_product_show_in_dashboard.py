"""Add Product.show_in_dashboard flag — lets State Admin hide a product from
dashboard/summary tiles without deactivating it (is_active still governs
whether it can be used in STAP mappings, farmer forms, submission forms, etc).

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("show_in_dashboard", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("products", "show_in_dashboard")
