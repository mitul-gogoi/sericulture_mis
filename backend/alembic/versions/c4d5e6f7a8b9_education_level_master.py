"""Education Level master data table — Farmer.education_level (free-text) -> education_level_id (FK)

Revision ID: c4d5e6f7a8b9
Revises: b3e1f9a4c7d2
Create Date: 2026-07-21 10:00:00.000000

"""
import uuid

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'c4d5e6f7a8b9'
down_revision = 'b3e1f9a4c7d2'
branch_labels = None
depends_on = None


def _uuid() -> str:
    return str(uuid.uuid4())


EDUCATION_LEVELS = [
    "Illiterate", "Below Primary", "Primary", "Middle", "Secondary",
    "Higher Secondary", "Graduate", "Post Graduate", "Diploma", "Professional",
]


def upgrade() -> None:
    op.create_table(
        "education_levels",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("education_level_name", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("education_level_name"),
    )

    education_levels_tbl = sa.table(
        "education_levels",
        sa.column("id", sa.String), sa.column("education_level_name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(education_levels_tbl, [
        {"id": _uuid(), "education_level_name": name, "is_active": True}
        for name in EDUCATION_LEVELS
    ])

    op.add_column("farmers", sa.Column("education_level_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_farmers_education_level_id", "farmers", "education_levels",
                          ["education_level_id"], ["id"])

    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE farmers SET education_level_id = el.id "
        "FROM education_levels el WHERE farmers.education_level = el.education_level_name"
    ))

    op.drop_column("farmers", "education_level")


def downgrade() -> None:
    raise NotImplementedError(
        "This migration converts Farmer.education_level from a free-text string into a "
        "master-data FK (education_level_id); reverting would require reconstructing the "
        "original string values and lose the education_levels table. Restore from a "
        "pre-migration backup instead."
    )
