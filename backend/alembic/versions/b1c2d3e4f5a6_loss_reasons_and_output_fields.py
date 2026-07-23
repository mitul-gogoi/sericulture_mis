"""loss reasons master + per-row output fields

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-07-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'b1c2d3e4f5a6'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loss_reasons",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("reason_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reason_name"),
    )

    op.add_column("yields", sa.Column("loss_reason_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_yields_loss_reason_id", "yields", "loss_reasons", ["loss_reason_id"], ["id"])
    op.create_index("ix_yields_loss_reason_id", "yields", ["loss_reason_id"])
    op.drop_column("yields", "crop_loss_reason")

    op.add_column("byproduct_entries", sa.Column("planned_quantity", sa.Float(), nullable=False, server_default="0"))
    op.add_column("byproduct_entries", sa.Column("next_month_plan", sa.Float(), nullable=False, server_default="0"))
    op.add_column("byproduct_entries", sa.Column("stock_balance", sa.Float(), nullable=False, server_default="0"))
    op.alter_column("byproduct_entries", "planned_quantity", server_default=None)
    op.alter_column("byproduct_entries", "next_month_plan", server_default=None)
    op.alter_column("byproduct_entries", "stock_balance", server_default=None)
    op.add_column("byproduct_entries", sa.Column("loss_reason_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_byproduct_entries_loss_reason_id", "byproduct_entries", "loss_reasons", ["loss_reason_id"], ["id"])
    op.create_index("ix_byproduct_entries_loss_reason_id", "byproduct_entries", ["loss_reason_id"])


def downgrade() -> None:
    op.drop_index("ix_byproduct_entries_loss_reason_id", table_name="byproduct_entries")
    op.drop_constraint("fk_byproduct_entries_loss_reason_id", "byproduct_entries", type_="foreignkey")
    op.drop_column("byproduct_entries", "loss_reason_id")
    op.drop_column("byproduct_entries", "stock_balance")
    op.drop_column("byproduct_entries", "next_month_plan")
    op.drop_column("byproduct_entries", "planned_quantity")

    op.add_column("yields", sa.Column("crop_loss_reason", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
    op.drop_index("ix_yields_loss_reason_id", table_name="yields")
    op.drop_constraint("fk_yields_loss_reason_id", "yields", type_="foreignkey")
    op.drop_column("yields", "loss_reason_id")

    op.drop_table("loss_reasons")
