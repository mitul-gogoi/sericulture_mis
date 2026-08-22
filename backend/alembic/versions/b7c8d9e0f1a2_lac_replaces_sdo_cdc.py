"""Sericulture Circles map to a Legislative Assembly Constituency, not an SDO/CDC office.

The Directorate does not work in terms of Sub-division Offices, and CDC offices exist only
in some places, so neither covers Assam uniformly. The constituency does, so the whole
`subdivision_cdc_offices` master is replaced by `lacs`.

Nothing is migrated across. The old table held 19 rows (4 Sub-division Offices, 15 CDCs)
and only 3 of 87 circles pointed at one, so carrying them over would mean keeping SDO rows
the user explicitly asked to remove and inventing constituency names for CDC rows. The
circles are simply left unmapped for the State Admin to re-map against the seeded LAC list.

Revision ID: b7c8d9e0f1a2
Revises: e3f4a5b6c7d8
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lacs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("district_id", sa.String(), nullable=False),
        sa.Column("lac_no", sa.Integer(), nullable=True),
        sa.Column("lac_name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "lac_name", name="uq_lac_district_name"),
    )
    op.create_index("ix_lacs_district_id", "lacs", ["district_id"])

    op.add_column("sericulture_circles", sa.Column("lac_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_sericulture_circles_lac_id", "sericulture_circles", "lacs",
                          ["lac_id"], ["id"])
    op.create_index("ix_sericulture_circles_lac_id", "sericulture_circles", ["lac_id"])

    # The FK has to go before the table it points at.
    op.drop_constraint("fk_sericulture_circles_subdivision_cdc_id", "sericulture_circles",
                       type_="foreignkey")
    op.drop_index("ix_sericulture_circles_subdivision_cdc_id", table_name="sericulture_circles")
    op.drop_column("sericulture_circles", "subdivision_cdc_id")
    op.drop_table("subdivision_cdc_offices")


def downgrade() -> None:
    """Restores the shape but not the rows — the SDO/CDC records are gone for good, and
    every circle comes back unmapped."""
    op.create_table(
        "subdivision_cdc_offices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("district_id", sa.String(), nullable=False),
        sa.Column("office_type", sa.String(length=20), nullable=False),
        sa.Column("office_name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("office_address", sa.Text(), nullable=True),
        sa.Column("office_contact_no", sa.String(length=15), nullable=True),
        sa.Column("officer_in_charge_name", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["district_id"], ["districts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "office_name"),
    )
    op.add_column("sericulture_circles",
                  sa.Column("subdivision_cdc_id", sa.String(), nullable=True))
    op.create_foreign_key("fk_sericulture_circles_subdivision_cdc_id", "sericulture_circles",
                          "subdivision_cdc_offices", ["subdivision_cdc_id"], ["id"])
    op.create_index("ix_sericulture_circles_subdivision_cdc_id", "sericulture_circles",
                    ["subdivision_cdc_id"])

    op.drop_index("ix_sericulture_circles_lac_id", table_name="sericulture_circles")
    op.drop_constraint("fk_sericulture_circles_lac_id", "sericulture_circles", type_="foreignkey")
    op.drop_column("sericulture_circles", "lac_id")
    op.drop_index("ix_lacs_district_id", table_name="lacs")
    op.drop_table("lacs")
