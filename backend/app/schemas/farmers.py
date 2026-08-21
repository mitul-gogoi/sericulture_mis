"""Farmer request DTOs."""
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field
from .lands import LandDetailIn
from .assets import AssetDetailIn

__all__ = ["FarmerIn", "FarmerUpdateIn", "FarmerPasswordResetIn"]


class FarmerIn(BaseModel):
    first_name: str
    middle_name: Optional[str] = ""
    last_name: str
    gender: str
    date_of_birth: Optional[date] = None
    mobile_no: str
    # WRITE-ONLY: the raw 12 digits go in here and are immediately converted to
    # aadhaar_last4/aadhaar_hash/aadhaar_enc. Responses never echo this field back —
    # they carry `aadhaar_masked` instead. Validated by app/core/aadhaar.normalize_aadhaar
    # in the router (not here) so create and update share one error message.
    aadhaar_no: Optional[str] = None
    pan_no: Optional[str] = None
    photo_path: Optional[str] = None
    is_pwd: bool = False
    education_level_id: Optional[str] = None
    farmer_type: Optional[str] = None
    experience_years: int = 0
    caste_id: Optional[str] = None
    religion_id: Optional[str] = None
    family_member_male: int = 0
    family_member_female: int = 0
    district_id: str
    seri_circle_id: str
    village_name: str
    gaon_panchayat: Optional[str] = ""
    development_block: Optional[str] = ""
    post_office: Optional[str] = ""
    pin_code: Optional[str] = ""
    stap_ids: List[str] = Field(default_factory=list)
    primary_stap_id: Optional[str] = None
    experience_activity_ids: List[str] = Field(default_factory=list)
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    passbook_path: Optional[str] = None
    lands: List[LandDetailIn] = Field(default_factory=list)
    assets: List[AssetDetailIn] = Field(default_factory=list)


class FarmerUpdateIn(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    mobile_no: Optional[str] = None
    aadhaar_no: Optional[str] = None
    pan_no: Optional[str] = None
    photo_path: Optional[str] = None
    is_pwd: Optional[bool] = None
    education_level_id: Optional[str] = None
    farmer_type: Optional[str] = None
    experience_years: Optional[int] = None
    caste_id: Optional[str] = None
    religion_id: Optional[str] = None
    family_member_male: Optional[int] = None
    family_member_female: Optional[int] = None
    seri_circle_id: Optional[str] = None
    village_name: Optional[str] = None
    gaon_panchayat: Optional[str] = None
    development_block: Optional[str] = None
    post_office: Optional[str] = None
    pin_code: Optional[str] = None
    stap_ids: Optional[List[str]] = None
    primary_stap_id: Optional[str] = None
    experience_activity_ids: Optional[List[str]] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    passbook_path: Optional[str] = None


class FarmerPasswordResetIn(BaseModel):
    password: str
