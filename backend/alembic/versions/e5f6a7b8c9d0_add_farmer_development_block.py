"""add development_block column to farmers

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-15 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("farmers", sa.Column("development_block", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("farmers", "development_block")
