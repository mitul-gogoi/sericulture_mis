"""Notification send DTOs."""
from typing import List, Optional
from pydantic import BaseModel, Field

__all__ = ["NotificationIn", "NotificationReplyIn"]


class NotificationIn(BaseModel):
    title: str
    details: str
    attachment_path: Optional[str] = None
    recipient_type: str
    recipient_ids: List[str] = Field(default_factory=list)


class NotificationReplyIn(BaseModel):
    details: str
    attachment_path: Optional[str] = None
