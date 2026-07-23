"""rename circle_id to seri_circle_id on farmers and figs

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def _fk_name(bind, table_name, column_name):
    for fk in sa.inspect(bind).get_foreign_keys(table_name):
        if fk["constrained_columns"] == [column_name]:
            return fk["name"]
    return None


def upgrade() -> None:
    bind = op.get_bind()

    farmers_fk = _fk_name(bind, "farmers", "circle_id")
    figs_fk = _fk_name(bind, "figs", "circle_id")

    op.alter_column("farmers", "circle_id", new_column_name="seri_circle_id")
    op.alter_column("figs", "circle_id", new_column_name="seri_circle_id")

    op.execute("ALTER INDEX ix_farmers_circle_id RENAME TO ix_farmers_seri_circle_id")
    op.execute("ALTER INDEX ix_figs_circle_id RENAME TO ix_figs_seri_circle_id")

    if farmers_fk:
        op.execute(f'ALTER TABLE farmers RENAME CONSTRAINT "{farmers_fk}" TO farmers_seri_circle_id_fkey')
    if figs_fk:
        op.execute(f'ALTER TABLE figs RENAME CONSTRAINT "{figs_fk}" TO figs_seri_circle_id_fkey')


def downgrade() -> None:
    bind = op.get_bind()

    farmers_fk = _fk_name(bind, "farmers", "seri_circle_id")
    figs_fk = _fk_name(bind, "figs", "seri_circle_id")

    if farmers_fk:
        op.execute(f'ALTER TABLE farmers RENAME CONSTRAINT "{farmers_fk}" TO farmers_circle_id_fkey')
    if figs_fk:
        op.execute(f'ALTER TABLE figs RENAME CONSTRAINT "{figs_fk}" TO figs_circle_id_fkey')

    op.execute("ALTER INDEX ix_farmers_seri_circle_id RENAME TO ix_farmers_circle_id")
    op.execute("ALTER INDEX ix_figs_seri_circle_id RENAME TO ix_figs_circle_id")

    op.alter_column("figs", "seri_circle_id", new_column_name="circle_id")
    op.alter_column("farmers", "seri_circle_id", new_column_name="circle_id")
