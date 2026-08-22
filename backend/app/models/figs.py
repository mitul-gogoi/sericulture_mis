"""FIG (Farmer Interest Group) and membership models."""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text, UniqueConstraint
from ._common import _uuid, _now

__all__ = ["Fig", "FigMember", "FigActivity"]


class Fig(SQLModel, table=True):
    __tablename__ = "figs"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fig_code: str = Field(unique=True, max_length=30, index=True)
    fig_name: str = Field(max_length=160)
    # A FIG is always built around exactly ONE silk type, but may run several activities
    # within it (see FigActivity). This replaces the old single stap_id: nearly every
    # consumer joined through STAP only to reach the silk type, so holding it directly makes
    # those queries shorter as well as allowing more than one activity.
    silk_type_id: str = Field(foreign_key="silk_types.id", index=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    formation_date: date
    village_name: Optional[str] = Field(default=None, max_length=120)
    panchayat_name: Optional[str] = Field(default=None, max_length=120)
    post_office: Optional[str] = Field(default=None, max_length=120)
    pin_code: Optional[str] = Field(default=None, max_length=10)
    address: Optional[str] = Field(default=None, sa_column=Column(Text))
    # Registration paperwork, captured in step 2 of FIG registration (not at create time —
    # the FIG must exist first so the upload folder can be named after its real code).
    minutes_path: Optional[str] = Field(default=None, max_length=500)
    group_photo_path: Optional[str] = Field(default=None, max_length=500)
    contact_no: Optional[str] = Field(default=None, max_length=15)
    meeting_venue: Optional[str] = Field(default=None, max_length=200)
    remarks: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class FigMember(SQLModel, table=True):
    __tablename__ = "fig_members"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    joining_date: datetime = Field(default_factory=_now)
    exit_date: Optional[datetime] = None
    role: str = Field(default="Member", max_length=20)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class FigActivity(SQLModel, table=True):
    """The activities a FIG runs, all within its single silk type.

    A join table rather than a JSON column on Fig: scheme targeting and the reports filter on
    it, and Farmer.stap_ids is the cautionary example here -- it is `json`, not `jsonb`, so
    every consumer has to resolve it in Python.
    """
    __tablename__ = "fig_activities"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    activity_id: str = Field(foreign_key="activities.id", index=True)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("fig_id", "activity_id", name="uq_fig_activity"),)
