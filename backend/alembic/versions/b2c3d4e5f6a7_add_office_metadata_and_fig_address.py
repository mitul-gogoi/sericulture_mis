"""add office metadata and fig address fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-14 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("districts", "sericulture_circles"):
        op.add_column(table, sa.Column("office_name", sqlmodel.sql.sqltypes.AutoString(length=160), nullable=True))
        op.add_column(table, sa.Column("office_address", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("office_contact_no", sqlmodel.sql.sqltypes.AutoString(length=15), nullable=True))
        op.add_column(table, sa.Column("officer_in_charge_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))

    op.add_column("figs", sa.Column("village_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column("figs", sa.Column("post_office", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column("figs", sa.Column("police_station", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column("figs", sa.Column("pin_code", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True))

    op.create_table(
        "directorate_office",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("office_name", sqlmodel.sql.sqltypes.AutoString(length=160), nullable=False,
                  server_default="Directorate of Sericulture, Assam"),
        sa.Column("office_address", sa.Text(), nullable=True),
        sa.Column("office_contact_no", sqlmodel.sql.sqltypes.AutoString(length=15), nullable=True),
        sa.Column("officer_in_charge_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("directorate_office")
    op.drop_column("figs", "pin_code")
    op.drop_column("figs", "police_station")
    op.drop_column("figs", "post_office")
    op.drop_column("figs", "village_name")
    for table in ("districts", "sericulture_circles"):
        op.drop_column(table, "officer_in_charge_name")
        op.drop_column(table, "office_contact_no")
        op.drop_column(table, "office_address")
        op.drop_column(table, "office_name")
