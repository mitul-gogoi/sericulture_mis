"""rename karimganj to sribhumi

Revision ID: e20a2188b717
Revises: 2c64047697ca
Create Date: 2026-07-10 15:28:43.157620

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'e20a2188b717'
down_revision = '2c64047697ca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    karimganj = bind.execute(sa.text("SELECT id FROM districts WHERE district_name = 'Karimganj'")).scalar()
    if karimganj is None:
        return  # already migrated, or never seeded on this DB

    sribhumi = bind.execute(sa.text("SELECT id FROM districts WHERE district_name = 'Sribhumi'")).scalar()

    if sribhumi is None:
        # No separate "Sribhumi" row exists — simple in-place rename, preserves the id so every
        # FK reference (blocks/farmers/users/etc.) stays valid with zero data migration.
        bind.execute(sa.text("UPDATE districts SET district_name = 'Sribhumi' WHERE id = :id"), {"id": karimganj})
        return

    # A separate "Sribhumi" row already exists on this DB (the State Admin added it via the
    # Masters UI before Assam's real-world renaming was reflected here) — merge Karimganj into it:
    # repoint every FK reference, dropping/skipping anything that would collide with a
    # unique constraint against data already under Sribhumi.
    dup_blocks = bind.execute(sa.text("""
        SELECT b1.id FROM blocks b1
        JOIN blocks b2 ON b2.district_id = :sribhumi AND b2.block_name = b1.block_name
        WHERE b1.district_id = :karimganj
    """), {"sribhumi": sribhumi, "karimganj": karimganj}).fetchall()
    for row in dup_blocks:
        bind.execute(sa.text("DELETE FROM blocks WHERE id = :id"), {"id": row.id})

    dup_allocations = bind.execute(sa.text("""
        SELECT a1.id FROM allocations a1
        JOIN allocations a2 ON a2.district_id = :sribhumi AND a2.scheme_id = a1.scheme_id
        WHERE a1.district_id = :karimganj
    """), {"sribhumi": sribhumi, "karimganj": karimganj}).fetchall()
    for row in dup_allocations:
        bind.execute(sa.text("DELETE FROM allocations WHERE id = :id"), {"id": row.id})

    for table in ("blocks", "farmers", "users", "trainings", "allocations", "beneficiaries", "figs"):
        bind.execute(sa.text(f"UPDATE {table} SET district_id = :sribhumi WHERE district_id = :karimganj"),
                     {"sribhumi": sribhumi, "karimganj": karimganj})

    bind.execute(sa.text("DELETE FROM districts WHERE id = :id"), {"id": karimganj})


def downgrade() -> None:
    raise NotImplementedError(
        "Merging Karimganj into an existing Sribhumi row (or renaming it) is not reversible once "
        "dependent rows have been repointed/deduplicated. Restore from a pre-migration backup instead."
    )
