"""remove activity group

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-19 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
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

    fk = _fk_name(bind, "activities", "activity_group_id")
    if fk:
        op.drop_constraint(fk, "activities", type_="foreignkey")
    idx = _index_name(bind, "activities", "activity_group_id")
    if idx:
        op.drop_index(idx, table_name="activities")
    uq = _unique_name(bind, "activities", ["silk_type_id", "activity_group_id", "step_no"])
    if uq:
        op.drop_constraint(uq, "activities", type_="unique")
    op.drop_column("activities", "activity_group_id")

    op.create_unique_constraint("uq_activities_silk_type_step", "activities", ["silk_type_id", "step_no"])

    op.drop_table("activity_groups")


def downgrade() -> None:
    raise NotImplementedError(
        "This migration drops the activity_groups table and Activity.activity_group_id outright; "
        "restoring them would require re-deriving group assignments that no longer exist anywhere. "
        "Restore from a pre-migration backup instead."
    )
