"""FIG request DTOs."""
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
from .assets import AssetDetailIn

__all__ = ["FigIn", "FigMemberIn", "PresidentSetIn", "FigUpdateIn"]


class FigIn(BaseModel):
    fig_name: str
    stap_id: str
    seri_circle_id: str
    district_id: str
    formation_date: date
    village_name: Optional[str] = ""
    panchayat_name: Optional[str] = ""
    post_office: Optional[str] = ""
    police_station: Optional[str] = ""
    pin_code: Optional[str] = ""
    address: Optional[str] = ""
    contact_no: Optional[str] = ""
    meeting_venue: Optional[str] = ""
    remarks: Optional[str] = ""
    member_ids: list[str] = []
    assets: List[AssetDetailIn] = Field(default_factory=list)


class FigMemberIn(BaseModel):
    fig_id: str
    farmer_id: str
    role: str = "Member"


class PresidentSetIn(BaseModel):
    fig_id: str
    farmer_id: str


class FigUpdateIn(BaseModel):
    fig_name: Optional[str] = None
    stap_id: Optional[str] = None
    seri_circle_id: Optional[str] = None
    formation_date: Optional[date] = None
    village_name: Optional[str] = None
    panchayat_name: Optional[str] = None
    post_office: Optional[str] = None
    police_station: Optional[str] = None
    pin_code: Optional[str] = None
    address: Optional[str] = None
    contact_no: Optional[str] = None
    meeting_venue: Optional[str] = None
    remarks: Optional[str] = None
