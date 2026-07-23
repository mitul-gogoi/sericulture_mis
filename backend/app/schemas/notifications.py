"""Notification send DTO."""
from typing import List, Optional
from pydantic import BaseModel, Field

__all__ = ["NotificationIn"]


class NotificationIn(BaseModel):
    title: str
    details: str
    attachment_path: Optional[str] = None
    recipient_type: str
    recipient_ids: List[str] = Field(default_factory=list)
