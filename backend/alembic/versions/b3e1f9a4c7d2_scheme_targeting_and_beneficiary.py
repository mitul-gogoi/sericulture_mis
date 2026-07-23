"""Scheme targeting/lifecycle columns + polymorphic Beneficiary (farmer or FIG)

Revision ID: b3e1f9a4c7d2
Revises: a7f3c9d2e5b1
Create Date: 2026-07-20 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'b3e1f9a4c7d2'
down_revision = 'a7f3c9d2e5b1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Scheme: targeting + lifecycle + asset grant ----
    op.add_column("schemes", sa.Column("beneficiary_kind", sqlmodel.sql.sqltypes.AutoString(length=10),
                                       nullable=False, server_default="FARMER"))
    op.add_column("schemes", sa.Column("target_all_districts", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("schemes", sa.Column("target_district_ids", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("target_silk_type_ids", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("target_genders", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("target_farmer_types", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("grants_asset_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("schemes", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("schemes", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("schemes", sa.Column("notified_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_schemes_grants_asset_type_id", "schemes", "asset_types", ["grants_asset_type_id"], ["id"])

    conn = op.get_bind()
    # Backfill: existing single silk_type_id -> 1-element target list; empty list means "all".
    conn.execute(sa.text(
        "UPDATE schemes SET target_silk_type_ids = jsonb_build_array(silk_type_id) WHERE silk_type_id IS NOT NULL"
    ))
    conn.execute(sa.text(
        "UPDATE schemes SET target_silk_type_ids = '[]'::jsonb WHERE target_silk_type_ids IS NULL"
    ))
    # Legacy "All" meant no farmer-type restriction; anything else becomes a 1-element target list.
    conn.execute(sa.text(
        "UPDATE schemes SET target_farmer_types = jsonb_build_array(eligible_farmer_type) "
        "WHERE eligible_farmer_type IS NOT NULL AND eligible_farmer_type <> 'All'"
    ))
    conn.execute(sa.text(
        "UPDATE schemes SET target_farmer_types = '[]'::jsonb WHERE target_farmer_types IS NULL"
    ))
    conn.execute(sa.text(
        "UPDATE schemes SET target_district_ids = '[]'::jsonb WHERE target_district_ids IS NULL"
    ))
    conn.execute(sa.text(
        "UPDATE schemes SET target_genders = '[]'::jsonb WHERE target_genders IS NULL"
    ))

    op.alter_column("schemes", "target_district_ids", nullable=False)
    op.alter_column("schemes", "target_silk_type_ids", nullable=False)
    op.alter_column("schemes", "target_genders", nullable=False)
    op.alter_column("schemes", "target_farmer_types", nullable=False)

    # ---- Beneficiary: farmer_id -> nullable, add fig_id + beneficiary_type + override reason ----
    op.alter_column("beneficiaries", "farmer_id", existing_type=sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    op.add_column("beneficiaries", sa.Column("fig_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("beneficiaries", sa.Column("beneficiary_type", sqlmodel.sql.sqltypes.AutoString(length=10),
                                             nullable=False, server_default="FARMER"))
    op.add_column("beneficiaries", sa.Column("cooldown_override_reason", sqlmodel.sql.sqltypes.AutoString(length=500),
                                             nullable=True))
    op.create_foreign_key("fk_beneficiaries_fig_id", "beneficiaries", "figs", ["fig_id"], ["id"])
    op.create_index("ix_beneficiaries_fig_id", "beneficiaries", ["fig_id"])


def downgrade() -> None:
    raise NotImplementedError(
        "This migration adds scheme targeting/lifecycle columns and makes Beneficiary polymorphic "
        "(farmer-or-FIG); reverting would silently drop targeting configuration and FIG-beneficiary "
        "records. Restore from a pre-migration backup instead."
    )
