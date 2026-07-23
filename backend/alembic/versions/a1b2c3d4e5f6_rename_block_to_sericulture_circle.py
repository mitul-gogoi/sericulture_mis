"""rename block to sericulture circle

Revision ID: a1b2c3d4e5f6
Revises: 35f566bcc2d9
Create Date: 2026-07-14 16:47:09.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'a1b2c3d4e5f6'
down_revision = '35f566bcc2d9'
branch_labels = None
depends_on = None


def _fk_name(bind, table_name, column_name):
    for fk in sa.inspect(bind).get_foreign_keys(table_name):
        if fk["constrained_columns"] == [column_name]:
            return fk["name"]
    return None


def _unique_name(bind, table_name, column_names):
    for uc in sa.inspect(bind).get_unique_constraints(table_name):
        if uc["column_names"] == column_names:
            return uc["name"]
    return None


def upgrade() -> None:
    bind = op.get_bind()

    # ---- Look up existing constraint/index names before anything moves ----
    blocks_unique = _unique_name(bind, "blocks", ["district_id", "block_name"])
    farmers_fk = _fk_name(bind, "farmers", "block_id")
    figs_fk = _fk_name(bind, "figs", "block_id")

    # ---- Pure rename: table, columns — no data movement, FKs keep working via OID ----
    op.rename_table("blocks", "sericulture_circles")
    op.alter_column("sericulture_circles", "block_name", new_column_name="circle_name")
    op.alter_column("farmers", "block_id", new_column_name="circle_id")
    op.alter_column("figs", "block_id", new_column_name="circle_id")

    # ---- Rename indexes (Postgres does not auto-rename on RENAME TABLE/COLUMN) ----
    op.execute("ALTER INDEX ix_blocks_district_id RENAME TO ix_sericulture_circles_district_id")
    op.execute("ALTER INDEX ix_farmers_block_id RENAME TO ix_farmers_circle_id")
    op.execute("ALTER INDEX ix_figs_block_id RENAME TO ix_figs_circle_id")

    # ---- Rename constraints (cosmetic only — avoids autogenerate drift later) ----
    if blocks_unique:
        op.execute(f'ALTER TABLE sericulture_circles RENAME CONSTRAINT "{blocks_unique}" TO uq_sericulture_circles_district_id_circle_name')
    if farmers_fk:
        op.execute(f'ALTER TABLE farmers RENAME CONSTRAINT "{farmers_fk}" TO farmers_circle_id_fkey')
    if figs_fk:
        op.execute(f'ALTER TABLE figs RENAME CONSTRAINT "{figs_fk}" TO figs_circle_id_fkey')


def downgrade() -> None:
    bind = op.get_bind()

    circles_unique = _unique_name(bind, "sericulture_circles", ["district_id", "circle_name"])
    farmers_fk = _fk_name(bind, "farmers", "circle_id")
    figs_fk = _fk_name(bind, "figs", "circle_id")

    if circles_unique:
        op.execute(f'ALTER TABLE sericulture_circles RENAME CONSTRAINT "{circles_unique}" TO {"blocks_district_id_block_name_key"}')
    if farmers_fk:
        op.execute(f'ALTER TABLE farmers RENAME CONSTRAINT "{farmers_fk}" TO farmers_block_id_fkey')
    if figs_fk:
        op.execute(f'ALTER TABLE figs RENAME CONSTRAINT "{figs_fk}" TO figs_block_id_fkey')

    op.execute("ALTER INDEX ix_sericulture_circles_district_id RENAME TO ix_blocks_district_id")
    op.execute("ALTER INDEX ix_farmers_circle_id RENAME TO ix_farmers_block_id")
    op.execute("ALTER INDEX ix_figs_circle_id RENAME TO ix_figs_block_id")

    op.alter_column("figs", "circle_id", new_column_name="block_id")
    op.alter_column("farmers", "circle_id", new_column_name="block_id")
    op.alter_column("sericulture_circles", "circle_name", new_column_name="block_name")
    op.rename_table("sericulture_circles", "blocks")
