"""Stop storing farmer Aadhaar numbers in plaintext.

`farmers.aadhaar_no` (plaintext, indexed) is replaced by three derived columns:

  aadhaar_last4  plaintext last 4 digits, for the masked display shown to every role
                 except the farmer viewing their own record
  aadhaar_hash   HMAC-SHA256 blind index — takes over the index from the dropped
                 plaintext column, because it is what the existing "Aadhaar already
                 registered" duplicate check now queries on
  aadhaar_enc    AES-256-GCM ciphertext, decrypted only by GET /farmers/me

The backfill is a row-by-row Python loop rather than pure SQL because the derivation is
keyed cryptography (see app/core/aadhaar.py), not something the database can express.
Legacy rows whose stored value is not a clean 12 digits are LEFT NULL and reported at the
end rather than crashing the migration — historic data was never validated on entry.

`downgrade()` is genuinely reversible here, since the ciphertext is retained — but only
while AADHAAR_SECRET_KEY is still available and unchanged.

Revision ID: a35af4acdb86
Revises: f9a0b1c2d3e4
Create Date: 2026-08-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

from app.core.aadhaar import normalize_aadhaar, aadhaar_fields, aadhaar_decrypt


revision = 'a35af4acdb86'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('farmers', sa.Column('aadhaar_last4', sa.String(length=4), nullable=True))
    op.add_column('farmers', sa.Column('aadhaar_hash', sa.String(length=64), nullable=True))
    op.add_column('farmers', sa.Column('aadhaar_enc', sa.String(length=255), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(text(
        "SELECT id, aadhaar_no FROM farmers WHERE aadhaar_no IS NOT NULL AND aadhaar_no <> ''"
    )).fetchall()

    converted, skipped = 0, []
    for row in rows:
        try:
            digits = normalize_aadhaar(row.aadhaar_no)
        except ValueError:
            skipped.append(row.id)
            continue
        bind.execute(
            text("UPDATE farmers SET aadhaar_last4=:aadhaar_last4, aadhaar_hash=:aadhaar_hash, "
                 "aadhaar_enc=:aadhaar_enc WHERE id=:id"),
            {**aadhaar_fields(digits), "id": row.id},
        )
        converted += 1

    print(f"[aadhaar] encrypted {converted} of {len(rows)} farmer Aadhaar numbers")
    if skipped:
        print(f"[aadhaar] LEFT NULL — {len(skipped)} row(s) held a value that is not 12 digits: {skipped}")

    op.drop_index('ix_farmers_aadhaar_no', table_name='farmers')
    op.drop_column('farmers', 'aadhaar_no')
    op.create_index(op.f('ix_farmers_aadhaar_hash'), 'farmers', ['aadhaar_hash'])


def downgrade() -> None:
    """Restores the plaintext column by decrypting. Requires the same AADHAAR_SECRET_KEY
    that was used on the way up; rows encrypted under a different key will fail here."""
    op.add_column('farmers', sa.Column('aadhaar_no', sa.String(length=20), nullable=True))

    bind = op.get_bind()
    for row in bind.execute(text(
        "SELECT id, aadhaar_enc FROM farmers WHERE aadhaar_enc IS NOT NULL"
    )).fetchall():
        bind.execute(
            text("UPDATE farmers SET aadhaar_no=:a WHERE id=:i"),
            {"a": aadhaar_decrypt(row.aadhaar_enc), "i": row.id},
        )

    op.create_index('ix_farmers_aadhaar_no', 'farmers', ['aadhaar_no'])
    op.drop_index(op.f('ix_farmers_aadhaar_hash'), table_name='farmers')
    op.drop_column('farmers', 'aadhaar_enc')
    op.drop_column('farmers', 'aadhaar_hash')
    op.drop_column('farmers', 'aadhaar_last4')
