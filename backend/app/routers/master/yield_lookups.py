"""Loss-reason, input-source-category, and input-source-type master data — read (public)
+ State-Admin-only CRUD."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.db import get_session, commit_or_conflict, delete_or_conflict
from app.models import LossReason, InputSourceCategory, InputSourceType, User
from ._common import _SA, _q, _get_or_404, ActiveToggleIn

router = APIRouter()


@router.get("/loss-reasons")
def list_loss_reasons(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, LossReason, all).order_by(LossReason.reason_name).all()


@router.get("/input-source-categories")
def list_input_source_categories(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, InputSourceCategory, all).order_by(InputSourceCategory.category_name).all()


@router.get("/input-source-types")
def list_input_source_types(all: bool = False, db: Session = Depends(get_session)):
    rows = _q(db, InputSourceType, all).order_by(InputSourceType.source_name).all()
    categories = {c.id: c.category_name for c in db.query(InputSourceCategory).all()}
    out = []
    for r in rows:
        d = r.model_dump()
        d["category_name"] = categories.get(r.category_id)
        out.append(d)
    return out


class LossReasonIn(BaseModel):
    reason_name: str = Field(min_length=1, max_length=120)
    is_active: Optional[bool] = None


class InputSourceCategoryIn(BaseModel):
    category_name: str = Field(min_length=1, max_length=60)
    is_active: Optional[bool] = None


class InputSourceTypeIn(BaseModel):
    source_name: str = Field(min_length=1, max_length=60)
    category_id: str
    requires_scheme: bool = False
    is_own_source: bool = False
    is_active: Optional[bool] = None


# ---------- Loss Reasons ----------
@router.post("/loss-reasons")
def create_loss_reason(body: LossReasonIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    lr = LossReason(reason_name=body.reason_name.strip(),
                    is_active=True if body.is_active is None else body.is_active)
    db.add(lr)
    commit_or_conflict(db, "Loss reason already exists")
    db.refresh(lr)
    return lr


@router.patch("/loss-reasons/{loss_reason_id}")
def update_loss_reason(loss_reason_id: str, body: LossReasonIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    lr = _get_or_404(db, LossReason, loss_reason_id, "Loss reason")
    lr.reason_name = body.reason_name.strip()
    if body.is_active is not None:
        lr.is_active = body.is_active
    commit_or_conflict(db, "Loss reason already exists")
    db.refresh(lr)
    return lr


@router.patch("/loss-reasons/{loss_reason_id}/active")
def toggle_loss_reason(loss_reason_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    lr = _get_or_404(db, LossReason, loss_reason_id, "Loss reason")
    lr.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": lr.is_active}


@router.delete("/loss-reasons/{loss_reason_id}")
def delete_loss_reason(loss_reason_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    lr = _get_or_404(db, LossReason, loss_reason_id, "Loss reason")
    if lr.is_active:
        raise HTTPException(400, "Deactivate this loss reason before deleting it")
    delete_or_conflict(db, lr, "Cannot delete — one or more yield/byproduct entries still reference this loss reason")
    return {"ok": True}


# ---------- Input Source Categories ----------
@router.post("/input-source-categories")
def create_input_source_category(body: InputSourceCategoryIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    isc = InputSourceCategory(category_name=body.category_name.strip(),
                              is_active=True if body.is_active is None else body.is_active)
    db.add(isc)
    commit_or_conflict(db, "Input source category already exists")
    db.refresh(isc)
    return isc


@router.patch("/input-source-categories/{category_id}")
def update_input_source_category(category_id: str, body: InputSourceCategoryIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    isc = _get_or_404(db, InputSourceCategory, category_id, "Input source category")
    isc.category_name = body.category_name.strip()
    if body.is_active is not None:
        isc.is_active = body.is_active
    commit_or_conflict(db, "Input source category already exists")
    db.refresh(isc)
    return isc


@router.patch("/input-source-categories/{category_id}/active")
def toggle_input_source_category(category_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    isc = _get_or_404(db, InputSourceCategory, category_id, "Input source category")
    isc.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": isc.is_active}


@router.delete("/input-source-categories/{category_id}")
def delete_input_source_category(category_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    isc = _get_or_404(db, InputSourceCategory, category_id, "Input source category")
    if isc.is_active:
        raise HTTPException(400, "Deactivate this input source category before deleting it")
    delete_or_conflict(db, isc, "Cannot delete — one or more input source types, products, or activity/product mappings still reference this category")
    return {"ok": True}


# ---------- Input Source Types ----------
@router.post("/input-source-types")
def create_input_source_type(body: InputSourceTypeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, InputSourceCategory, body.category_id, "Input source category")
    ist = InputSourceType(source_name=body.source_name.strip(), category_id=body.category_id,
                          requires_scheme=body.requires_scheme, is_own_source=body.is_own_source,
                          is_active=True if body.is_active is None else body.is_active)
    db.add(ist)
    commit_or_conflict(db, "Input source type already exists")
    db.refresh(ist)
    return ist


@router.patch("/input-source-types/{source_type_id}")
def update_input_source_type(source_type_id: str, body: InputSourceTypeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    ist = _get_or_404(db, InputSourceType, source_type_id, "Input source type")
    _get_or_404(db, InputSourceCategory, body.category_id, "Input source category")
    ist.source_name = body.source_name.strip()
    ist.category_id = body.category_id
    ist.requires_scheme = body.requires_scheme
    ist.is_own_source = body.is_own_source
    if body.is_active is not None:
        ist.is_active = body.is_active
    commit_or_conflict(db, "Input source type already exists")
    db.refresh(ist)
    return ist


@router.patch("/input-source-types/{source_type_id}/active")
def toggle_input_source_type(source_type_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    ist = _get_or_404(db, InputSourceType, source_type_id, "Input source type")
    ist.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": ist.is_active}


@router.delete("/input-source-types/{source_type_id}")
def delete_input_source_type(source_type_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    ist = _get_or_404(db, InputSourceType, source_type_id, "Input source type")
    if ist.is_active:
        raise HTTPException(400, "Deactivate this input source type before deleting it")
    delete_or_conflict(db, ist, "Cannot delete — one or more input mappings or yield input entries still reference this source type")
    return {"ok": True}
