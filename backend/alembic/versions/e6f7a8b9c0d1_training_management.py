"""Training Management: nomination/approval gate on Beneficiary, Scheme->Training link,
new demographic targeting criteria, and new training_attendance/training_certificates tables.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Scheme: new demographic targeting dimensions (FARMER-kind only) ----
    op.add_column("schemes", sa.Column("target_caste_ids", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("target_religion_ids", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("target_education_level_ids", sa.JSON(), nullable=True))
    op.add_column("schemes", sa.Column("target_pwd_only", sa.Boolean(), nullable=False, server_default=sa.false()))

    conn = op.get_bind()
    for col in ("target_caste_ids", "target_religion_ids", "target_education_level_ids"):
        conn.execute(sa.text(f"UPDATE schemes SET {col} = '[]'::jsonb WHERE {col} IS NULL"))

    op.alter_column("schemes", "target_caste_ids", nullable=False)
    op.alter_column("schemes", "target_religion_ids", nullable=False)
    op.alter_column("schemes", "target_education_level_ids", nullable=False)

    # ---- Beneficiary: nomination/approval gate (Training-support-type schemes only —
    # default "APPROVED" preserves current immediate-and-final behavior for Cash/Kind and
    # every pre-existing row) ----
    op.add_column("beneficiaries", sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20),
                                             nullable=False, server_default="APPROVED"))
    op.add_column("beneficiaries", sa.Column("created_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("beneficiaries", sa.Column("approved_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("beneficiaries", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("beneficiaries", sa.Column("rejection_reason", sa.String(length=500), nullable=True))
    op.create_foreign_key("fk_beneficiaries_created_by_user_id", "beneficiaries", "users", ["created_by_user_id"], ["id"])
    op.create_foreign_key("fk_beneficiaries_approved_by_user_id", "beneficiaries", "users", ["approved_by_user_id"], ["id"])

    # ---- Training: link to the funding scheme (nullable — legacy requests have none) ----
    op.add_column("trainings", sa.Column("scheme_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key("fk_trainings_scheme_id", "trainings", "schemes", ["scheme_id"], ["id"])
    op.create_index("ix_trainings_scheme_id", "trainings", ["scheme_id"])

    # ---- New: training_attendance ----
    op.create_table(
        "training_attendance",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), primary_key=True),
        sa.Column("training_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("beneficiary_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marked_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("marked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"]),
        sa.ForeignKeyConstraint(["marked_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("training_id", "beneficiary_id", name="uq_training_attendance_training_beneficiary"),
    )
    op.create_index("ix_training_attendance_training_id", "training_attendance", ["training_id"])
    op.create_index("ix_training_attendance_beneficiary_id", "training_attendance", ["beneficiary_id"])

    # ---- New: training_certificates ----
    op.create_table(
        "training_certificates",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), primary_key=True),
        sa.Column("training_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("beneficiary_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("certificate_number", sa.String(length=30), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("issued_by_user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("pdf_path", sa.String(length=500), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"]),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["beneficiaries.id"]),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("certificate_number", name="uq_training_certificates_certificate_number"),
        # Deliberately NOT unique on (training_id, beneficiary_id) — a revoked certificate must
        # not block issuing a fresh one for the same beneficiary; "only one ACTIVE certificate"
        # is enforced by generate_certificates()'s own revoked=False check, not a DB constraint.
    )
    op.create_index("ix_training_certificates_training_id", "training_certificates", ["training_id"])
    op.create_index("ix_training_certificates_beneficiary_id", "training_certificates", ["beneficiary_id"])
    op.create_index("ix_training_certificates_certificate_number", "training_certificates", ["certificate_number"])


def downgrade() -> None:
    raise NotImplementedError(
        "This migration adds the Beneficiary nomination/approval gate (status column) and new "
        "training attendance/certificate tables; reverting would silently un-gate pending Training "
        "nominations and drop attendance/certificate records. Restore from a pre-migration backup instead."
    )
