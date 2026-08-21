"""User accounts (State Admin / District Admin / FIG President)."""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from ._common import _uuid, _now

__all__ = ["User"]


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=_uuid, primary_key=True)
    mobile_no: str = Field(unique=True, index=True, max_length=15)
    password_hash: str = Field(max_length=200)
    role: str = Field(max_length=20)  # STATE_ADMIN | DISTRICT_ADMIN | FIG_PRESIDENT | FARMER
    name: Optional[str] = Field(default=None, max_length=120)
    district_id: Optional[str] = Field(default=None, foreign_key="districts.id")
    fig_id: Optional[str] = Field(default=None, foreign_key="figs.id")
    farmer_id: Optional[str] = Field(default=None)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
