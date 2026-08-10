"""Meeting submission DTO."""
from typing import List, Optional, Any, Dict
from datetime import date
from pydantic import BaseModel

__all__ = [
    "MeetingIn", "MeetingCorrectionIn", "MeetingCorrectionRejectIn",
    "FarmerSubmissionIn", "FarmerSubmissionCorrectionIn", "FarmerDraftIn",
]


class MeetingIn(BaseModel):
    fig_id: str
    meeting_title: str
    meeting_date: date
    meeting_time: Optional[str] = ""
    meeting_venue: str
    meeting_details: Optional[str] = ""
    minutes_path: Optional[str] = None
    next_meeting_date: Optional[date] = None
    attendance: List[Dict[str, Any]]
    entries: List[Dict[str, Any]]


class MeetingCorrectionIn(BaseModel):
    """Same shape as MeetingIn minus fig_id — the meeting (and its FIG) is implied by the URL."""
    meeting_title: str
    meeting_date: date
    meeting_time: Optional[str] = ""
    meeting_venue: str
    meeting_details: Optional[str] = ""
    minutes_path: Optional[str] = None
    next_meeting_date: Optional[date] = None
    attendance: List[Dict[str, Any]]
    entries: List[Dict[str, Any]]


class MeetingCorrectionRejectIn(BaseModel):
    rejection_reason: str


class FarmerSubmissionIn(BaseModel):
    submission_month: str
    entries: List[Dict[str, Any]]


class FarmerSubmissionCorrectionIn(BaseModel):
    """Same shape as FarmerSubmissionIn minus submission_month — the submission (and its
    month) is implied by the URL; only the entries can be resubmitted for review."""
    entries: List[Dict[str, Any]]


class FarmerDraftIn(BaseModel):
    """A FIG-member farmer's own private staging entries for the current month — never
    validated/applied until the FIG President reviews and submits the real Meeting."""
    draft_month: str
    entries: List[Dict[str, Any]]
