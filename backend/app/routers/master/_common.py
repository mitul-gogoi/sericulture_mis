"""Shared helpers for the master-data router package."""
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import require_roles

_SA = require_roles("STATE_ADMIN")


class ActiveToggleIn(BaseModel):
    is_active: bool


def _q(db: Session, model, include_inactive: bool):
    q = db.query(model)
    if not include_inactive:
        q = q.filter(model.is_active)
    return q


def _get_or_404(db: Session, model, obj_id: str, label: str):
    row = db.query(model).filter(model.id == obj_id).first()
    if not row:
        raise HTTPException(404, f"{label} not found")
    return row
