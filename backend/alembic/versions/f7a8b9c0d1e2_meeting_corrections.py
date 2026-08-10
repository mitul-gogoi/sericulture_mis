"""New meeting_corrections table: FIG President can propose an edit to an already-submitted
month, held pending until a District/State Admin accepts it (live Meeting/Yield_/ByproductEntry/
YieldInputEntry/Stock rows are only touched on acceptance — see routers/meetings.py).

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meeting_corrections",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), primary_key=True),
        sa.Column("meeting_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fig_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("submitted_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"]),
        sa.ForeignKeyConstraint(["fig_id"], ["figs.id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_meeting_corrections_meeting_id", "meeting_corrections", ["meeting_id"])
    op.create_index("ix_meeting_corrections_fig_id", "meeting_corrections", ["fig_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_corrections_fig_id", table_name="meeting_corrections")
    op.drop_index("ix_meeting_corrections_meeting_id", table_name="meeting_corrections")
    op.drop_table("meeting_corrections")
