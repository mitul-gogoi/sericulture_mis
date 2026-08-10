"""asset_instances: add asset_code (Asset Code) and a GPS capture/approval lifecycle.

Adds asset_code (SERI-AST-NNNNN, matching the existing SERI-FRM/SERI-FIG/SERI-MSG convention)
plus latitude/longitude and a gps_status lifecycle (Not Submitted -> Pending -> Verified/Failed,
mirroring Land.gps_verified exactly) so a FIG President can capture an asset's location on the
Asset Management page and a District Admin can approve/reject it — entirely independent of the
existing verification_status (physical-condition check). Existing rows are backfilled with
sequential asset codes assigned in created_at order; the GPS fields need no backfill since no
asset has ever had a location recorded before this migration.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-08-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd6e7f8a9b0c1'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset_instances", sa.Column("asset_code", sa.String(length=30), nullable=True))
    op.add_column("asset_instances", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("asset_instances", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("asset_instances", sa.Column("gps_status", sa.String(length=20), nullable=False,
                                                server_default="Not Submitted"))
    op.add_column("asset_instances", sa.Column("gps_failure_reason", sa.String(), nullable=True))
    op.add_column("asset_instances", sa.Column("gps_verified_by", sa.String(), nullable=True))
    op.add_column("asset_instances", sa.Column("gps_verified_at", sa.DateTime(), nullable=True))

    op.execute(
        "UPDATE asset_instances a SET asset_code = 'SERI-AST-' || LPAD(sub.rn::text, 5, '0') "
        "FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn FROM asset_instances) sub "
        "WHERE a.id = sub.id"
    )

    op.alter_column("asset_instances", "asset_code", nullable=False)
    op.alter_column("asset_instances", "gps_status", server_default=None)
    op.create_unique_constraint("uq_asset_instances_asset_code", "asset_instances", ["asset_code"])
    op.create_index("ix_asset_instances_asset_code", "asset_instances", ["asset_code"])


def downgrade() -> None:
    op.drop_index("ix_asset_instances_asset_code", table_name="asset_instances")
    op.drop_constraint("uq_asset_instances_asset_code", "asset_instances", type_="unique")
    op.drop_column("asset_instances", "gps_verified_at")
    op.drop_column("asset_instances", "gps_verified_by")
    op.drop_column("asset_instances", "gps_failure_reason")
    op.drop_column("asset_instances", "gps_status")
    op.drop_column("asset_instances", "longitude")
    op.drop_column("asset_instances", "latitude")
    op.drop_column("asset_instances", "asset_code")
