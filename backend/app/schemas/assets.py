"""Asset-instance request DTOs."""
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field

__all__ = ["AssetDetailIn", "AssetInstanceIn", "AssetInstanceUpdateIn", "AssetVerifyIn"]


class AssetDetailIn(BaseModel):
    """One self-declared asset row inside the Register Farmer dialog."""
    asset_type_id: str
    quantity: int = 1
    acquisition_year: Optional[int] = None


class AssetInstanceIn(BaseModel):
    asset_type_id: str
    owner_type: str = Field(pattern="^(FARMER|FIG)$")
    owner_id: str
    quantity: int = 1
    acquisition_date: Optional[date] = None
    # Scheme-disbursed assets are created automatically by the scheme module, never posted here.
    acquisition_mode: str = Field(default="LEGACY_SELF_DECLARED",
                                  pattern="^(SELF_PROCURED|SELF_DECLARED_AT_REGISTRATION|LEGACY_SELF_DECLARED)$")
    confidence: Optional[str] = Field(default=None,
                                      pattern="^(FARMER_SELF_DECLARED|CIRCLE_OFFICER_RECOLLECTION|DOCUMENTARY_EVIDENCE_SEEN)$")
    photo_path: Optional[str] = None
    remarks: Optional[str] = ""


class AssetInstanceUpdateIn(BaseModel):
    quantity: Optional[int] = None
    acquisition_date: Optional[date] = None
    status: Optional[str] = Field(default=None,
                                  pattern="^(FUNCTIONAL|NON_FUNCTIONAL|UNDER_REPAIR|DECOMMISSIONED)$")
    photo_path: Optional[str] = None
    remarks: Optional[str] = None


class AssetVerifyIn(BaseModel):
    result: str = Field(pattern="^(CONFIRMED_PRESENT|NOT_FOUND|PARTIALLY_FUNCTIONAL)$")
    photo_url: Optional[str] = None
    remarks: Optional[str] = ""
