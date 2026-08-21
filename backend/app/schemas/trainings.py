"""Training request/approval/attendance/certificate DTOs."""
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field

__all__ = [
    "TrainingRequestIn", "TrainingAttendanceItemIn", "TrainingAttendanceMarkIn",
    "CertificateRevokeIn", "TrainingApprovalIn", "TrainingCompletionIn",
]


class TrainingRequestIn(BaseModel):
    topic: str
    description: Optional[str] = ""
    activity_id: Optional[str] = None
    scheme_id: Optional[str] = None
    proposed_from_date: date
    proposed_to_date: date
    proposed_venue: str
    estimated_participants: int = 0
    participant_names: Optional[str] = ""
    # Which district the request is filed against. Optional: admins covering a single
    # district need not send it, and it falls back to the district they are acting as.
    district_id: Optional[str] = None


class TrainingAttendanceItemIn(BaseModel):
    beneficiary_id: str
    is_present: bool = False


class TrainingAttendanceMarkIn(BaseModel):
    items: List[TrainingAttendanceItemIn] = Field(default_factory=list)


class CertificateRevokeIn(BaseModel):
    reason: str


class TrainingApprovalIn(BaseModel):
    request_id: str
    decision: str
    approval_from_date: Optional[date] = None
    approval_to_date: Optional[date] = None
    approved_venue: Optional[str] = None
    approval_remarks: Optional[str] = ""
    rejection_reason: Optional[str] = ""


class TrainingCompletionIn(BaseModel):
    request_id: str
    actual_from_date: date
    actual_to_date: date
    actual_venue: str
    actual_participants: int
    completion_report: str
