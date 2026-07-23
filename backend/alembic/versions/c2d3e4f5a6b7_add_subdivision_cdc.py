"""add subdivision/cdc offices

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subdivision_cdc_offices",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("district_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("office_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("office_name", sqlmodel.sql.sqltypes.AutoString(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("office_address", sa.Text(), nullable=True),
        sa.Column("office_contact_no", sqlmodel.sql.sqltypes.AutoString(length=15), nullable=True),
        sa.Column("officer_in_charge_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "office_name"),
    )
    op.create_index("ix_subdivision_cdc_offices_district_id", "subdivision_cdc_offices", ["district_id"])

    op.add_column("sericulture_circles", sa.Column("subdivision_cdc_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_sericulture_circles_subdivision_cdc_id", "sericulture_circles",
                          "subdivision_cdc_offices", ["subdivision_cdc_id"], ["id"])
    op.create_index("ix_sericulture_circles_subdivision_cdc_id", "sericulture_circles", ["subdivision_cdc_id"])


def downgrade() -> None:
    op.drop_index("ix_sericulture_circles_subdivision_cdc_id", table_name="sericulture_circles")
    op.drop_constraint("fk_sericulture_circles_subdivision_cdc_id", "sericulture_circles", type_="foreignkey")
    op.drop_column("sericulture_circles", "subdivision_cdc_id")

    op.drop_index("ix_subdivision_cdc_offices_district_id", table_name="subdivision_cdc_offices")
    op.drop_table("subdivision_cdc_offices")
