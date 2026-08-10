"""Farmer self-submission workflow: solo (non-FIG) farmers can submit their own monthly
production/stock data directly (live immediately, resubmission requires District Admin
approval), while FIG-member farmers stage private drafts the FIG President reviews/edits
before finally submitting the FIG's Meeting as today.

To support this, `fig_id` becomes nullable on yields/byproduct_entries/yield_input_entries/
attendance/stock (a solo farmer's rows have no FIG at all), and `district_id`/`seri_circle_id`
are denormalized onto yields/byproduct_entries/yield_input_entries/stock (backfilled from the
owning farmer) so district/circle/state-level reporting no longer depends on joining through
Fig — this is what makes solo-farmer data show up correctly in the existing Yield View/Dashboard
alongside FIG-based farmers. `yields.farmer_submission_id` is a new nullable sibling to the
existing `meeting_id` column, exactly mirroring how a Yield_ row already links to whichever
container (a Meeting) produced it.

Three new tables: farmer_submissions (the solo-farmer analog of Meeting, minus meeting-specific
fields), farmer_submission_corrections (mirrors meeting_corrections, but approved by District
Admin instead of State Admin), and farmer_draft_entries (a FIG-member farmer's private staging
area, consumed once the FIG President submits the real Meeting).

Revision ID: e7f8a9b0c1d2
Revises: a2b3c4d5e6f7
Create Date: 2026-08-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e7f8a9b0c1d2'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


_TABLES_WITH_GEO = ["yields", "byproduct_entries", "yield_input_entries", "stock"]


def upgrade() -> None:
    # 1. fig_id becomes nullable everywhere a solo farmer's rows might land.
    for table in ["yields", "byproduct_entries", "yield_input_entries", "attendance", "stock"]:
        op.alter_column(table, "fig_id", existing_type=sa.String(), nullable=True)

    # 2. Denormalize district_id/seri_circle_id (nullable first, backfilled from the owning
    # farmer, then constrained NOT NULL) onto every transactional table that needs geographic
    # scoping independent of Fig.
    for table in _TABLES_WITH_GEO:
        op.add_column(table, sa.Column("district_id", sa.String(), nullable=True))
        op.add_column(table, sa.Column("seri_circle_id", sa.String(), nullable=True))

    for table in _TABLES_WITH_GEO:
        op.execute(
            f"UPDATE {table} t SET district_id = f.district_id, seri_circle_id = f.seri_circle_id "
            f"FROM farmers f WHERE t.farmer_id = f.id"
        )

    for table in _TABLES_WITH_GEO:
        op.alter_column(table, "district_id", nullable=False)
        op.alter_column(table, "seri_circle_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_district_id", table, "districts", ["district_id"], ["id"])
        op.create_foreign_key(f"fk_{table}_seri_circle_id", table, "sericulture_circles", ["seri_circle_id"], ["id"])
        op.create_index(f"ix_{table}_district_id", table, ["district_id"])
        op.create_index(f"ix_{table}_seri_circle_id", table, ["seri_circle_id"])

    # 3. New tables — created before the farmer_submission_id FK on yields needs them to exist.
    op.create_table(
        "farmer_submissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("farmer_id", sa.String(), nullable=False),
        sa.Column("submission_code", sa.String(length=30), nullable=False),
        sa.Column("submission_month", sa.String(length=7), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_id", "submission_month"),
        sa.UniqueConstraint("submission_code"),
    )
    op.create_index("ix_farmer_submissions_farmer_id", "farmer_submissions", ["farmer_id"])
    op.create_index("ix_farmer_submissions_submission_code", "farmer_submissions", ["submission_code"])
    op.create_index("ix_farmer_submissions_submission_month", "farmer_submissions", ["submission_month"])

    op.create_table(
        "farmer_submission_corrections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("farmer_submission_id", sa.String(), nullable=False),
        sa.Column("farmer_id", sa.String(), nullable=False),
        sa.Column("submitted_by_user_id", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by_user_id", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["farmer_submission_id"], ["farmer_submissions.id"]),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmers.id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_farmer_submission_corrections_farmer_submission_id",
                     "farmer_submission_corrections", ["farmer_submission_id"])
    op.create_index("ix_farmer_submission_corrections_farmer_id",
                     "farmer_submission_corrections", ["farmer_id"])

    op.create_table(
        "farmer_draft_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("farmer_id", sa.String(), nullable=False),
        sa.Column("fig_id", sa.String(), nullable=False),
        sa.Column("draft_month", sa.String(length=7), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmers.id"]),
        sa.ForeignKeyConstraint(["fig_id"], ["figs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("farmer_id", "draft_month"),
    )
    op.create_index("ix_farmer_draft_entries_farmer_id", "farmer_draft_entries", ["farmer_id"])
    op.create_index("ix_farmer_draft_entries_fig_id", "farmer_draft_entries", ["fig_id"])
    op.create_index("ix_farmer_draft_entries_draft_month", "farmer_draft_entries", ["draft_month"])

    # 4. yields.farmer_submission_id — sibling to the existing meeting_id column.
    op.add_column("yields", sa.Column("farmer_submission_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_yields_farmer_submission_id", "yields", "farmer_submissions",
                          ["farmer_submission_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_yields_farmer_submission_id", "yields", type_="foreignkey")
    op.drop_column("yields", "farmer_submission_id")

    op.drop_index("ix_farmer_draft_entries_draft_month", table_name="farmer_draft_entries")
    op.drop_index("ix_farmer_draft_entries_fig_id", table_name="farmer_draft_entries")
    op.drop_index("ix_farmer_draft_entries_farmer_id", table_name="farmer_draft_entries")
    op.drop_table("farmer_draft_entries")

    op.drop_index("ix_farmer_submission_corrections_farmer_id", table_name="farmer_submission_corrections")
    op.drop_index("ix_farmer_submission_corrections_farmer_submission_id", table_name="farmer_submission_corrections")
    op.drop_table("farmer_submission_corrections")

    op.drop_index("ix_farmer_submissions_submission_month", table_name="farmer_submissions")
    op.drop_index("ix_farmer_submissions_submission_code", table_name="farmer_submissions")
    op.drop_index("ix_farmer_submissions_farmer_id", table_name="farmer_submissions")
    op.drop_table("farmer_submissions")

    for table in _TABLES_WITH_GEO:
        op.drop_index(f"ix_{table}_seri_circle_id", table_name=table)
        op.drop_index(f"ix_{table}_district_id", table_name=table)
        op.drop_constraint(f"fk_{table}_seri_circle_id", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_district_id", table, type_="foreignkey")
        op.drop_column(table, "seri_circle_id")
        op.drop_column(table, "district_id")

    for table in ["yields", "byproduct_entries", "yield_input_entries", "attendance", "stock"]:
        op.alter_column(table, "fig_id", existing_type=sa.String(), nullable=False)
