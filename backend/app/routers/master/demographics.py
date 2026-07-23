"""Caste, religion, and education-level master data — read (public) + State-Admin-only CRUD."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.db import get_session, commit_or_conflict, delete_or_conflict
from app.models import Caste, Religion, EducationLevel, User
from ._common import _SA, _q, _get_or_404, ActiveToggleIn

router = APIRouter()


@router.get("/castes")
def list_castes(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, Caste, all).order_by(Caste.caste_name).all()


@router.get("/religions")
def list_religions(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, Religion, all).order_by(Religion.religion_name).all()


@router.get("/education-levels")
def list_education_levels(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, EducationLevel, all).order_by(EducationLevel.education_level_name).all()


class CasteIn(BaseModel):
    caste_name: str = Field(min_length=1, max_length=40)
    is_active: Optional[bool] = None


class ReligionIn(BaseModel):
    religion_name: str = Field(min_length=1, max_length=40)
    is_active: Optional[bool] = None


class EducationLevelIn(BaseModel):
    education_level_name: str = Field(min_length=1, max_length=50)
    is_active: Optional[bool] = None


# ---------- Castes ----------
@router.post("/castes")
def create_caste(body: CasteIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = Caste(caste_name=body.caste_name.strip(),
              is_active=True if body.is_active is None else body.is_active)
    db.add(c)
    commit_or_conflict(db, "Caste name already exists")
    db.refresh(c)
    return c


@router.patch("/castes/{caste_id}")
def update_caste(caste_id: str, body: CasteIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, Caste, caste_id, "Caste")
    c.caste_name = body.caste_name.strip()
    if body.is_active is not None:
        c.is_active = body.is_active
    commit_or_conflict(db, "Caste name already exists")
    db.refresh(c)
    return c


@router.patch("/castes/{caste_id}/active")
def toggle_caste(caste_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, Caste, caste_id, "Caste")
    c.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": c.is_active}


@router.delete("/castes/{caste_id}")
def delete_caste(caste_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, Caste, caste_id, "Caste")
    if c.is_active:
        raise HTTPException(400, "Deactivate this caste before deleting it")
    delete_or_conflict(db, c, "Cannot delete — one or more farmers still reference this caste")
    return {"ok": True}


# ---------- Religions ----------
@router.post("/religions")
def create_religion(body: ReligionIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    r = Religion(religion_name=body.religion_name.strip(),
                 is_active=True if body.is_active is None else body.is_active)
    db.add(r)
    commit_or_conflict(db, "Religion name already exists")
    db.refresh(r)
    return r


@router.patch("/religions/{religion_id}")
def update_religion(religion_id: str, body: ReligionIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    r = _get_or_404(db, Religion, religion_id, "Religion")
    r.religion_name = body.religion_name.strip()
    if body.is_active is not None:
        r.is_active = body.is_active
    commit_or_conflict(db, "Religion name already exists")
    db.refresh(r)
    return r


@router.patch("/religions/{religion_id}/active")
def toggle_religion(religion_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    r = _get_or_404(db, Religion, religion_id, "Religion")
    r.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": r.is_active}


@router.delete("/religions/{religion_id}")
def delete_religion(religion_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    r = _get_or_404(db, Religion, religion_id, "Religion")
    if r.is_active:
        raise HTTPException(400, "Deactivate this religion before deleting it")
    delete_or_conflict(db, r, "Cannot delete — one or more farmers still reference this religion")
    return {"ok": True}


# ---------- Education Levels ----------
@router.post("/education-levels")
def create_education_level(body: EducationLevelIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    e = EducationLevel(education_level_name=body.education_level_name.strip(),
                       is_active=True if body.is_active is None else body.is_active)
    db.add(e)
    commit_or_conflict(db, "Education level already exists")
    db.refresh(e)
    return e


@router.patch("/education-levels/{education_level_id}")
def update_education_level(education_level_id: str, body: EducationLevelIn,
                           user: User = Depends(_SA), db: Session = Depends(get_session)):
    e = _get_or_404(db, EducationLevel, education_level_id, "Education level")
    e.education_level_name = body.education_level_name.strip()
    if body.is_active is not None:
        e.is_active = body.is_active
    commit_or_conflict(db, "Education level already exists")
    db.refresh(e)
    return e


@router.patch("/education-levels/{education_level_id}/active")
def toggle_education_level(education_level_id: str, body: ActiveToggleIn,
                           user: User = Depends(_SA), db: Session = Depends(get_session)):
    e = _get_or_404(db, EducationLevel, education_level_id, "Education level")
    e.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": e.is_active}


@router.delete("/education-levels/{education_level_id}")
def delete_education_level(education_level_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    e = _get_or_404(db, EducationLevel, education_level_id, "Education level")
    if e.is_active:
        raise HTTPException(400, "Deactivate this education level before deleting it")
    delete_or_conflict(db, e, "Cannot delete — one or more farmers still reference this education level")
    return {"ok": True}
