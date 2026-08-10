"""Farmer self-capture for Land GPS + Asset GPS: any farmer (solo or FIG-member) can now
capture GPS for their own land parcels/assets. A solo farmer's capture submits directly,
live, through the existing POST /lands/gps / POST /assets/{id}/gps endpoints. A FIG-member
farmer's capture instead stages a private draft (land_gps_drafts / asset_gps_drafts) that
only becomes visible when their FIG President opens the existing per-row Capture GPS dialog
for that land/asset (as a pre-fill, editable, no separate review list) and actually submits
through the same real endpoints — at which point the draft is deleted.

This migration only adds the two new draft-staging tables; no existing columns change.

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-08-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'f9a0b1c2d3e4'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'land_gps_drafts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('farmer_id', sa.String(), nullable=False),
        sa.Column('land_id', sa.String(), nullable=False),
        sa.Column('fig_id', sa.String(), nullable=False),
        sa.Column('points', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id']),
        sa.ForeignKeyConstraint(['land_id'], ['lands.id']),
        sa.ForeignKeyConstraint(['fig_id'], ['figs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('land_id'),
    )
    op.create_index(op.f('ix_land_gps_drafts_farmer_id'), 'land_gps_drafts', ['farmer_id'])
    op.create_index(op.f('ix_land_gps_drafts_land_id'), 'land_gps_drafts', ['land_id'])
    op.create_index(op.f('ix_land_gps_drafts_fig_id'), 'land_gps_drafts', ['fig_id'])

    op.create_table(
        'asset_gps_drafts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('farmer_id', sa.String(), nullable=False),
        sa.Column('asset_id', sa.String(), nullable=False),
        sa.Column('fig_id', sa.String(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmers.id']),
        sa.ForeignKeyConstraint(['asset_id'], ['asset_instances.id']),
        sa.ForeignKeyConstraint(['fig_id'], ['figs.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id'),
    )
    op.create_index(op.f('ix_asset_gps_drafts_farmer_id'), 'asset_gps_drafts', ['farmer_id'])
    op.create_index(op.f('ix_asset_gps_drafts_asset_id'), 'asset_gps_drafts', ['asset_id'])
    op.create_index(op.f('ix_asset_gps_drafts_fig_id'), 'asset_gps_drafts', ['fig_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_asset_gps_drafts_fig_id'), table_name='asset_gps_drafts')
    op.drop_index(op.f('ix_asset_gps_drafts_asset_id'), table_name='asset_gps_drafts')
    op.drop_index(op.f('ix_asset_gps_drafts_farmer_id'), table_name='asset_gps_drafts')
    op.drop_table('asset_gps_drafts')

    op.drop_index(op.f('ix_land_gps_drafts_fig_id'), table_name='land_gps_drafts')
    op.drop_index(op.f('ix_land_gps_drafts_land_id'), table_name='land_gps_drafts')
    op.drop_index(op.f('ix_land_gps_drafts_farmer_id'), table_name='land_gps_drafts')
    op.drop_table('land_gps_drafts')
