"""Users — SA-only creation of DA accounts + SA edit / activate-deactivate for any account."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.security import hash_password
from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.models import User
from app.schemas import DistrictAdminCreateIn

router = APIRouter(prefix="/users", tags=["users"])


class StateAdminCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    mobile_no: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=6)


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    mobile_no: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    district_id: Optional[str] = None


class ActiveToggleIn(BaseModel):
    is_active: bool


def is_protected_admin(u: User) -> bool:
    """The permanent super-admin: cannot be edited, deactivated, or have its password
    changed through the API. Identified by mobile number, which is not a secret."""
    return u.mobile_no == settings.PROTECTED_ADMIN_MOBILE


def _serialize(u: User) -> dict:
    d = u.model_dump()
    d.pop("password_hash", None)
    d["is_protected"] = is_protected_admin(u)
    return d


@router.post("/state-admin")
def create_state_admin(body: StateAdminCreateIn,
                      user: User = Depends(require_roles("STATE_ADMIN")),
                      db: Session = Depends(get_session)):
    if db.query(User).filter(User.mobile_no == body.mobile_no).first():
        raise HTTPException(400, "Mobile already exists")
    u = User(mobile_no=body.mobile_no.strip(), name=body.name.strip(),
             password_hash=hash_password(body.password), role="STATE_ADMIN")
    db.add(u)
    db.commit()
    db.refresh(u)
    return _serialize(u)


@router.post("/district-admin")
def create_district_admin(body: DistrictAdminCreateIn,
                          user: User = Depends(require_roles("STATE_ADMIN")),
                          db: Session = Depends(get_session)):
    if db.query(User).filter(User.mobile_no == body.mobile_no).first():
        raise HTTPException(400, "Mobile already exists")
    if db.query(User).filter(User.role == "DISTRICT_ADMIN",
                              User.district_id == body.district_id,
                              User.is_active).first():
        raise HTTPException(400, "District already has an active admin")
    u = User(mobile_no=body.mobile_no, name=body.name,
             password_hash=hash_password(body.password), role="DISTRICT_ADMIN",
             district_id=body.district_id)
    db.add(u)
    db.commit()
    db.refresh(u)
    return _serialize(u)


@router.get("")
def list_users(role: Optional[str] = None, all: bool = False,
               user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(User)
    if not all:
        q = q.filter(User.is_active)
    if role:
        q = q.filter(User.role == role)
    if user.role == "DISTRICT_ADMIN":
        q = q.filter(User.district_id == user.district_id)
    rows = q.order_by(User.created_at.desc()).all()
    return [_serialize(u) for u in rows]


@router.patch("/{user_id}")
def update_user(user_id: str, body: UserUpdateIn,
                user: User = Depends(require_roles("STATE_ADMIN")),
                db: Session = Depends(get_session)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if is_protected_admin(target):
        raise HTTPException(403, "The super admin account cannot be modified")
    if body.mobile_no and body.mobile_no != target.mobile_no:
        if db.query(User).filter(User.mobile_no == body.mobile_no, User.id != user_id).first():
            raise HTTPException(400, "Mobile already exists")
        target.mobile_no = body.mobile_no.strip()
    if body.name is not None:
        target.name = body.name.strip() or None
    if body.password:
        target.password_hash = hash_password(body.password)
    if body.district_id is not None:
        # Enforce one-active-DA-per-district
        if target.role == "DISTRICT_ADMIN" and body.district_id and target.is_active:
            conflict = db.query(User).filter(User.role == "DISTRICT_ADMIN",
                                             User.district_id == body.district_id,
                                             User.is_active,
                                             User.id != user_id).first()
            if conflict:
                raise HTTPException(400, "District already has an active admin")
        target.district_id = body.district_id or None
    db.commit()
    db.refresh(target)
    return _serialize(target)


@router.patch("/{user_id}/active")
def toggle_user(user_id: str, body: ActiveToggleIn,
                user: User = Depends(require_roles("STATE_ADMIN")),
                db: Session = Depends(get_session)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    if is_protected_admin(target):
        raise HTTPException(403, "The super admin account cannot be deactivated")
    if target.id == user.id:
        raise HTTPException(400, "Cannot deactivate your own account")
    # Prevent deactivating the last active State Admin
    if not body.is_active and target.role == "STATE_ADMIN":
        remaining = db.query(User).filter(User.role == "STATE_ADMIN",
                                          User.is_active,
                                          User.id != user_id).count()
        if remaining == 0:
            raise HTTPException(400, "Cannot deactivate the last active State Admin")
    # Prevent re-activating a DA if district already has an active DA
    if body.is_active and target.role == "DISTRICT_ADMIN" and target.district_id:
        conflict = db.query(User).filter(User.role == "DISTRICT_ADMIN",
                                         User.district_id == target.district_id,
                                         User.is_active,
                                         User.id != user_id).first()
        if conflict:
            raise HTTPException(400, "Another active DA exists for this district")
    target.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": target.is_active}
