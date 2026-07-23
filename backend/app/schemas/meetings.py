"""Meeting submission DTO."""
from typing import List, Optional, Any, Dict
from datetime import date
from pydantic import BaseModel

__all__ = ["MeetingIn"]


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
