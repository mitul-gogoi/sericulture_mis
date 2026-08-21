"""FastAPI deps: get_current_user, require_roles."""
from typing import Optional
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .db import get_session
from .security import decode_access
from app.models import User
from .scope import DISTRICT_HEADER, resolve_active_district, set_active_district


def get_current_user(request: Request, db: Session = Depends(get_session)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = auth[7:]
    try:
        payload = decode_access(token)
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
    except Exception as e:
        from jwt import ExpiredSignatureError
        if isinstance(e, ExpiredSignatureError):
            raise HTTPException(401, "Token expired")
        raise HTTPException(401, "Invalid token")
    user = db.query(User).filter(User.id == payload["sub"], User.is_active).first()
    if not user:
        raise HTTPException(401, "User not found")
    # Resolve which district this request acts as, validating the header against what the
    # user actually holds. Stored in a request-scoped ContextVar rather than written onto
    # the User object, which is live in this session and must not be mutated -- see
    # core/scope.py.
    set_active_district(
        user, resolve_active_district(db, user, request.headers.get(DISTRICT_HEADER)))
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"Requires role: {roles}")
        return user
    return dep
