"""Auth: login, refresh, me — JWT bearer + refresh tokens + rate-limited."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import jwt
from app.core.db import get_session
from app.core.security import (
    verify_password, hash_password, create_access_token, create_refresh_token, decode_refresh,
)
from app.core.limiter import limiter
from app.core.config import settings
from app.core.scope import assigned_district_ids
from app.core.deps import get_current_user
from app.models import User, Designation
from app.schemas import LoginIn, RefreshIn, TokenOut, ChangePasswordIn

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_dict(u: User, db: Optional[Session] = None) -> dict:
    return {"id": u.id, "mobile_no": u.mobile_no, "role": u.role, "name": u.name,
            "district_id": u.district_id, "fig_id": u.fig_id, "farmer_id": u.farmer_id,
            # Lets the UI hide "Change Password" for the super admin rather than
            # offering a button that always 403s.
            "is_protected": u.mobile_no == settings.PROTECTED_ADMIN_MOBILE,
            # All districts this admin covers, primary first. The UI shows a switcher when
            # there is more than one.
            "district_ids": assigned_district_ids(db, u) if db is not None else (
                [u.district_id] if u.district_id else []),
            "designation_name": (
                db.query(Designation.designation_name)
                  .filter(Designation.id == u.designation_id).scalar()
                if db is not None and u.designation_id else None)}


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, body: LoginIn, db: Session = Depends(get_session)):
    # No account lockout by design: a locked-out district officer costs more than a
    # throttled guesser. Brute force is held back by the per-IP rate limit above
    # (RATE_LIMIT_LOGIN) — which only reports the real client IP because the backend
    # runs uvicorn with --proxy-headers behind the reverse proxy.
    user = db.query(User).filter(User.mobile_no == body.mobile_no, User.is_active).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid mobile number or password")
    scope = {"district_id": user.district_id, "fig_id": user.fig_id}
    access = create_access_token(user.id, user.role, scope)
    refresh = create_refresh_token(user.id)
    return TokenOut(access_token=access, refresh_token=refresh, user=_user_dict(user, db))


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_session)):
    try:
        payload = decode_refresh(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token expired")
    except Exception:
        raise HTTPException(401, "Invalid refresh token")
    user = db.query(User).filter(User.id == payload["sub"], User.is_active).first()
    if not user:
        raise HTTPException(401, "User not found")
    scope = {"district_id": user.district_id, "fig_id": user.fig_id}
    access = create_access_token(user.id, user.role, scope)
    new_refresh = create_refresh_token(user.id)
    return TokenOut(access_token=access, refresh_token=new_refresh, user=_user_dict(user, db))


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _user_dict(user, db)


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_session)):
    if user.mobile_no == settings.PROTECTED_ADMIN_MOBILE:
        raise HTTPException(403, "The super admin password cannot be changed")
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    if body.new_password == body.old_password:
        raise HTTPException(400, "New password must be different from the current password")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
