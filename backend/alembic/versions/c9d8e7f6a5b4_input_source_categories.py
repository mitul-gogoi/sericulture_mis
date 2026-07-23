"""Input source categories (land vs produce filtering)

Revision ID: c9d8e7f6a5b4
Revises: f5a6b7c8d9e0
Create Date: 2026-07-20 00:15:00.000000

"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'c9d8e7f6a5b4'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def _uuid() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    op.create_table(
        "input_source_categories",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("category_name", sqlmodel.sql.sqltypes.AutoString(length=60), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_name"),
    )

    land_id, produce_id = _uuid(), _uuid()
    input_source_categories = sa.table(
        "input_source_categories",
        sa.column("id", sa.String), sa.column("category_name", sa.String),
        sa.column("is_active", sa.Boolean), sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(input_source_categories, [
        {"id": land_id, "category_name": "Land Related", "is_active": True, "created_at": now},
        {"id": produce_id, "category_name": "Produce Related", "is_active": True, "created_at": now},
    ])

    # input_source_types.category_id — add nullable, backfill by name, tighten to NOT NULL.
    op.add_column("input_source_types", sa.Column("category_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    bind.execute(
        sa.text("UPDATE input_source_types SET category_id = :land_id WHERE source_name IN ('Own Land', 'Government Land')"),
        {"land_id": land_id},
    )
    bind.execute(
        sa.text("UPDATE input_source_types SET category_id = :produce_id WHERE source_name IN ('Own Source', 'Market Source', 'Government Source')"),
        {"produce_id": produce_id},
    )
    # Defensive fallback for any renamed/added rows that didn't match the known 5 names.
    bind.execute(
        sa.text("UPDATE input_source_types SET category_id = :produce_id WHERE category_id IS NULL"),
        {"produce_id": produce_id},
    )
    op.alter_column("input_source_types", "category_id", nullable=False)
    op.create_index("ix_input_source_types_category_id", "input_source_types", ["category_id"])
    op.create_foreign_key(
        "fk_input_source_types_category_id", "input_source_types",
        "input_source_categories", ["category_id"], ["id"],
    )

    # products.default_source_category_id — nullable, no backfill (convenience default only).
    op.add_column("products", sa.Column("default_source_category_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index("ix_products_default_source_category_id", "products", ["default_source_category_id"])
    op.create_foreign_key(
        "fk_products_default_source_category_id", "products",
        "input_source_categories", ["default_source_category_id"], ["id"],
    )

    # silk_type_activity_products.input_source_category_id — nullable, no backfill.
    op.add_column("silk_type_activity_products", sa.Column("input_source_category_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index("ix_silk_type_activity_products_input_source_category_id", "silk_type_activity_products", ["input_source_category_id"])
    op.create_foreign_key(
        "fk_silk_type_activity_products_input_source_category_id", "silk_type_activity_products",
        "input_source_categories", ["input_source_category_id"], ["id"],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "This migration introduces the State-Admin-managed input_source_categories table and "
        "tags every input_source_types row with a required category; restoring the prior "
        "uncategorized state would silently discard State-Admin-edited category assignments. "
        "Restore from a pre-migration backup instead."
    )
