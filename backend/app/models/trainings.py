"""Training requests/approvals, training-day attendance, and issued certificates."""
from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import UniqueConstraint, Text
from ._common import _uuid, _now

__all__ = ["Training", "TrainingAttendance", "TrainingCertificate"]


class Training(SQLModel, table=True):
    __tablename__ = "trainings"
    id: str = Field(default_factory=_uuid, primary_key=True)
    topic: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    activity_id: Optional[str] = Field(default=None, foreign_key="activities.id")
    # The Training-support-type Scheme funding this training, if any — resolves the expected
    # attendee roster as that scheme's APPROVED Beneficiary rows. Nullable: legacy/unfunded
    # training requests have no roster concept.
    scheme_id: Optional[str] = Field(default=None, foreign_key="schemes.id", index=True)
    proposed_from_date: date
    proposed_to_date: date
    proposed_venue: str = Field(max_length=200)
    estimated_participants: int = 0
    participant_names: Optional[str] = Field(default=None, sa_column=Column(Text))
    requesting_da_id: str = Field(foreign_key="users.id")
    district_id: str = Field(foreign_key="districts.id", index=True)
    status: str = Field(default="Pending", max_length=20)
    approval_from_date: Optional[date] = None
    approval_to_date: Optional[date] = None
    approved_venue: Optional[str] = Field(default=None, max_length=200)
    approval_remarks: Optional[str] = Field(default=None, sa_column=Column(Text))
    rejection_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    actual_from_date: Optional[date] = None
    actual_to_date: Optional[date] = None
    actual_venue: Optional[str] = Field(default=None, max_length=200)
    actual_participants: int = 0
    completion_report: Optional[str] = Field(default=None, sa_column=Column(Text))
    submitted_at: datetime = Field(default_factory=_now)
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TrainingAttendance(SQLModel, table=True):
    """Training-day attendance for a scheme-nominated, State-Admin-approved beneficiary.
    Deliberately not the existing `Attendance` model — that one is hard-tied to FIG monthly
    meetings via a required `meeting_id` FK and isn't reusable here (same pattern as
    ByproductEntry being separate from Yield_ rather than overloading one table)."""
    __tablename__ = "training_attendance"
    id: str = Field(default_factory=_uuid, primary_key=True)
    training_id: str = Field(foreign_key="trainings.id", index=True)
    beneficiary_id: str = Field(foreign_key="beneficiaries.id", index=True)
    is_present: bool = False
    marked_by_user_id: str = Field(foreign_key="users.id")
    marked_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("training_id", "beneficiary_id"),)


class TrainingCertificate(SQLModel, table=True):
    """One ACTIVE (non-revoked) certificate per (training, beneficiary) — only issuable for
    attendees marked present on a Completed training. Revoking one is a correction, not a
    delete — the app layer (not a DB constraint, since revoked rows must stay unique-exempt)
    re-issues a fresh row with a new certificate_number the next time certificates are
    generated for that training."""
    __tablename__ = "training_certificates"
    id: str = Field(default_factory=_uuid, primary_key=True)
    training_id: str = Field(foreign_key="trainings.id", index=True)
    beneficiary_id: str = Field(foreign_key="beneficiaries.id", index=True)
    certificate_number: str = Field(unique=True, max_length=30, index=True)
    issued_at: datetime = Field(default_factory=_now)
    issued_by_user_id: str = Field(foreign_key="users.id")
    pdf_path: Optional[str] = Field(default=None, max_length=500)
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = Field(default=None, max_length=500)
