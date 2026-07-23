"""FIG (Farmer Interest Group) and membership models."""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text
from ._common import _uuid, _now

__all__ = ["Fig", "FigMember"]


class Fig(SQLModel, table=True):
    __tablename__ = "figs"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fig_code: str = Field(unique=True, max_length=30, index=True)
    fig_name: str = Field(max_length=160)
    stap_id: str = Field(foreign_key="silk_type_activity_products.id")
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    formation_date: date
    village_name: Optional[str] = Field(default=None, max_length=120)
    panchayat_name: Optional[str] = Field(default=None, max_length=120)
    post_office: Optional[str] = Field(default=None, max_length=120)
    police_station: Optional[str] = Field(default=None, max_length=120)
    pin_code: Optional[str] = Field(default=None, max_length=10)
    address: Optional[str] = Field(default=None, sa_column=Column(Text))
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
