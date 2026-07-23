"""Auth: login, refresh, me — JWT bearer + refresh tokens + rate-limited."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import jwt
from app.core.db import get_session
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, decode_refresh,
)
from app.core.limiter import limiter
from app.core.config import settings
from app.core.deps import get_current_user
from app.models import User
from app.schemas import LoginIn, RefreshIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def _user_dict(u: User) -> dict:
    return {"id": u.id, "mobile_no": u.mobile_no, "role": u.role, "name": u.name,
            "district_id": u.district_id, "fig_id": u.fig_id, "farmer_id": u.farmer_id}


@router.post("/login", response_model=TokenOut)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, body: LoginIn, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.mobile_no == body.mobile_no, User.is_active).first()
    if not user:
        raise HTTPException(401, "Invalid mobile number or password")
    if user.lock_until and user.lock_until > datetime.now(timezone.utc):
        raise HTTPException(429, "Account locked due to repeated failed attempts. Try again later.")
    if not verify_password(body.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_ATTEMPTS:
            user.lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
            user.failed_attempts = 0
        db.commit()
        raise HTTPException(401, "Invalid mobile number or password")
    # success
    user.failed_attempts = 0
    user.lock_until = None
    db.commit()
    scope = {"district_id": user.district_id, "fig_id": user.fig_id}
    access = create_access_token(user.id, user.role, scope)
    refresh = create_refresh_token(user.id)
    return TokenOut(access_token=access, refresh_token=refresh, user=_user_dict(user))


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
    return TokenOut(access_token=access, refresh_token=new_refresh, user=_user_dict(user))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_dict(user)
