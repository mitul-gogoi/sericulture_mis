"""add meeting minutes_path

Revision ID: a9b8c7d6e5f4
Revises: 64ccd085d514
Create Date: 2026-07-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'a9b8c7d6e5f4'
down_revision = '64ccd085d514'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column(
        "minutes_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("meetings", "minutes_path")
