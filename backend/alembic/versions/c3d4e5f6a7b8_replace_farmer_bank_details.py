"""replace farmer bank_details json and add experience activities

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-14 17:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("farmers", sa.Column("account_number", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=True))
    op.add_column("farmers", sa.Column("bank_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column("farmers", sa.Column("branch_name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=True))
    op.add_column("farmers", sa.Column("ifsc_code", sqlmodel.sql.sqltypes.AutoString(length=15), nullable=True))
    op.add_column("farmers", sa.Column("passbook_path", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True))

    bind.execute(sa.text("""
        UPDATE farmers
        SET account_number = bank_details->>'account_no',
            ifsc_code       = bank_details->>'ifsc',
            passbook_path   = bank_details->>'passbook_path'
        WHERE bank_details IS NOT NULL
    """))

    missing = bind.execute(sa.text("""
        SELECT count(*) FROM farmers
        WHERE bank_details IS NOT NULL
          AND bank_details->>'account_no' IS NOT NULL
          AND account_number IS NULL
    """)).scalar()
    if missing:
        raise RuntimeError(f"{missing} farmers rows failed to backfill account_number from bank_details — aborting before dropping the column")

    op.drop_column("farmers", "bank_details")
    op.add_column("farmers", sa.Column("experience_activity_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()

    op.add_column("farmers", sa.Column("bank_details", sa.JSON(), nullable=True))
    bind.execute(sa.text("""
        UPDATE farmers
        SET bank_details = jsonb_build_object(
            'account_no', account_number,
            'ifsc', ifsc_code,
            'passbook_path', passbook_path
        )
        WHERE account_number IS NOT NULL OR ifsc_code IS NOT NULL OR passbook_path IS NOT NULL
    """))

    op.drop_column("farmers", "experience_activity_ids")
    op.drop_column("farmers", "passbook_path")
    op.drop_column("farmers", "ifsc_code")
    op.drop_column("farmers", "branch_name")
    op.drop_column("farmers", "bank_name")
    op.drop_column("farmers", "account_number")
