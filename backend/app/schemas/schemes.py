"""Scheme, allocation, and beneficiary request DTOs."""
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field

__all__ = [
    "SchemeIn", "SchemeUpdateIn", "AllocationIn", "BeneficiaryIn", "BeneficiaryBulkItemIn",
    "BeneficiaryBulkIn", "BeneficiaryApprovalIn", "BeneficiaryApprovalBulkIn",
]


class SchemeIn(BaseModel):
    scheme_name: str
    description: Optional[str] = ""
    silk_type_id: Optional[str] = None
    activity_ids: List[str] = Field(default_factory=list)
    eligible_farmer_type: Optional[str] = "All"
    total_budget_rs: float = 0
    disbursement_type: str = "DBT"
    support_type: str = Field(default="Cash", pattern="^(Cash|Kind|Training)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # ---- Targeting ----
    beneficiary_kind: str = Field(default="FARMER", pattern="^(FARMER|FIG)$")
    target_all_districts: bool = True
    target_district_ids: List[str] = Field(default_factory=list)
    target_silk_type_ids: List[str] = Field(default_factory=list)
    target_genders: List[str] = Field(default_factory=list)
    target_farmer_types: List[str] = Field(default_factory=list)
    target_caste_ids: List[str] = Field(default_factory=list)
    target_religion_ids: List[str] = Field(default_factory=list)
    target_education_level_ids: List[str] = Field(default_factory=list)
    target_pwd_only: bool = False
    grants_asset_type_id: Optional[str] = None


class SchemeUpdateIn(BaseModel):
    scheme_name: Optional[str] = None
    description: Optional[str] = None
    silk_type_id: Optional[str] = None
    activity_ids: Optional[List[str]] = None
    eligible_farmer_type: Optional[str] = None
    total_budget_rs: Optional[float] = None
    disbursement_type: Optional[str] = None
    support_type: Optional[str] = Field(default=None, pattern="^(Cash|Kind|Training)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    beneficiary_kind: Optional[str] = Field(default=None, pattern="^(FARMER|FIG)$")
    target_all_districts: Optional[bool] = None
    target_district_ids: Optional[List[str]] = None
    target_silk_type_ids: Optional[List[str]] = None
    target_genders: Optional[List[str]] = None
    target_farmer_types: Optional[List[str]] = None
    target_caste_ids: Optional[List[str]] = None
    target_religion_ids: Optional[List[str]] = None
    target_education_level_ids: Optional[List[str]] = None
    target_pwd_only: Optional[bool] = None
    grants_asset_type_id: Optional[str] = None


class AllocationIn(BaseModel):
    scheme_id: str
    district_id: str
    allocated_amount_rs: float


class BeneficiaryIn(BaseModel):
    scheme_id: str
    beneficiary_type: str = Field(default="FARMER", pattern="^(FARMER|FIG)$")
    farmer_id: Optional[str] = None
    fig_id: Optional[str] = None
    benefit_amount: float = 0
    benefit_material: Optional[str] = ""
    disbursement_date: Optional[date] = None
    remarks: Optional[str] = ""
    cooldown_override_reason: Optional[str] = None


class BeneficiaryBulkItemIn(BaseModel):
    beneficiary_type: str = Field(pattern="^(FARMER|FIG)$")
    farmer_id: Optional[str] = None
    fig_id: Optional[str] = None
    benefit_amount: float = 0
    benefit_material: Optional[str] = ""
    disbursement_date: Optional[date] = None
    remarks: Optional[str] = ""
    cooldown_override_reason: Optional[str] = None


class BeneficiaryBulkIn(BaseModel):
    scheme_id: str
    items: List[BeneficiaryBulkItemIn] = Field(default_factory=list)


class BeneficiaryApprovalIn(BaseModel):
    rejection_reason: Optional[str] = None  # required by the router when rejecting


class BeneficiaryApprovalBulkIn(BaseModel):
    beneficiary_ids: List[str] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
