"""Farmer model."""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON
from ._common import _uuid, _now

__all__ = ["Farmer"]


class Farmer(SQLModel, table=True):
    __tablename__ = "farmers"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_code: str = Field(unique=True, max_length=30, index=True)
    first_name: str = Field(max_length=80)
    middle_name: Optional[str] = Field(default=None, max_length=80)
    last_name: str = Field(max_length=80)
    gender: str = Field(max_length=10)
    date_of_birth: Optional[date] = None
    mobile_no: str = Field(unique=True, index=True, max_length=15)
    # The raw 12 digits are never stored — see app/core/aadhaar.py. `aadhaar_hash` carries
    # the index because it is what the duplicate-Aadhaar check now queries on. Neither the
    # hash nor the ciphertext may be serialized to a client.
    aadhaar_last4: Optional[str] = Field(default=None, max_length=4)
    aadhaar_hash: Optional[str] = Field(default=None, max_length=64, index=True)
    aadhaar_enc: Optional[str] = Field(default=None, max_length=255)
    pan_no: Optional[str] = Field(default=None, max_length=15)
    photo_path: Optional[str] = Field(default=None, max_length=500)
    is_pwd: bool = False
    education_level_id: Optional[str] = Field(default=None, foreign_key="education_levels.id")
    farmer_type: Optional[str] = Field(default=None, max_length=30)
    experience_years: int = 0
    caste_id: Optional[str] = Field(default=None, foreign_key="castes.id")
    religion_id: Optional[str] = Field(default=None, foreign_key="religions.id")
    family_member_male: int = 0
    family_member_female: int = 0
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    village_name: str = Field(max_length=120)
    gaon_panchayat: Optional[str] = Field(default=None, max_length=120)
    development_block: Optional[str] = Field(default=None, max_length=120)
    post_office: Optional[str] = Field(default=None, max_length=120)
    pin_code: Optional[str] = Field(default=None, max_length=10)
    stap_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    primary_stap_id: Optional[str] = Field(default=None)
    experience_activity_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    account_number: Optional[str] = Field(default=None, max_length=30)
    bank_name: Optional[str] = Field(default=None, max_length=120)
    branch_name: Optional[str] = Field(default=None, max_length=120)
    ifsc_code: Optional[str] = Field(default=None, max_length=15)
    passbook_path: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    auto_inactivated: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
