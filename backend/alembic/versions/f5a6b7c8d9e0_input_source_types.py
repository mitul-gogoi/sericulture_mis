"""State-Admin-managed input source types

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-19 00:15:00.000000

"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def _uuid() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    op.create_table(
        "input_source_types",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_name", sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.Column("requires_scheme", sa.Boolean(), nullable=False),
        sa.Column("is_own_source", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name"),
    )

    op.create_table(
        "stap_source_types",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("stap_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["stap_id"], ["silk_type_activity_products.id"]),
        sa.ForeignKeyConstraint(["source_type_id"], ["input_source_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stap_id", "source_type_id"),
    )
    op.create_index("ix_stap_source_types_stap_id", "stap_source_types", ["stap_id"])
    op.create_index("ix_stap_source_types_source_type_id", "stap_source_types", ["source_type_id"])

    # Seed the 5 canonical source types, replacing the old hardcoded 4-string enum.
    ids = {name: _uuid() for name in
           ("Own Land", "Government Land", "Own Source", "Market Source", "Government Source")}
    input_source_types = sa.table(
        "input_source_types",
        sa.column("id", sa.String), sa.column("source_name", sa.String),
        sa.column("requires_scheme", sa.Boolean), sa.column("is_own_source", sa.Boolean),
        sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(input_source_types, [
        {"id": ids["Own Land"], "source_name": "Own Land", "requires_scheme": False, "is_own_source": False, "is_active": True, "created_at": now},
        {"id": ids["Government Land"], "source_name": "Government Land", "requires_scheme": False, "is_own_source": False, "is_active": True, "created_at": now},
        {"id": ids["Own Source"], "source_name": "Own Source", "requires_scheme": False, "is_own_source": True, "is_active": True, "created_at": now},
        {"id": ids["Market Source"], "source_name": "Market Source", "requires_scheme": False, "is_own_source": False, "is_active": True, "created_at": now},
        {"id": ids["Government Source"], "source_name": "Government Source", "requires_scheme": True, "is_own_source": False, "is_active": True, "created_at": now},
    ])

    # Add the new FK column (nullable for now), backfill from the old string column, then
    # tighten to NOT NULL and drop the string column.
    op.add_column("yield_input_entries", sa.Column("source_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    backfill_map = {
        "Own Source": ids["Own Source"],
        "Purchased": ids["Market Source"],
        "Government Scheme": ids["Government Source"],
        "Government Land/Forest": ids["Government Land"],
    }
    for old_value, new_id in backfill_map.items():
        bind.execute(
            sa.text("UPDATE yield_input_entries SET source_type_id = :new_id WHERE source_type = :old_value"),
            {"new_id": new_id, "old_value": old_value},
        )
    # Any row with an unrecognized old value (shouldn't happen — VALID_INPUT_SOURCE_TYPES
    # enforced exactly these 4 strings) falls back to Own Source rather than being left null.
    bind.execute(
        sa.text("UPDATE yield_input_entries SET source_type_id = :fallback WHERE source_type_id IS NULL"),
        {"fallback": ids["Own Source"]},
    )

    op.alter_column("yield_input_entries", "source_type_id", nullable=False)
    op.create_index("ix_yield_input_entries_source_type_id", "yield_input_entries", ["source_type_id"])
    op.create_foreign_key(
        "fk_yield_input_entries_source_type_id", "yield_input_entries",
        "input_source_types", ["source_type_id"], ["id"],
    )
    op.drop_column("yield_input_entries", "source_type")


def downgrade() -> None:
    raise NotImplementedError(
        "This migration replaces the free-text source_type column with a source_type_id FK "
        "into the new State-Admin-managed input_source_types table; restoring the old string "
        "column would require re-deriving it from the (now State-Admin-editable) source names. "
        "Restore from a pre-migration backup instead."
    )
