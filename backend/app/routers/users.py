"""Users — SA-only creation of DA accounts + SA edit / activate-deactivate for any account."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.security import hash_password
from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.models import User
from app.schemas import DistrictAdminCreateIn
from app.core.scope import active_district, assigned_district_ids, set_assigned_districts

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
    # Full replacement set for a District Admin; first entry becomes the primary.
    district_ids: Optional[List[str]] = None


class ActiveToggleIn(BaseModel):
    is_active: bool


def is_protected_admin(u: User) -> bool:
    """The permanent super-admin: cannot be edited, deactivated, or have its password
    changed through the API. Identified by mobile number, which is not a secret."""
    return u.mobile_no == settings.PROTECTED_ADMIN_MOBILE


def _serialize(u: User, db: Optional[Session] = None) -> dict:
    d = u.model_dump()
    d.pop("password_hash", None)
    d["is_protected"] = is_protected_admin(u)
    # Every district this admin covers, primary first. Drives the district switcher and
    # the "additional charge" column on the District Admins page.
    d["district_ids"] = assigned_district_ids(db, u) if db is not None else (
        [u.district_id] if u.district_id else [])
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
    return _serialize(u, db)


@router.post("/district-admin")
def create_district_admin(body: DistrictAdminCreateIn,
                          user: User = Depends(require_roles("STATE_ADMIN")),
                          db: Session = Depends(get_session)):
    if db.query(User).filter(User.mobile_no == body.mobile_no).first():
        raise HTTPException(400, "Mobile already exists")
    # A district may have more than one active admin: officers routinely hold additional
    # charge of a neighbouring district, so the old one-admin-per-district rule is gone.
    wanted = list(body.district_ids) or ([body.district_id] if body.district_id else [])
    if not wanted:
        raise HTTPException(400, "At least one district is required")
    u = User(mobile_no=body.mobile_no, name=body.name,
             password_hash=hash_password(body.password), role="DISTRICT_ADMIN",
             district_id=wanted[0])
    db.add(u)
    db.flush()
    set_assigned_districts(db, u, wanted)
    db.commit()
    db.refresh(u)
    return _serialize(u, db)


@router.get("")
def list_users(role: Optional[str] = None, all: bool = False,
               user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(User)
    if not all:
        q = q.filter(User.is_active)
    if role:
        q = q.filter(User.role == role)
    if user.role == "DISTRICT_ADMIN":
        q = q.filter(User.district_id == active_district(user))
    rows = q.order_by(User.created_at.desc()).all()
    return [_serialize(u, db) for u in rows]


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
    # A district may have several active admins (additional charge), so there is no
    # conflict check here any more.
    if body.district_ids is not None:
        if target.role == "DISTRICT_ADMIN" and not body.district_ids:
            raise HTTPException(400, "A District Admin needs at least one district")
        set_assigned_districts(db, target, body.district_ids)
    elif body.district_id is not None:
        target.district_id = body.district_id or None
        if target.role == "DISTRICT_ADMIN" and body.district_id:
            set_assigned_districts(db, target, [body.district_id])
    db.commit()
    db.refresh(target)
    return _serialize(target, db)


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
    # Re-activating a DA no longer conflicts: a district may have several admins.
    target.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": target.is_active}
