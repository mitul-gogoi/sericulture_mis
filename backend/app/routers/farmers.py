"""Farmers."""
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models import Farmer, User, FigMember, SilkTypeActivityProduct, Land, AssetInstance, AssetType
from app.schemas import FarmerIn, FarmerUpdateIn
from app.services.farmer_reports import apply_farmer_filters
from app.routers.lands import VALID_LAND_TYPES

_PAGE_SIZES = {10, 20, 50, 100}

router = APIRouter(prefix="/farmers", tags=["farmers"])


class ActiveToggleIn(BaseModel):
    is_active: bool


def _fcode(seq: int) -> str:
    return f"SERI-FRM-{seq:06d}"


def _require_output_staps(db: Session, stap_ids: list[str]) -> None:
    if not stap_ids:
        return
    n_output = db.query(SilkTypeActivityProduct).filter(
        SilkTypeActivityProduct.id.in_(stap_ids), SilkTypeActivityProduct.role == "OUTPUT",
    ).count()
    if n_output != len(set(stap_ids)):
        raise HTTPException(400, "A farmer's silk type / activity / product assignment must be an output stage, not an input")


def _next_farmer_seq(db: Session) -> int:
    # Codes must be >= 100001 and never end in 0.
    max_num = 100000
    for (code,) in db.query(Farmer.farmer_code).all():
        try:
            num = int(code.rsplit("-", 1)[-1])
        except (ValueError, AttributeError):
            continue
        max_num = max(max_num, num)
    candidate = max_num + 1
    while candidate % 10 == 0:
        candidate += 1
    return candidate


@router.post("")
def create_farmer(body: FarmerIn, user: User = Depends(require_roles("DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    if user.role == "DISTRICT_ADMIN" and body.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if db.query(Farmer).filter(Farmer.mobile_no == body.mobile_no).first():
        raise HTTPException(400, "Mobile already registered")
    if body.aadhaar_no and db.query(Farmer).filter(Farmer.aadhaar_no == body.aadhaar_no).first():
        raise HTTPException(400, "Aadhaar already registered")
    if body.stap_ids and body.primary_stap_id and body.primary_stap_id not in body.stap_ids:
        raise HTTPException(400, "Primary stap must be in staps")
    _require_output_staps(db, body.stap_ids)
    for land in body.lands:
        if land.land_type not in VALID_LAND_TYPES:
            raise HTTPException(400, f"Invalid land_type: {land.land_type}")
    # Self-declared assets are an eligibility-screening snapshot, so they must reference a real
    # catalog entry — but a FIG-level shared asset can never be owned by an individual farmer.
    asset_types = {}
    if body.assets:
        asset_types = {t.id: t for t in db.query(AssetType).filter(
            AssetType.id.in_([a.asset_type_id for a in body.assets])).all()}
        for asset in body.assets:
            at = asset_types.get(asset.asset_type_id)
            if not at:
                raise HTTPException(400, f"Unknown asset type: {asset.asset_type_id}")
            if at.ownership_level == "FIG":
                raise HTTPException(400, f"'{at.name}' is a FIG-level shared asset — it cannot be declared for an individual farmer")

    seq = _next_farmer_seq(db)
    data = body.model_dump()
    land_rows = data.pop("lands")
    asset_rows = data.pop("assets")
    farmer = Farmer(farmer_code=_fcode(seq), **data)
    db.add(farmer)
    db.flush()
    for land in land_rows:
        db.add(Land(farmer_id=farmer.id, **land))
    for asset in asset_rows:
        year = asset.get("acquisition_year")
        db.add(AssetInstance(
            asset_type_id=asset["asset_type_id"], owner_type="FARMER", owner_id=farmer.id,
            quantity=asset.get("quantity") or 1,
            acquisition_date=date(year, 1, 1) if year else None,
            acquisition_mode="SELF_DECLARED_AT_REGISTRATION",
            confidence="FARMER_SELF_DECLARED", created_by_user_id=user.id,
        ))
    db.commit()
    db.refresh(farmer)
    return {"id": farmer.id, "farmer_code": farmer.farmer_code}


@router.get("")
def list_farmers(
    q: Optional[str] = None,
    district_id: Optional[str] = None,
    seri_circle_id: Optional[str] = None,
    unassigned: bool = False,
    limit: int = Query(100, le=500),
    gender: Optional[str] = None,
    education_level_id: Optional[str] = None,
    caste_id: Optional[str] = None,
    religion_id: Optional[str] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    has_bank_details: Optional[bool] = None,
    is_active: Optional[bool] = None,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    query = db.query(Farmer)
    if user.role == "DISTRICT_ADMIN":
        query = query.filter(Farmer.district_id == user.district_id)
    elif user.role == "FIG_PRESIDENT":
        member_ids = [m.farmer_id for m in db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
        query = query.filter(Farmer.id.in_(member_ids or [""]))
    if district_id and user.role == "STATE_ADMIN":
        query = query.filter(Farmer.district_id == district_id)
    if seri_circle_id:
        query = query.filter(Farmer.seri_circle_id == seri_circle_id)
    if unassigned:
        active_member_ids = [m.farmer_id for m in db.query(FigMember).filter(FigMember.is_active).all()]
        if active_member_ids:
            query = query.filter(~Farmer.id.in_(active_member_ids))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Farmer.first_name.ilike(like), Farmer.last_name.ilike(like),
            Farmer.mobile_no.like(like), Farmer.farmer_code.ilike(like),
        ))
    query = apply_farmer_filters(
        query, gender=gender, education_level_id=education_level_id, caste_id=caste_id, religion_id=religion_id,
        experience_min=experience_min, experience_max=experience_max,
        has_bank_details=has_bank_details, is_active=is_active,
    )
    query = query.order_by(Farmer.created_at.desc())

    # Only opt-in via `page` triggers the new paginated {items,total} shape; omitting it
    # preserves the exact legacy flat-array contract relied on by yields/figs/lands/
    # schemes-beneficiaries pages, none of which ever pass `page`.
    if page is None:
        return query.limit(limit).all()
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    return {"items": rows, "total": total}


@router.get("/{farmer_id}")
def get_farmer(farmer_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    return f


@router.patch("/{farmer_id}")
def update_farmer(farmer_id: str, body: FarmerUpdateIn,
                  user: User = Depends(require_roles("DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and f.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    data = body.model_dump(exclude_unset=True)
    if data.get("mobile_no") and data["mobile_no"] != f.mobile_no:
        if db.query(Farmer).filter(Farmer.mobile_no == data["mobile_no"], Farmer.id != farmer_id).first():
            raise HTTPException(400, "Mobile already registered")
    if data.get("aadhaar_no") and data["aadhaar_no"] != f.aadhaar_no:
        if db.query(Farmer).filter(Farmer.aadhaar_no == data["aadhaar_no"], Farmer.id != farmer_id).first():
            raise HTTPException(400, "Aadhaar already registered")
    stap_ids = data.get("stap_ids", f.stap_ids)
    primary_stap_id = data.get("primary_stap_id", f.primary_stap_id)
    if stap_ids and primary_stap_id and primary_stap_id not in stap_ids:
        raise HTTPException(400, "Primary stap must be in staps")
    if "stap_ids" in data:
        _require_output_staps(db, data["stap_ids"])
    for k, v in data.items():
        setattr(f, k, v)
    f.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(f)
    return f


@router.patch("/{farmer_id}/active")
def toggle_farmer(farmer_id: str, body: ActiveToggleIn,
                  user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and f.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    f.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": f.is_active}
