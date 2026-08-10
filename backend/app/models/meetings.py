"""Meeting, attendance, yield/byproduct/input production records, and stock snapshots."""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import UniqueConstraint, Index, Text
from ._common import _uuid, _now

__all__ = [
    "Meeting", "Attendance", "Yield_", "ByproductEntry", "YieldInputEntry", "Stock", "MeetingCorrection",
    "FarmerSubmission", "FarmerSubmissionCorrection", "FarmerDraftEntry",
]


class Meeting(SQLModel, table=True):
    __tablename__ = "meetings"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    meeting_title: str = Field(max_length=200)
    meeting_date: date
    meeting_time: Optional[str] = Field(default=None, max_length=10)
    meeting_venue: str = Field(max_length=200)
    meeting_details: Optional[str] = Field(default=None, sa_column=Column(Text))
    minutes_path: Optional[str] = Field(default=None, max_length=500)
    next_meeting_date: Optional[date] = None
    meeting_month: str = Field(max_length=7, index=True)  # YYYY-MM
    submission_status: str = Field(default="Submitted", max_length=20)
    submitted_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("fig_id", "meeting_month"),)


class Attendance(SQLModel, table=True):
    __tablename__ = "attendance"
    id: str = Field(default_factory=_uuid, primary_key=True)
    meeting_id: str = Field(foreign_key="meetings.id", index=True)
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id")
    farmer_id: str = Field(foreign_key="farmers.id")
    is_present: bool = True
    created_at: datetime = Field(default_factory=_now)


class Yield_(SQLModel, table=True):
    __tablename__ = "yields"
    id: str = Field(default_factory=_uuid, primary_key=True)
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id", index=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    stap_id: str = Field(foreign_key="silk_type_activity_products.id", index=True)
    activity_id: Optional[str] = Field(default=None, foreign_key="activities.id", index=True)
    product_id: Optional[str] = Field(default=None, foreign_key="products.id", index=True)
    meeting_id: Optional[str] = Field(default=None, foreign_key="meetings.id")
    farmer_submission_id: Optional[str] = Field(default=None, foreign_key="farmer_submissions.id")
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    yield_month: str = Field(max_length=7, index=True)
    is_primary_stage: bool = True
    planned_yield: float = 0
    actual_yield: float = 0
    next_month_plan: float = 0
    stock_balance: float = 0
    sold_quantity: float = 0
    sold_rate: float = 0
    earning: float = 0
    loss_reason_id: Optional[str] = Field(default=None, foreign_key="loss_reasons.id", index=True)
    remarks: Optional[str] = Field(default=None, max_length=500)
    entered_by_role: str = Field(default="FIG_PRESIDENT", max_length=20)
    submission_status: str = Field(default="Submitted", max_length=20)
    submitted_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (
        UniqueConstraint("farmer_id", "stap_id", "yield_month"),
        Index("ix_yields_stap_month_fig", "stap_id", "yield_month", "fig_id"),
    )


