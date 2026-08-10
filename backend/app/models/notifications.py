"""Notifications, per-recipient read-state, and uploaded-file bookkeeping."""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Text
from ._common import _uuid, _now

__all__ = ["Notification", "NotificationRecipient", "FileRecord"]


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: str = Field(default_factory=_uuid, primary_key=True)
    notification_code: str = Field(max_length=30, index=True)
    title: str = Field(max_length=200)
    details: str = Field(sa_column=Column(Text))
    attachment_path: Optional[str] = Field(default=None, max_length=500)
    sent_by_user_id: str = Field(foreign_key="users.id")
    sent_by_role: str = Field(max_length=20)
    recipient_type: str = Field(max_length=30)
    in_reply_to_id: Optional[str] = Field(default=None, foreign_key="notifications.id")
    thread_id: str = Field(foreign_key="notifications.id", index=True)
    reply_seq: int = 0
    is_active: bool = True
    sent_at: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)


class NotificationRecipient(SQLModel, table=True):
    __tablename__ = "notification_recipients"
    id: str = Field(default_factory=_uuid, primary_key=True)
    notification_id: str = Field(foreign_key="notifications.id", index=True)
    recipient_user_id: str = Field(foreign_key="users.id", index=True)
    is_read: bool = False
    read_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class FileRecord(SQLModel, table=True):
    __tablename__ = "files"
    id: str = Field(default_factory=_uuid, primary_key=True)
    storage_path: str = Field(unique=True, max_length=500)
    original_filename: str = Field(max_length=300)
    content_type: str = Field(max_length=100)
    size: int = 0
    is_deleted: bool = False
    uploaded_by: str = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)
