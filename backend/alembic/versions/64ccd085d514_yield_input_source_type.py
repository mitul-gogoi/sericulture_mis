"""yield input source type

Revision ID: 64ccd085d514
Revises: ec8e7733a0d8
Create Date: 2026-07-17 08:54:05.943442

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = '64ccd085d514'
down_revision = 'ec8e7733a0d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("yield_input_entries", sa.Column(
        "source_type", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False, server_default="Own Source"))
    op.alter_column("yield_input_entries", "source_type", server_default=None)
    op.add_column("yield_input_entries", sa.Column("scheme_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_yield_input_entries_scheme_id", "yield_input_entries", "schemes", ["scheme_id"], ["id"])
    op.create_index("ix_yield_input_entries_scheme_id", "yield_input_entries", ["scheme_id"])


def downgrade() -> None:
    op.drop_index("ix_yield_input_entries_scheme_id", table_name="yield_input_entries")
    op.drop_constraint("fk_yield_input_entries_scheme_id", "yield_input_entries", type_="foreignkey")
    op.drop_column("yield_input_entries", "scheme_id")
    op.drop_column("yield_input_entries", "source_type")
