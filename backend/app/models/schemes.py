"""Government schemes, district budget allocations, and beneficiary registrations."""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import UniqueConstraint, Text
from ._common import _uuid, _now

__all__ = ["Scheme", "Allocation", "Beneficiary"]


class Scheme(SQLModel, table=True):
    __tablename__ = "schemes"
    id: str = Field(default_factory=_uuid, primary_key=True)
    scheme_name: str = Field(unique=True, max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    silk_type_id: Optional[str] = Field(default=None, foreign_key="silk_types.id")
    activity_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    eligible_farmer_type: str = Field(default="All", max_length=50)
    total_budget_rs: float = 0
    disbursement_type: str = Field(default="DBT", max_length=20)
    support_type: str = Field(default="Cash", max_length=20)  # Cash | Kind | Training
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    # ---- Targeting (State Admin sets these; District Admin selects beneficiaries within them) ----
    beneficiary_kind: str = Field(default="FARMER", max_length=10)  # FARMER | FIG
    target_all_districts: bool = True
    target_district_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    target_silk_type_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # empty = all
    target_genders: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # empty = all
    target_farmer_types: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # empty = all
    # FARMER-kind only — FIGs have no individual-level demographic attributes.
    target_caste_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # empty = all
    target_religion_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # empty = all
    target_education_level_ids: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # empty = all
    target_pwd_only: bool = False
    # asset auto-granted to each beneficiary on registration — feeds the useful-life cooldown check
    grants_asset_type_id: Optional[str] = Field(default=None, foreign_key="asset_types.id")

    # ---- Lifecycle ----
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    notified_at: Optional[datetime] = None


class Allocation(SQLModel, table=True):
    __tablename__ = "allocations"
    id: str = Field(default_factory=_uuid, primary_key=True)
    scheme_id: str = Field(foreign_key="schemes.id", index=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    allocated_amount_rs: float = 0
    utilised: float = 0
    remaining: float = 0
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("scheme_id", "district_id"),)


class Beneficiary(SQLModel, table=True):
    __tablename__ = "beneficiaries"
    id: str = Field(default_factory=_uuid, primary_key=True)
    scheme_id: str = Field(foreign_key="schemes.id", index=True)
    # Exactly one of farmer_id/fig_id is set, matching the parent Scheme's beneficiary_kind.
    farmer_id: Optional[str] = Field(default=None, foreign_key="farmers.id", index=True)
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id", index=True)
    beneficiary_type: str = Field(default="FARMER", max_length=10)  # FARMER | FIG
    district_id: str = Field(foreign_key="districts.id", index=True)
    benefit_amount: float = 0
    benefit_material: Optional[str] = Field(default=None, max_length=200)
    disbursement_date: Optional[date] = None
    remarks: Optional[str] = Field(default=None, max_length=500)
    # Set only when the asset-cooldown check flagged this beneficiary as ineligible and the
    # District Admin explicitly overrode it — an audit trail, not a validation bypass.
    cooldown_override_reason: Optional[str] = Field(default=None, max_length=500)
    # Nomination/approval gate — only meaningful for Training-support-type schemes. Defaults to
    # already-APPROVED so every pre-existing row and every Cash/Kind registration keeps today's
    # exact immediate-and-final behavior; only Training nominations start PENDING_APPROVAL.
    status: str = Field(default="APPROVED", max_length=20)  # PENDING_APPROVAL | APPROVED | REJECTED
    created_by_user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    approved_by_user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=_now)
