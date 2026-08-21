"""Designation master, and a designation on officer accounts.

Seeds the standard Directorate hierarchy so an admin can be created immediately rather than
someone first having to populate an empty master. The list is ordinary master data: the
State Admin can rename, reorder, deactivate or add to it.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
"""
from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None

# Seniority order, which is what display_order preserves -- alphabetical would put
# "Assistant Director" above "Director".
SEED = [
    "Director of Sericulture",
    "Additional Director of Sericulture",
    "Joint Director of Sericulture",
    "Deputy Director of Sericulture",
    "Assistant Director of Sericulture (ADS)",
    "Superintendent of Sericulture",
    "Sericulture Extension Officer",
    "Inspector of Sericulture",
    "Sericulture Demonstrator",
]


def upgrade() -> None:
    op.create_table(
        "designations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("designation_name", sa.String(length=120), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("designation_name"),
    )

    conn = op.get_bind()
    for i, name in enumerate(SEED, start=1):
        conn.execute(
            sa.text(
                "INSERT INTO designations (id, designation_name, display_order, is_active) "
                "VALUES (gen_random_uuid()::text, :n, :o, true) "
                "ON CONFLICT (designation_name) DO NOTHING"
            ),
            {"n": name, "o": i * 10},
        )

    op.add_column("users", sa.Column("designation_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_users_designation_id", "users", "designations", ["designation_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_users_designation_id", "users", type_="foreignkey")
    op.drop_column("users", "designation_id")
    op.drop_table("designations")
