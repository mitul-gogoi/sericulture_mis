"""Asset-type catalog master data — read (public) + State-Admin-only CRUD."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.db import get_session, commit_or_conflict, delete_or_conflict
from app.models import AssetType, User
from ._common import _SA, _q, _get_or_404, ActiveToggleIn

router = APIRouter()


@router.get("/asset-types")
def list_asset_types(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, AssetType, all).order_by(AssetType.name).all()


class AssetTypeIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(pattern="^(STRUCTURE|SHARED_INFRASTRUCTURE|EQUIPMENT)$")
    silk_types: list[str] = []          # empty = applies to all silk types
    ownership_level: str = Field(default="INDIVIDUAL", pattern="^(INDIVIDUAL|FIG|EITHER)$")
    useful_life_years: int = Field(default=0, ge=0, le=100)
    typically_scheme_funded: bool = True
    is_active: Optional[bool] = None


@router.post("/asset-types")
def create_asset_type(body: AssetTypeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    at = AssetType(name=body.name.strip(), category=body.category, silk_types=body.silk_types,
                   ownership_level=body.ownership_level, useful_life_years=body.useful_life_years,
                   typically_scheme_funded=body.typically_scheme_funded,
                   is_active=True if body.is_active is None else body.is_active)
    db.add(at)
    commit_or_conflict(db, "Asset type already exists")
    db.refresh(at)
    return at


@router.patch("/asset-types/{asset_type_id}")
def update_asset_type(asset_type_id: str, body: AssetTypeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    at = _get_or_404(db, AssetType, asset_type_id, "Asset type")
    at.name = body.name.strip()
    at.category = body.category
    at.silk_types = body.silk_types
    at.ownership_level = body.ownership_level
    at.useful_life_years = body.useful_life_years
    at.typically_scheme_funded = body.typically_scheme_funded
    if body.is_active is not None:
        at.is_active = body.is_active
    commit_or_conflict(db, "Asset type already exists")
    db.refresh(at)
    return at


@router.patch("/asset-types/{asset_type_id}/active")
def toggle_asset_type(asset_type_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    at = _get_or_404(db, AssetType, asset_type_id, "Asset type")
    at.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": at.is_active}


@router.delete("/asset-types/{asset_type_id}")
def delete_asset_type(asset_type_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    at = _get_or_404(db, AssetType, asset_type_id, "Asset type")
    if at.is_active:
        raise HTTPException(400, "Deactivate this asset type before deleting it")
    delete_or_conflict(db, at, "Cannot delete — one or more recorded assets or schemes still reference this asset type")
    return {"ok": True}
