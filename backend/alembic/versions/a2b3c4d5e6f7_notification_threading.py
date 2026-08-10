"""notifications: add thread_id (private-conversation grouping) and reply_seq (per-code disambiguator).

A reply to a broadcast now always keeps the identical notification_code as whatever it's
replying to, forever (no forking) — the visible "ticket number" never changes across a whole
conversation, no matter how many different recipients reply to the same broadcast. Two new
columns support this: thread_id (self-FK, NOT NULL) groups messages into the private 2-party
conversation they actually belong to (a broadcast has many recipients; the *first* time any one
of them replies, that reply seeds a brand-new private thread — every further message in that
same back-and-forth, from either party, shares that thread_id — but the notification_code stays
identical to the original broadcast's throughout); reply_seq (int, NOT NULL) is a small integer
stamped once per message, drawn from a counter shared by every message under one notification_code
regardless of which private thread it's in, so a sender who gets several different recipients'
private replies to the same broadcast (all showing the same code) can still tell them apart
("reply #2 on SERI-MSG-000100") — chosen over a raw timestamp because it's stable across
retraction (which never deletes rows) and easier to reference verbally.

Backfill processes existing rows in sent_at order and, because the code-sharing rule is new,
also REWRITES notification_code on the 3 existing reply rows to match their parent's code
(previously each reply had generated its own distinct, now-invalid code) — safe because none of
those 3 replies have replies of their own (max chain depth today is 1), confirmed by direct query
before writing this migration. notification_code's uniqueness constraint is dropped since many
rows now deliberately share one code by design.

Revision ID: a2b3c4d5e6f7
Revises: d6e7f8a9b0c1
Create Date: 2026-08-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a2b3c4d5e6f7'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("thread_id", sa.String(), nullable=True))
    op.add_column("notifications", sa.Column("reply_seq", sa.Integer(), nullable=True))
    op.drop_constraint("uq_notifications_notification_code", "notifications", type_="unique")

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, notification_code, in_reply_to_id FROM notifications ORDER BY sent_at ASC"
    )).fetchall()

    thread_of: dict[str, str] = {}   # notification id -> resolved thread_id
    code_of: dict[str, str] = {}     # notification id -> resolved (possibly rewritten) code
    seq_counter: dict[str, int] = {}  # notification_code -> next reply_seq to assign

    for row in rows:
        nid, code, parent_id = row.id, row.notification_code, row.in_reply_to_id
        if not parent_id:
            # Root broadcast — its own thread, keeps its own code, starts the code's counter at 0.
            thread_of[nid] = nid
            code_of[nid] = code
            seq_counter.setdefault(code, 0)
            seq = 0
        else:
            parent_active_recipients = bind.execute(sa.text(
                "SELECT COUNT(*) FROM notification_recipients WHERE notification_id = :pid AND is_active"
            ), {"pid": parent_id}).scalar()

            if parent_active_recipients == 1:
                # CONTINUE an existing private thread.
                thread_of[nid] = thread_of.get(parent_id, parent_id)
            else:
                # FORK a brand-new private thread off this broadcast.
                thread_of[nid] = nid

            # The code is ALWAYS inherited from whatever this message is replying to, unconditionally —
            # this is what may rewrite a pre-existing reply's own (now-invalid) distinct code.
            root_code = code_of.get(parent_id, code)
            code_of[nid] = root_code
            seq_counter[root_code] = seq_counter.get(root_code, 0) + 1
            seq = seq_counter[root_code]

        bind.execute(sa.text(
            "UPDATE notifications SET thread_id = :tid, notification_code = :code, reply_seq = :seq WHERE id = :nid"
        ), {"tid": thread_of[nid], "code": code_of[nid], "seq": seq, "nid": nid})

    op.alter_column("notifications", "thread_id", nullable=False)
    op.alter_column("notifications", "reply_seq", nullable=False)
    op.create_foreign_key("fk_notifications_thread_id", "notifications", "notifications",
                          ["thread_id"], ["id"])
    op.create_index("ix_notifications_thread_id", "notifications", ["thread_id"])


def downgrade() -> None:
    # NOTE: restoring the unique constraint will fail if, by the time of downgrade, any two rows
    # actually share a notification_code (expected once real conversations have replies) — this
    # migration is not meant to be cleanly reversible after the feature has seen real usage.
    op.drop_index("ix_notifications_thread_id", table_name="notifications")
    op.drop_constraint("fk_notifications_thread_id", "notifications", type_="foreignkey")
    op.drop_column("notifications", "reply_seq")
    op.drop_column("notifications", "thread_id")
    op.create_unique_constraint("uq_notifications_notification_code", "notifications", ["notification_code"])
