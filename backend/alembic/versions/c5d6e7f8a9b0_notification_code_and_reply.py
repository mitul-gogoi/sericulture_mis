"""notifications: add notification_code (human-facing Message ID) and in_reply_to_id.

Adds notification_code (SERI-MSG-NNNNNN, matching the existing SERI-FRM/SERI-FIG/SERI-CERT
convention) and in_reply_to_id (self-FK, nullable) to the notifications table, so the
Notifications module can surface a Message ID in its new detail view and support a lightweight
one-level reply. Existing rows are backfilled with sequential codes assigned in sent_at order;
in_reply_to_id needs no backfill since replies didn't exist before this migration.

Revision ID: c5d6e7f8a9b0
Revises: b2c4d6e8f0a1
Create Date: 2026-08-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c5d6e7f8a9b0'
down_revision = 'b2c4d6e8f0a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("notification_code", sa.String(length=30), nullable=True))
    op.add_column("notifications", sa.Column("in_reply_to_id", sa.String(), nullable=True))

    op.execute(
        "UPDATE notifications n SET notification_code = 'SERI-MSG-' || LPAD(sub.rn::text, 6, '0') "
        "FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY sent_at) AS rn FROM notifications) sub "
        "WHERE n.id = sub.id"
    )

    op.alter_column("notifications", "notification_code", nullable=False)
    op.create_unique_constraint("uq_notifications_notification_code", "notifications", ["notification_code"])
    op.create_index("ix_notifications_notification_code", "notifications", ["notification_code"])
    op.create_foreign_key(
        "fk_notifications_in_reply_to_id", "notifications", "notifications",
        ["in_reply_to_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_notifications_in_reply_to_id", "notifications", type_="foreignkey")
    op.drop_index("ix_notifications_notification_code", table_name="notifications")
    op.drop_constraint("uq_notifications_notification_code", "notifications", type_="unique")
    op.drop_column("notifications", "in_reply_to_id")
    op.drop_column("notifications", "notification_code")
