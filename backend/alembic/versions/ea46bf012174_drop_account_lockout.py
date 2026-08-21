"""Drop the account-lockout columns.

The feature is removed entirely (see app/routers/auth.py): a locked-out district
officer costs more than a throttled password guesser, and the implementation was
broken anyway — `lock_until` is a TIMESTAMP WITHOUT TIME ZONE, so reading it back
gave a naive datetime that `auth.py` compared against an aware one, raising a
TypeError and turning every subsequent login for that account into a 500.

Brute force is now held back solely by the per-IP rate limit on POST /auth/login
(RATE_LIMIT_LOGIN, default 5/minute).

Revision ID: ea46bf012174
Revises: a35af4acdb86
"""
import sqlalchemy as sa
from alembic import op

revision = "ea46bf012174"
down_revision = "a35af4acdb86"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "lock_until")
    op.drop_column("users", "failed_attempts")


def downgrade() -> None:
    # Restores the columns only — the lockout logic itself is gone from auth.py.
    op.add_column("users", sa.Column("failed_attempts", sa.Integer(), nullable=False,
                                     server_default="0"))
    op.add_column("users", sa.Column("lock_until", sa.DateTime(), nullable=True))
    op.alter_column("users", "failed_attempts", server_default=None)
