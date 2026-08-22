"""A FIG runs several activities within one silk type; farmers no longer have a primary.

Two changes that go together, both driven by dropping product-level detail from the
registration forms:

1. figs.stap_id (one silk type + activity + PRODUCT) becomes figs.silk_type_id plus a
   fig_activities join table. Nearly every consumer of stap_id joined through STAP only to
   reach the silk type, so this makes those queries shorter as well as allowing more than one
   activity per FIG.

2. farmers.primary_stap_id is dropped. It only existed to mark one product row as the
   farmer's main line of work, which has no meaning once the form selects activities.

Backfill is exact for existing rows: each FIG's silk type and its one activity are read
straight off the STAP row it already points at, so nothing is guessed.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""
from alembic import op
import sqlalchemy as sa

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fig_activities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("fig_id", sa.String(), nullable=False),
        sa.Column("activity_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fig_id"], ["figs.id"]),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fig_id", "activity_id", name="uq_fig_activity"),
    )
    op.create_index("ix_fig_activities_fig_id", "fig_activities", ["fig_id"])
    op.create_index("ix_fig_activities_activity_id", "fig_activities", ["activity_id"])

    # Add nullable, backfill from the STAP row each FIG already points at, then constrain.
    op.add_column("figs", sa.Column("silk_type_id", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE figs f
        SET silk_type_id = s.silk_type_id
        FROM silk_type_activity_products s
        WHERE s.id = f.stap_id
        """
    )
    op.execute(
        """
        INSERT INTO fig_activities (id, fig_id, activity_id, created_at)
        SELECT gen_random_uuid()::text, f.id, s.activity_id, now()
        FROM figs f
        JOIN silk_type_activity_products s ON s.id = f.stap_id
        ON CONFLICT (fig_id, activity_id) DO NOTHING
        """
    )
    # Any FIG whose stap_id no longer resolves would block the NOT NULL below. There should
    # be none -- stap_id is a foreign key -- but fail loudly rather than silently drop them.
    orphan = op.get_bind().execute(
        sa.text("SELECT count(*) FROM figs WHERE silk_type_id IS NULL")).scalar()
    if orphan:
        raise RuntimeError(
            f"{orphan} FIG(s) have a stap_id that does not resolve to a silk type; "
            "fix those rows before migrating")

    op.alter_column("figs", "silk_type_id", nullable=False)
    op.create_foreign_key("fk_figs_silk_type_id", "figs", "silk_types", ["silk_type_id"], ["id"])
    op.create_index("ix_figs_silk_type_id", "figs", ["silk_type_id"])

    op.drop_column("figs", "stap_id")
    op.drop_column("farmers", "primary_stap_id")


def downgrade() -> None:
    # figs.stap_id cannot be restored faithfully: a FIG may now hold several activities and
    # the original product choice is not recorded anywhere. The first activity's first OUTPUT
    # product is used, which is a reasonable stand-in but not necessarily the original.
    op.add_column("farmers", sa.Column("primary_stap_id", sa.String(), nullable=True))
    op.add_column("figs", sa.Column("stap_id", sa.String(), nullable=True))
    op.execute(
        """
        UPDATE figs f SET stap_id = (
            SELECT s.id FROM silk_type_activity_products s
            JOIN fig_activities fa ON fa.activity_id = s.activity_id AND fa.fig_id = f.id
            WHERE s.silk_type_id = f.silk_type_id AND s.role = 'OUTPUT'
            ORDER BY fa.created_at, s.id LIMIT 1)
        """
    )
    op.drop_index("ix_figs_silk_type_id", table_name="figs")
    op.drop_constraint("fk_figs_silk_type_id", "figs", type_="foreignkey")
    op.drop_column("figs", "silk_type_id")
    op.drop_index("ix_fig_activities_activity_id", table_name="fig_activities")
    op.drop_index("ix_fig_activities_fig_id", table_name="fig_activities")
    op.drop_table("fig_activities")
