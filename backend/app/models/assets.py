"""Durable asset catalog, physical asset instances, and verification audit trail."""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON
from ._common import _uuid, _now

__all__ = ["AssetType", "AssetInstance", "AssetVerificationLog", "AssetGpsDraft"]


class AssetType(SQLModel, table=True):
    """Catalog of trackable durable assets (seeded). Deliberately excludes host-plant
    plantations (they are land — tracked in Land & GIS) and low-value consumables."""
    __tablename__ = "asset_types"
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str = Field(unique=True, max_length=120)
    category: str = Field(max_length=30)  # STRUCTURE | SHARED_INFRASTRUCTURE | EQUIPMENT
    silk_types: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # ["Eri", "Muga"] — empty = all
    ownership_level: str = Field(default="INDIVIDUAL", max_length=20)  # INDIVIDUAL | FIG | EITHER
    useful_life_years: int = 0
    typically_scheme_funded: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class AssetInstance(SQLModel, table=True):
    """A physical asset held by a farmer or a FIG. Single source of truth for the scheme
    useful-life cooldown check — every acquisition_mode counts equally toward it."""
    __tablename__ = "asset_instances"
    id: str = Field(default_factory=_uuid, primary_key=True)
    asset_type_id: str = Field(foreign_key="asset_types.id", index=True)
    owner_type: str = Field(max_length=10, index=True)  # FARMER | FIG
    owner_id: str = Field(index=True)  # farmers.id or figs.id — polymorphic, so no DB-level FK
    quantity: int = 1
    acquisition_date: Optional[date] = None
    # SCHEME_DISBURSEMENT | SELF_PROCURED | SELF_DECLARED_AT_REGISTRATION | LEGACY_SELF_DECLARED
    acquisition_mode: str = Field(max_length=40)
    # scheme_id/beneficiary_id are set only when acquisition_mode == "SCHEME_DISBURSEMENT" (enforced in the router)
    scheme_id: Optional[str] = Field(default=None, foreign_key="schemes.id", index=True)
    beneficiary_id: Optional[str] = Field(default=None, foreign_key="beneficiaries.id", index=True)
    status: str = Field(default="FUNCTIONAL", max_length=20)  # FUNCTIONAL | NON_FUNCTIONAL | UNDER_REPAIR | DECOMMISSIONED
    verification_status: str = Field(default="UNVERIFIED", max_length=20)  # UNVERIFIED | CIRCLE_VERIFIED | DISPUTED
    # FARMER_SELF_DECLARED | CIRCLE_OFFICER_RECOLLECTION | DOCUMENTARY_EVIDENCE_SEEN
    confidence: Optional[str] = Field(default=None, max_length=40)
    photo_path: Optional[str] = Field(default=None, max_length=500)  # evidence photo captured when the asset was added
    remarks: Optional[str] = Field(default=None, max_length=500)
    created_by_user_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_now)
    last_verified_by: Optional[str] = Field(default=None)
    last_verified_at: Optional[datetime] = None
    asset_code: str = Field(max_length=30, unique=True, index=True)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Not Submitted | Pending | Verified | Failed — mirrors Land.gps_verified exactly, captured by
    # FIG President (never at Register Farmer/FIG time) and approved/rejected by District Admin.
    gps_status: str = Field(default="Not Submitted", max_length=20)
    gps_failure_reason: Optional[str] = None
    gps_verified_by: Optional[str] = Field(default=None)
    gps_verified_at: Optional[datetime] = None


class AssetGpsDraft(SQLModel, table=True):
    """A FIG-member farmer's own, private, self-captured GPS point for an asset they own —
    invisible until the FIG President's Capture GPS dialog pulls it up as a pre-fill and
    actually submits via the real POST /assets/{id}/gps. One draft per asset; consumed
    (deleted) the moment that real submission succeeds."""
    __tablename__ = "asset_gps_drafts"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    asset_id: str = Field(foreign_key="asset_instances.id", index=True, unique=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    latitude: float
    longitude: float
    updated_at: datetime = Field(default_factory=_now)


class AssetVerificationLog(SQLModel, table=True):
    """Append-only audit trail — one row per physical verification visit."""
    __tablename__ = "asset_verification_logs"
    id: str = Field(default_factory=_uuid, primary_key=True)
    asset_instance_id: str = Field(foreign_key="asset_instances.id", index=True)
    checked_by_user_id: str
    checked_at: datetime = Field(default_factory=_now)
    result: str = Field(max_length=30)  # CONFIRMED_PRESENT | NOT_FOUND | PARTIALLY_FUNCTIONAL
    photo_url: Optional[str] = Field(default=None, max_length=500)
    remarks: Optional[str] = Field(default=None, max_length=500)
