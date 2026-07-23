"""consolidate sector stage into silk type activity product

Revision ID: 35f566bcc2d9
Revises: e20a2188b717
Create Date: 2026-07-10 15:29:02.555849

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
import geoalchemy2


revision = '35f566bcc2d9'
down_revision = 'e20a2188b717'
branch_labels = None
depends_on = None


def _fk_name(bind, table_name, column_name):
    for fk in sa.inspect(bind).get_foreign_keys(table_name):
        if fk["constrained_columns"] == [column_name]:
            return fk["name"]
    return None


def _index_name(bind, table_name, column_name):
    for idx in sa.inspect(bind).get_indexes(table_name):
        if idx["column_names"] == [column_name]:
            return idx["name"]
    return None


def _unique_name(bind, table_name, column_names):
    for uc in sa.inspect(bind).get_unique_constraints(table_name):
        if uc["column_names"] == column_names:
            return uc["name"]
    return None


def upgrade() -> None:
    bind = op.get_bind()

    # ---- 1. Expand: add new nullable columns ----
    op.add_column("figs", sa.Column("stap_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("farmers", sa.Column("stap_ids", sa.JSON(), nullable=True))
    op.add_column("farmers", sa.Column("primary_stap_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("yields", sa.Column("stap_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("schemes", sa.Column("silk_type_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("schemes", sa.Column("activity_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("trainings", sa.Column("activity_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # ---- 2. Migrate: backfill from the legacy_stage_id bridge ----
    bind.execute(sa.text("""
        UPDATE figs f SET stap_id = m.id
        FROM silk_type_activity_products m
        WHERE m.legacy_stage_id = f.stage_id
    """))
    bind.execute(sa.text("""
        UPDATE yields y SET stap_id = m.id
        FROM silk_type_activity_products m
        WHERE m.legacy_stage_id = y.stage_id
    """))
    bind.execute(sa.text("""
        UPDATE farmers f SET primary_stap_id = m.id
        FROM silk_type_activity_products m
        WHERE m.legacy_stage_id = f.primary_stage_id
    """))
    bind.execute(sa.text("""
        UPDATE schemes s SET silk_type_id = st.id
        FROM sectors sec JOIN silk_types st ON st.silk_type_name = sec.sector_name
        WHERE sec.id = s.sector_id
    """))
    # schemes.activity_id / trainings.activity_id: no clean 1:1 mapping exists from a bare
    # stage_id (Stage -> Activity is many-to-one via STAP, ambiguous without a product context),
    # so these are left null for the State Admin to set later via the UI.

    # farmers.stap_ids is a JSON array — transform via a Python loop (small volume: ~12 rows),
    # not raw jsonb SQL, so the mapping is easy to read and verify.
    stage_to_stap = dict(bind.execute(sa.text(
        "SELECT legacy_stage_id, id FROM silk_type_activity_products WHERE legacy_stage_id IS NOT NULL"
    )).fetchall())
    farmers_t = sa.table("farmers", sa.column("id", sqlmodel.sql.sqltypes.AutoString()),
                          sa.column("stage_ids", sa.JSON()), sa.column("stap_ids", sa.JSON()))
    for row in bind.execute(sa.text("SELECT id, stage_ids FROM farmers")).fetchall():
        stage_ids = row.stage_ids or []
        stap_ids = [stage_to_stap[s] for s in stage_ids if s in stage_to_stap]
        bind.execute(farmers_t.update().where(farmers_t.c.id == row.id).values(stap_ids=stap_ids))

    # ---- 3. Tighten: figs.stap_id / yields.stap_id must be fully resolved before going NOT NULL ----
    missing_figs = bind.execute(sa.text("SELECT COUNT(*) FROM figs WHERE stap_id IS NULL")).scalar()
    if missing_figs:
        raise RuntimeError(f"{missing_figs} figs rows failed to resolve stap_id from legacy_stage_id — fix seed/data before migrating")
    missing_yields = bind.execute(sa.text("SELECT COUNT(*) FROM yields WHERE stap_id IS NULL")).scalar()
    if missing_yields:
        raise RuntimeError(f"{missing_yields} yields rows failed to resolve stap_id from legacy_stage_id — fix seed/data before migrating")

    op.alter_column("figs", "stap_id", nullable=False)
    op.alter_column("yields", "stap_id", nullable=False)
    op.create_foreign_key("fk_figs_stap_id", "figs", "silk_type_activity_products", ["stap_id"], ["id"])
    op.create_foreign_key("fk_yields_stap_id", "yields", "silk_type_activity_products", ["stap_id"], ["id"])
    op.create_index(op.f("ix_yields_stap_id"), "yields", ["stap_id"], unique=False)
    op.create_foreign_key("fk_farmers_primary_stap_id", "farmers", "silk_type_activity_products", ["primary_stap_id"], ["id"])
    op.create_foreign_key("fk_schemes_silk_type_id", "schemes", "silk_types", ["silk_type_id"], ["id"])
    op.create_foreign_key("fk_schemes_activity_id", "schemes", "activities", ["activity_id"], ["id"])
    op.create_foreign_key("fk_trainings_activity_id", "trainings", "activities", ["activity_id"], ["id"])

    # ---- 4. Contract: drop the old stage_id-based unique constraint/index, then old columns/tables ----
    old_unique = _unique_name(bind, "yields", ["farmer_id", "stage_id", "yield_month"])
    if old_unique:
        op.drop_constraint(old_unique, "yields", type_="unique")
    op.drop_index("ix_yields_stage_month_fig", table_name="yields")
    op.create_unique_constraint("uq_yields_farmer_stap_month", "yields", ["farmer_id", "stap_id", "yield_month"])
    op.create_index("ix_yields_stap_month_fig", "yields", ["stap_id", "yield_month", "fig_id"], unique=False)

    stap_legacy_fk = _fk_name(bind, "silk_type_activity_products", "legacy_stage_id")
    if stap_legacy_fk:
        op.drop_constraint(stap_legacy_fk, "silk_type_activity_products", type_="foreignkey")
    stap_legacy_idx = _index_name(bind, "silk_type_activity_products", "legacy_stage_id")
    if stap_legacy_idx:
        op.drop_index(stap_legacy_idx, table_name="silk_type_activity_products")
    op.drop_column("silk_type_activity_products", "legacy_stage_id")

    figs_stage_fk = _fk_name(bind, "figs", "stage_id")
    if figs_stage_fk:
        op.drop_constraint(figs_stage_fk, "figs", type_="foreignkey")
    op.drop_column("figs", "stage_id")

    yields_stage_fk = _fk_name(bind, "yields", "stage_id")
    if yields_stage_fk:
        op.drop_constraint(yields_stage_fk, "yields", type_="foreignkey")
    yields_stage_idx = _index_name(bind, "yields", "stage_id")
    if yields_stage_idx:
        op.drop_index(yields_stage_idx, table_name="yields")
    op.drop_column("yields", "stage_id")

    trainings_stage_fk = _fk_name(bind, "trainings", "stage_id")
    if trainings_stage_fk:
        op.drop_constraint(trainings_stage_fk, "trainings", type_="foreignkey")
    op.drop_column("trainings", "stage_id")

    schemes_sector_fk = _fk_name(bind, "schemes", "sector_id")
    if schemes_sector_fk:
        op.drop_constraint(schemes_sector_fk, "schemes", type_="foreignkey")
    op.drop_column("schemes", "sector_id")

    schemes_stage_fk = _fk_name(bind, "schemes", "stage_id")
    if schemes_stage_fk:
        op.drop_constraint(schemes_stage_fk, "schemes", type_="foreignkey")
    op.drop_column("schemes", "stage_id")

    op.drop_column("farmers", "stage_ids")
    op.drop_column("farmers", "primary_stage_id")

    # dropping the tables also drops their own indexes/constraints (e.g. stages.sector_id's FK,
    # ix_stages_sector_id, ix_sectors_sector_name) automatically.
    op.drop_table("stages")
    op.drop_table("sectors")


def downgrade() -> None:
    raise NotImplementedError(
        "This migration consolidates Sector/Stage into SilkType/Activity/Product and drops the "
        "legacy tables outright; restoring them would require re-deriving stage_id/sector_id from "
        "stap_id, which is lossy (one STAP row's legacy_stage_id may map from many rows) and is not "
        "supported. Restore from a pre-migration backup instead."
    )
