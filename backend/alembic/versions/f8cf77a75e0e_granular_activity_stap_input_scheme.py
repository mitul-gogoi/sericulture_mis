"""granular activity stap input scheme

Revision ID: f8cf77a75e0e
Revises: f6a7b8c9d0e1
Create Date: 2026-07-16 23:14:41.396649

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'f8cf77a75e0e'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def _fk_name(bind, table_name, column_name):
    for fk in sa.inspect(bind).get_foreign_keys(table_name):
        if fk["constrained_columns"] == [column_name]:
            return fk["name"]
    return None


def _unique_name(bind, table_name, column_names):
    for uc in sa.inspect(bind).get_unique_constraints(table_name):
        if set(uc["column_names"]) == set(column_names):
            return uc["name"]
    return None


def upgrade() -> None:
    bind = op.get_bind()

    # ---- 1. New tables ----
    op.create_table(
        "activity_groups",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("group_name", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_name"),
        sa.UniqueConstraint("sequence_no"),
    )

    op.create_table(
        "yield_input_entries",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("parent_yield_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("farmer_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fig_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("product_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("yield_month", sqlmodel.sql.sqltypes.AutoString(length=7), nullable=False),
        sa.Column("unit_of_measure", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("remarks", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("submission_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_yield_id"], ["yields.id"]),
        sa.ForeignKeyConstraint(["farmer_id"], ["farmers.id"]),
        sa.ForeignKeyConstraint(["fig_id"], ["figs.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_yield_id", "product_id"),
    )
    op.create_index("ix_yield_input_entries_parent_yield_id", "yield_input_entries", ["parent_yield_id"])
    op.create_index("ix_yield_input_entries_farmer_id", "yield_input_entries", ["farmer_id"])
    op.create_index("ix_yield_input_entries_fig_id", "yield_input_entries", ["fig_id"])
    op.create_index("ix_yield_input_entries_product_id", "yield_input_entries", ["product_id"])
    op.create_index("ix_yield_input_entries_yield_month", "yield_input_entries", ["yield_month"])
    op.create_index("ix_yield_input_farmer_month", "yield_input_entries", ["farmer_id", "yield_month"])

    # ---- 2. activities: restructure to be silk-type-specific + grouped + ordered ----
    old_activity_unique = _unique_name(bind, "activities", ["activity_name"])
    if old_activity_unique:
        op.drop_constraint(old_activity_unique, "activities", type_="unique")

    op.add_column("activities", sa.Column("silk_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("activities", sa.Column("activity_group_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("activities", sa.Column("step_no", sa.Integer(), nullable=True))
    op.add_column("activities", sa.Column("description", sa.Text(), nullable=True))

    # The old 8 activities are silk-type-agnostic and have no sensible 1:1 mapping into the new
    # granular, silk-type-specific catalog — this feature replaces them wholesale. Safe only
    # because this migration is always immediately followed by wipe_all()+seed_all()+
    # generate_demo_data() (see CLAUDE.md / project plan) — never run this migration in isolation
    # against data you intend to keep.
    op.execute("TRUNCATE TABLE activities CASCADE")

    op.alter_column("activities", "activity_name", type_=sqlmodel.sql.sqltypes.AutoString(length=120))
    op.alter_column("activities", "silk_type_id", nullable=False)
    op.alter_column("activities", "step_no", nullable=False)
    op.create_foreign_key("fk_activities_silk_type_id", "activities", "silk_types", ["silk_type_id"], ["id"])
    op.create_foreign_key("fk_activities_activity_group_id", "activities", "activity_groups", ["activity_group_id"], ["id"])
    op.create_index("ix_activities_silk_type_id", "activities", ["silk_type_id"])
    op.create_index("ix_activities_activity_group_id", "activities", ["activity_group_id"])
    op.create_unique_constraint("uq_activities_silk_type_name", "activities", ["silk_type_id", "activity_name"])
    op.create_unique_constraint("uq_activities_silk_type_group_step", "activities", ["silk_type_id", "activity_group_id", "step_no"])

    # ---- 3. silk_type_activity_products: add role, widen uniqueness ----
    old_stap_unique = _unique_name(bind, "silk_type_activity_products", ["silk_type_id", "activity_id", "product_id"])
    if old_stap_unique:
        op.drop_constraint(old_stap_unique, "silk_type_activity_products", type_="unique")
    op.add_column("silk_type_activity_products", sa.Column(
        "role", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False, server_default="OUTPUT"))
    op.alter_column("silk_type_activity_products", "role", server_default=None)
    op.create_unique_constraint(
        "uq_stap_silk_type_activity_product_role", "silk_type_activity_products",
        ["silk_type_id", "activity_id", "product_id", "role"])

    # ---- 4. schemes: single activity_id -> activity_ids list, add support_type ----
    schemes_activity_fk = _fk_name(bind, "schemes", "activity_id")
    if schemes_activity_fk:
        op.drop_constraint(schemes_activity_fk, "schemes", type_="foreignkey")
    op.add_column("schemes", sa.Column("activity_ids", sa.JSON(), nullable=True))
    op.execute("""
        UPDATE schemes SET activity_ids = CASE WHEN activity_id IS NOT NULL
            THEN json_build_array(activity_id) ELSE '[]'::json END
    """)
    op.alter_column("schemes", "activity_ids", nullable=False)
    op.drop_column("schemes", "activity_id")
    op.add_column("schemes", sa.Column(
        "support_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False, server_default="Cash"))
    op.alter_column("schemes", "support_type", server_default=None)


def downgrade() -> None:
    raise NotImplementedError(
        "This migration restructures Activity into a silk-type-specific, grouped, ordered catalog "
        "and truncates the old 8 shared activities (and everything that cascades from them) — "
        "there is no lossless way back. Restore from a pre-migration backup instead."
    )
