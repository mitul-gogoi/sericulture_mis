"""Add the two FIG registration documents.

Captured in step 2 of FIG registration — the FIG row must exist first so the upload
folder can be named after its real code. Both stay nullable: a FIG is created and
usable before its paperwork arrives, and is flagged "Documents pending" until both
are present.

Revision ID: ac1b4bb6cbef
Revises: a943889aa305
"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "ac1b4bb6cbef"
down_revision = "a943889aa305"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("figs", sa.Column(
        "minutes_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))
    op.add_column("figs", sa.Column(
        "group_photo_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("figs", "group_photo_path")
    op.drop_column("figs", "minutes_path")
