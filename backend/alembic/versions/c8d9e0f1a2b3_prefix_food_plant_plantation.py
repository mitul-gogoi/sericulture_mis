"""Name Food Plant Plantation after its silk type.

Every other activity already carries its silk type in the name; this one did not, so the
Register Farmer form showed three activities all reading plainly "Food Plant Plantation".
They are indistinguishable in the flat "Farmer experience in activities" list, which has no
silk-type grouping to disambiguate them.

Safe to do as a plain rename: nothing stores or filters on `activity_name`. Yields,
`Farmer.experience_activity_ids`, STAP rows and every report key on `activities.id`, so the
new label applies retroactively to existing records, which is the intent.

Written as a generic silk-type prefix rather than three hardcoded updates so it is
idempotent — production already carries the prefixed names and matches zero rows here, and
Tasar would be covered too if that activity is ever created.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""
from alembic import op

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None

BARE_NAME = "Food Plant Plantation"


def upgrade() -> None:
    # Matches only the exact bare name, so re-running cannot produce
    # "Eri Eri Food Plant Plantation".
    op.execute(
        f"""
        UPDATE activities a
        SET activity_name = s.silk_type_name || ' ' || a.activity_name
        FROM silk_types s
        WHERE s.id = a.silk_type_id
          AND a.activity_name = '{BARE_NAME}'
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE activities a
        SET activity_name = '{BARE_NAME}'
        FROM silk_types s
        WHERE s.id = a.silk_type_id
          AND a.activity_name = s.silk_type_name || ' {BARE_NAME}'
        """
    )
