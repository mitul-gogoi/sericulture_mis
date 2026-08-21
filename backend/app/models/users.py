"""User accounts (State Admin / District Admin / FIG President)."""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from ._common import _uuid, _now

__all__ = ["User", "UserDistrict"]


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


class UserDistrict(SQLModel, table=True):
    """Districts a District Admin is responsible for, including additional charge.

    A join table rather than a JSON array on User: this is filtered on essentially every
    request, so it has to be queryable in SQL and indexable. (Farmer.stap_ids is the
    cautionary example -- it is `json`, not `jsonb`, so every consumer resolves it in
    Python.)

    User.district_id remains the PRIMARY district: the default selection in the switcher
    and the fallback when no district is chosen. The invariant is that the primary always
    also has a row here; app/core/scope.py owns that.
    """
    __tablename__ = "user_districts"
    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("user_id", "district_id", name="uq_user_district"),)
