"""conversion_standards: replace direct %-entry with quantity-based entry.

Adds standard_input_qty/output_min_qty/output_max_qty (in each product's own unit) so the
State Admin enters e.g. "100 Eri Egg (DFL) -> 20-25 kg Eri Cocoon" instead of typing a bare
percentage. min_pct/max_pct stay as real, stored columns (now derived+written by the router
at create/update time) so services/yield_matrix.py's consuming code needs no changes at all.

Existing rows are backfilled losslessly: standard_input_qty=100, output_min_qty=<old min_pct>,
output_max_qty=<old max_pct> — with 100 as the input base, output_qty numerically equals the
percentage, so min_pct/max_pct are unchanged once the router starts recomputing them.

Revision ID: b2c4d6e8f0a1
Revises: 5aac3495e5ca
Create Date: 2026-08-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c4d6e8f0a1'
down_revision = '5aac3495e5ca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversion_standards", sa.Column("standard_input_qty", sa.Float(), nullable=True))
    op.add_column("conversion_standards", sa.Column("output_min_qty", sa.Float(), nullable=True))
    op.add_column("conversion_standards", sa.Column("output_max_qty", sa.Float(), nullable=True))

    op.execute(
        "UPDATE conversion_standards SET standard_input_qty = 100, "
        "output_min_qty = min_pct, output_max_qty = max_pct"
    )

    op.alter_column("conversion_standards", "standard_input_qty", nullable=False)
    op.alter_column("conversion_standards", "output_min_qty", nullable=False)
    op.alter_column("conversion_standards", "output_max_qty", nullable=False)


def downgrade() -> None:
    op.drop_column("conversion_standards", "output_max_qty")
    op.drop_column("conversion_standards", "output_min_qty")
    op.drop_column("conversion_standards", "standard_input_qty")
