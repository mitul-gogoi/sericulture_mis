"""Asset management: asset_types catalog, asset_instances, asset_verification_logs

Revision ID: a7f3c9d2e5b1
Revises: c9d8e7f6a5b4
Create Date: 2026-07-20 09:30:00.000000

"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'a7f3c9d2e5b1'
down_revision = 'c9d8e7f6a5b4'
branch_labels = None
depends_on = None


def _uuid() -> str:
    return str(uuid.uuid4())


# (name, category, silk_types, ownership_level, useful_life_years, typically_scheme_funded)
# Source: Asset Management spec §1. Deliberately excludes host-plant plantations (land — tracked
# in Land & GIS) and low-value consumables (chaloni baskets, trunk guards, paraffin paper, etc.).
SEED_ASSET_TYPES = [
    ("Rearing House", "STRUCTURE", ["Eri", "Mulberry"], "INDIVIDUAL", 6, True),
    ("Chawki Rearing Centre (CRC)", "SHARED_INFRASTRUCTURE", ["Mulberry"], "FIG", 8, True),
    ("Common Facility Centre (CFC) — Reeling/Degumming", "SHARED_INFRASTRUCTURE",
     ["Eri", "Muga", "Mulberry"], "FIG", 8, True),
    ("Mountage — Chandraki", "EQUIPMENT", ["Eri"], "INDIVIDUAL", 3, True),
    ("Mountage — Bamboo", "EQUIPMENT", ["Eri", "Muga"], "INDIVIDUAL", 3, True),
    ("Mountage — Plastic", "EQUIPMENT", ["Eri"], "INDIVIDUAL", 5, True),
    ("Mountage — Rotary", "EQUIPMENT", ["Mulberry"], "INDIVIDUAL", 5, True),
    ("Mountage — Box-type (Jali)", "EQUIPMENT", ["Muga"], "INDIVIDUAL", 4, True),
    ("Reeling Device — Bhir (traditional)", "EQUIPMENT", ["Muga"], "INDIVIDUAL", 6, True),
    ("Reeling Machine — Motorised/Cottage Basin/Filature", "EQUIPMENT",
     ["Muga", "Mulberry"], "EITHER", 8, True),
    ("Degumming Unit (eco-friendly)", "EQUIPMENT", ["Eri"], "EITHER", 6, True),
    ("Spinning Machine (motorised)", "EQUIPMENT", ["Eri"], "INDIVIDUAL", 5, True),
    ("Loom — Throw-shuttle", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 8, True),
    ("Loom — Fly-shuttle", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 8, True),
    ("Disinfectant Sprayer", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 4, True),
    ("Rearing Trays/Stands", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 4, True),
]


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    op.create_table(
        "asset_types",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("silk_types", sa.JSON(), nullable=True),
        sa.Column("ownership_level", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("useful_life_years", sa.Integer(), nullable=False),
        sa.Column("typically_scheme_funded", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    asset_types_tbl = sa.table(
        "asset_types",
        sa.column("id", sa.String), sa.column("name", sa.String),
        sa.column("category", sa.String), sa.column("silk_types", sa.JSON),
        sa.column("ownership_level", sa.String), sa.column("useful_life_years", sa.Integer),
        sa.column("typically_scheme_funded", sa.Boolean), sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(asset_types_tbl, [
        {"id": _uuid(), "name": name, "category": category, "silk_types": silk_types,
         "ownership_level": ownership, "useful_life_years": life,
         "typically_scheme_funded": funded, "is_active": True, "created_at": now}
        for (name, category, silk_types, ownership, life, funded) in SEED_ASSET_TYPES
    ])

    op.create_table(
        "asset_instances",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("asset_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("owner_type", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=False),
        sa.Column("owner_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("acquisition_mode", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=False),
        sa.Column("scheme_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("beneficiary_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("verification_status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("confidence", sqlmodel.sql.sqltypes.AutoString(length=40), nullable=True),
        sa.Column("photo_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("remarks", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("created_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_verified_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["asset_type_id"], ["asset_types.id"]),
        sa.ForeignKeyConstraint(["scheme_id"], ["schemes.id"]),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"]),
    )
    op.create_index("ix_asset_instances_asset_type_id", "asset_instances", ["asset_type_id"])
    op.create_index("ix_asset_instances_owner_type", "asset_instances", ["owner_type"])
    op.create_index("ix_asset_instances_owner_id", "asset_instances", ["owner_id"])
    op.create_index("ix_asset_instances_scheme_id", "asset_instances", ["scheme_id"])
    op.create_index("ix_asset_instances_beneficiary_id", "asset_instances", ["beneficiary_id"])

    op.create_table(
        "asset_verification_logs",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("asset_instance_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("checked_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("result", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False),
        sa.Column("photo_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("remarks", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["asset_instance_id"], ["asset_instances.id"]),
    )
    op.create_index("ix_asset_verification_logs_asset_instance_id",
                    "asset_verification_logs", ["asset_instance_id"])


def downgrade() -> None:
    raise NotImplementedError(
        "This migration introduces the asset management tables and seeds the asset-type catalog; "
        "dropping them would discard recorded asset holdings that the scheme cooldown check depends on. "
        "Restore from a pre-migration backup instead."
    )
