"""Farmer land parcels + GPS/PostGIS boundary tracking."""
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON
from geoalchemy2 import Geometry
from ._common import _uuid, _now

__all__ = ["Land", "LandGpsDraft"]


class Land(SQLModel, table=True):
    __tablename__ = "lands"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    dag_no: Optional[str] = Field(default=None, max_length=40)
    patta_no: Optional[str] = Field(default=None, max_length=40)
    land_type: str = Field(default="Owned", max_length=30)
    land_area_sqm: Optional[float] = None
    land_area_bigha: Optional[float] = None
    land_area_hectare: Optional[float] = None
    gps_verified: str = Field(default="Not Submitted", max_length=20)
    gps_points: Optional[list] = Field(default=None, sa_column=Column(JSON))
    boundary: Optional[bytes] = Field(default=None, sa_column=Column(Geometry(geometry_type="POLYGON", srid=4326)))
    overlap_detected: bool = False
    overlapping_parcel_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    failure_reason: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class LandGpsDraft(SQLModel, table=True):
    """A FIG-member farmer's own, private, self-captured boundary points for a land parcel
    they own — invisible until the FIG President's GPS-submission dialog pulls it up as a
    pre-fill and actually submits via the real POST /lands/gps. One draft per parcel;
    consumed (deleted) the moment that real submission succeeds."""
    __tablename__ = "land_gps_drafts"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    land_id: str = Field(foreign_key="lands.id", index=True, unique=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    points: list = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_now)
