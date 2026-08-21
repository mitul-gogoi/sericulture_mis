"""Let a District Admin hold additional charge of more than one district.

Adds the user_districts join table and backfills one row per existing District Admin from
their current users.district_id, so behaviour is unchanged until someone is actually given
a second district.

users.district_id is deliberately KEPT as the primary district: it is the default selection
in the switcher, the fallback when no district is chosen, and what every not-yet-converted
call site still reads. That last point is the safety property -- an unconverted site keeps
scoping to the primary district (today's behaviour) rather than leaking another district.

Revision ID: c1d2e3f4a5b6
Revises: ac1b4bb6cbef
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "ac1b4bb6cbef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_districts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("district_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "district_id", name="uq_user_district"),
    )
    op.create_index("ix_user_districts_user_id", "user_districts", ["user_id"])
    op.create_index("ix_user_districts_district_id", "user_districts", ["district_id"])

    # Backfill: every District Admin who already has a district gets it as their first
    # assignment. gen_random_uuid() is built into PostgreSQL 13+, so no extension needed.
    op.execute(
        """
        INSERT INTO user_districts (id, user_id, district_id, created_at)
        SELECT gen_random_uuid()::text, id, district_id, now()
        FROM users
        WHERE role = 'DISTRICT_ADMIN' AND district_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_districts_district_id", table_name="user_districts")
    op.drop_index("ix_user_districts_user_id", table_name="user_districts")
    op.drop_table("user_districts")