class ByproductEntry(SQLModel, table=True):
    __tablename__ = "byproduct_entries"
    id: str = Field(default_factory=_uuid, primary_key=True)
    parent_yield_id: str = Field(foreign_key="yields.id", index=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    yield_month: str = Field(max_length=7, index=True)
    unit_of_measure: str = Field(max_length=30)
    quantity: float = 0
    planned_quantity: float = 0
    next_month_plan: float = 0
    stock_balance: float = 0
    sold_quantity: float = 0
    sold_rate: float = 0
    earning: float = 0
    loss_reason_id: Optional[str] = Field(default=None, foreign_key="loss_reasons.id", index=True)
    remarks: Optional[str] = Field(default=None, max_length=500)
    submission_status: str = Field(default="Submitted", max_length=20)
    submitted_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (
        UniqueConstraint("parent_yield_id", "product_id"),
        Index("ix_byproduct_farmer_month", "farmer_id", "yield_month"),
    )


class YieldInputEntry(SQLModel, table=True):
    __tablename__ = "yield_input_entries"
    id: str = Field(default_factory=_uuid, primary_key=True)
    parent_yield_id: str = Field(foreign_key="yields.id", index=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    yield_month: str = Field(max_length=7, index=True)
    unit_of_measure: str = Field(max_length=30)
    quantity: float = 0
    source_type_id: str = Field(foreign_key="input_source_types.id", index=True)
    scheme_id: Optional[str] = Field(default=None, foreign_key="schemes.id", index=True)
    remarks: Optional[str] = Field(default=None, max_length=500)
    submission_status: str = Field(default="Submitted", max_length=20)
    submitted_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (
        UniqueConstraint("parent_yield_id", "product_id"),
        Index("ix_yield_input_farmer_month", "farmer_id", "yield_month"),
    )


class Stock(SQLModel, table=True):
    __tablename__ = "stock"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    seri_circle_id: str = Field(foreign_key="sericulture_circles.id", index=True)
    opening_balance: float = 0
    closing_balance: float = 0
    is_perishable: bool = False
    last_produced_month: Optional[str] = Field(default=None, max_length=7)
    last_entry_at: datetime = Field(default_factory=_now)
    last_source_yield_id: Optional[str] = Field(default=None, foreign_key="yields.id")
    last_source_byproduct_id: Optional[str] = Field(default=None, foreign_key="byproduct_entries.id")
    updated_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("farmer_id", "product_id"),)


class MeetingCorrection(SQLModel, table=True):
    """A FIG President's proposed edit to an already-submitted meeting. The payload is stored
    verbatim (same shape as the original submission body) and never touches live Meeting/Yield_/
    ByproductEntry/YieldInputEntry/Stock rows until a District/State Admin accepts it — see
    routers/meetings.py's accept endpoint for the reconciliation logic."""
    __tablename__ = "meeting_corrections"
    id: str = Field(default_factory=_uuid, primary_key=True)
    meeting_id: str = Field(foreign_key="meetings.id", index=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    submitted_by_user_id: str = Field(foreign_key="users.id")
    submitted_at: datetime = Field(default_factory=_now)
    payload: dict = Field(sa_column=Column(JSON))
    status: str = Field(default="PENDING", max_length=20)  # PENDING | ACCEPTED | REJECTED
    reviewed_by_user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(Text))


class FarmerSubmission(SQLModel, table=True):
    """A solo (non-FIG) farmer's own monthly production/stock submission — the individual-farmer
    analog of Meeting, minus everything meeting-specific (no venue/attendance/minutes; there is no
    'meeting', just this farmer's own entries for the month)."""
    __tablename__ = "farmer_submissions"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    submission_code: str = Field(max_length=30, unique=True, index=True)  # SERI-SUB-NNNNNN
    submission_month: str = Field(max_length=7, index=True)
    submitted_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("farmer_id", "submission_month"),)


class FarmerSubmissionCorrection(SQLModel, table=True):
    """Mirrors MeetingCorrection exactly, one level down — a solo farmer's proposed resubmission,
    approved/rejected by their District Admin (not State Admin — a deliberately different approver
    than the FIG-meeting-correction workflow)."""
    __tablename__ = "farmer_submission_corrections"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_submission_id: str = Field(foreign_key="farmer_submissions.id", index=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    submitted_by_user_id: str = Field(foreign_key="users.id")
    submitted_at: datetime = Field(default_factory=_now)
    payload: dict = Field(sa_column=Column(JSON))
    status: str = Field(default="PENDING", max_length=20)
    reviewed_by_user_id: Optional[str] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(Text))


class FarmerDraftEntry(SQLModel, table=True):
    """A FIG-member farmer's own, private, not-yet-visible entries for the current month — pure
    staging, consumed (deleted) once the FIG President finalizes the real Meeting for that
    farmer's FIG+month. One row per farmer per month; payload is a list of entry dicts in the
    exact same shape as MeetingIn.entries (one dict per stap_id the farmer has data for)."""
    __tablename__ = "farmer_draft_entries"
    id: str = Field(default_factory=_uuid, primary_key=True)
    farmer_id: str = Field(foreign_key="farmers.id", index=True)
    fig_id: str = Field(foreign_key="figs.id", index=True)
    draft_month: str = Field(max_length=7, index=True)
    payload: dict = Field(sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("farmer_id", "draft_month"),)
