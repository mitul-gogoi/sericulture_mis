"""Drop police_station from farmers and figs.

The field is not needed on either record. It was pure pass-through data — no query
filter, index, constraint or foreign key referenced it — so removing it cannot affect
any existing query.

Revision ID: a943889aa305
Revises: ea46bf012174
"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

revision = "a943889aa305"
down_revision = "ea46bf012174"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("farmers", "police_station")
    op.drop_column("figs", "police_station")


def downgrade() -> None:
    op.add_column("farmers", sa.Column(
        "police_station", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column("figs", sa.Column(
        "police_station", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
