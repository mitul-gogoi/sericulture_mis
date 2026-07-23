"""Asset instances — recording, listing and physical verification.

Assets are created and verified by District/State Admin (the spec's "Circle Office" role
maps to DA/SA here, exactly as land GPS verification does). FIG Presidents get read-only
visibility of their own FIG's holdings. Scheme-disbursed assets are never posted here —
the scheme module creates them automatically when a beneficiary is registered.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_session, delete_or_conflict
from app.core.deps import get_current_user, require_roles
from app.models import (
    AssetInstance, AssetType, AssetVerificationLog, Farmer, Fig, FigMember, User,
)
from app.schemas import AssetInstanceIn, AssetInstanceUpdateIn, AssetVerifyIn
from app.services.assets import check_asset_cooldown

router = APIRouter(prefix="/assets", tags=["assets"])

# result -> (verification_status, status override or None)
_VERIFY_OUTCOMES = {
    "CONFIRMED_PRESENT": ("CIRCLE_VERIFIED", "FUNCTIONAL"),
    "PARTIALLY_FUNCTIONAL": ("CIRCLE_VERIFIED", "UNDER_REPAIR"),
    "NOT_FOUND": ("DISPUTED", None),
}


def _owner_district(db: Session, owner_type: str, owner_id: str) -> tuple[str, str]:
    """Return (district_id, display_name) for an asset owner, 404 if it doesn't exist."""
    if owner_type == "FARMER":
        f = db.query(Farmer).filter(Farmer.id == owner_id).first()
        if not f:
            raise HTTPException(404, "Farmer not found")
        return f.district_id, f"{f.first_name} {f.last_name}".strip()
    fig = db.query(Fig).filter(Fig.id == owner_id).first()
    if not fig:
        raise HTTPException(404, "FIG not found")
    return fig.district_id, fig.fig_name


def _assert_owner_in_scope(db: Session, user: User, owner_type: str, owner_id: str) -> None:
    district_id, _ = _owner_district(db, owner_type, owner_id)
    if user.role == "DISTRICT_ADMIN" and district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")


def _visible_owner_filter(db: Session, user: User, q):
    """Restrict a query to the assets this user may see."""
    if user.role == "STATE_ADMIN":
        return q
    if user.role == "DISTRICT_ADMIN":
        farmer_ids = [f.id for f in db.query(Farmer).filter(Farmer.district_id == user.district_id).all()]
        fig_ids = [g.id for g in db.query(Fig).filter(Fig.district_id == user.district_id).all()]
        return q.filter(AssetInstance.owner_id.in_((farmer_ids + fig_ids) or [""]))
    # FIG President — own FIG plus its active members
    member_ids = [m.farmer_id for m in db.query(FigMember).filter(
        FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
    return q.filter(AssetInstance.owner_id.in_((member_ids + [user.fig_id or ""]) or [""]))


def _serialize(a: AssetInstance, at: Optional[AssetType], owner_name: Optional[str],
               verifier_name: Optional[str] = None) -> dict:
    return {
        "id": a.id, "asset_type_id": a.asset_type_id,
        "asset_type_name": at.name if at else None,
        "category": at.category if at else None,
        "ownership_level": at.ownership_level if at else None,
        "useful_life_years": at.useful_life_years if at else None,
        "owner_type": a.owner_type, "owner_id": a.owner_id, "owner_name": owner_name,
        "quantity": a.quantity, "acquisition_date": a.acquisition_date,
        "acquisition_mode": a.acquisition_mode, "scheme_id": a.scheme_id,
        "beneficiary_id": a.beneficiary_id, "status": a.status,
        "verification_status": a.verification_status, "confidence": a.confidence,
        "photo_path": a.photo_path, "remarks": a.remarks,
        "last_verified_by": a.last_verified_by, "last_verified_by_name": verifier_name,
        "last_verified_at": a.last_verified_at, "created_at": a.created_at,
    }


@router.post("")
def create_asset(body: AssetInstanceIn,
                 user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                 db: Session = Depends(get_session)):
    at = db.query(AssetType).filter(AssetType.id == body.asset_type_id).first()
    if not at:
        raise HTTPException(404, "Asset type not found")
    if not at.is_active:
        raise HTTPException(400, "This asset type is inactive")
    _assert_owner_in_scope(db, user, body.owner_type, body.owner_id)
    if at.ownership_level == "INDIVIDUAL" and body.owner_type == "FIG":
        raise HTTPException(400, f"'{at.name}' is an individually-owned asset — it cannot belong to a FIG")
    if at.ownership_level == "FIG" and body.owner_type == "FARMER":
        raise HTTPException(400, f"'{at.name}' is a FIG-level shared asset — it cannot belong to an individual farmer")

    a = AssetInstance(
        asset_type_id=body.asset_type_id, owner_type=body.owner_type, owner_id=body.owner_id,
        quantity=body.quantity, acquisition_date=body.acquisition_date,
        acquisition_mode=body.acquisition_mode, confidence=body.confidence,
        photo_path=body.photo_path, remarks=body.remarks or "",
        created_by_user_id=user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id}


@router.get("")
def list_assets(owner_type: Optional[str] = None, owner_id: Optional[str] = None,
                asset_type_id: Optional[str] = None, status: Optional[str] = None,
                verification_status: Optional[str] = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(AssetInstance)
    if owner_type:
        q = q.filter(AssetInstance.owner_type == owner_type)
    if owner_id:
        q = q.filter(AssetInstance.owner_id == owner_id)
    if asset_type_id:
        q = q.filter(AssetInstance.asset_type_id == asset_type_id)
    if status:
        q = q.filter(AssetInstance.status == status)
    if verification_status:
        q = q.filter(AssetInstance.verification_status == verification_status)
    q = _visible_owner_filter(db, user, q)
    rows = q.order_by(AssetInstance.created_at.desc()).limit(500).all()

    types = {t.id: t for t in db.query(AssetType).all()}
    farmer_ids = [r.owner_id for r in rows if r.owner_type == "FARMER"]
    fig_ids = [r.owner_id for r in rows if r.owner_type == "FIG"]
    farmers = {f.id: f"{f.first_name} {f.last_name}".strip()
               for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    figs = {g.id: g.fig_name for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}
    verifier_ids = [r.last_verified_by for r in rows if r.last_verified_by]
    verifiers = {u.id: (u.name or u.mobile_no)
                 for u in db.query(User).filter(User.id.in_(verifier_ids or [""])).all()}

    out = []
    for r in rows:
        owner_name = farmers.get(r.owner_id) if r.owner_type == "FARMER" else figs.get(r.owner_id)
        out.append(_serialize(r, types.get(r.asset_type_id), owner_name,
                              verifiers.get(r.last_verified_by) if r.last_verified_by else None))
    return out


@router.get("/cooldown-check")
def cooldown_check(owner_type: str, owner_id: str, asset_type_id: str,
                   user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if owner_type not in ("FARMER", "FIG"):
        raise HTTPException(400, "owner_type must be FARMER or FIG")
    return check_asset_cooldown(db, owner_type, owner_id, asset_type_id)


@router.patch("/{asset_id}")
def update_asset(asset_id: str, body: AssetInstanceUpdateIn,
                 user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                 db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    _assert_owner_in_scope(db, user, a.owner_type, a.owner_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return {"ok": True}


@router.delete("/{asset_id}")
def delete_asset(asset_id: str, user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                 db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    _assert_owner_in_scope(db, user, a.owner_type, a.owner_id)
    if a.acquisition_mode == "SCHEME_DISBURSEMENT":
        raise HTTPException(400, "Scheme-disbursed assets cannot be deleted — they mirror a disbursement record")
    db.query(AssetVerificationLog).filter(AssetVerificationLog.asset_instance_id == a.id).delete()
    delete_or_conflict(db, a, "Cannot delete — this asset is still referenced elsewhere")
    return {"ok": True}


@router.post("/{asset_id}/verify")
def verify_asset(asset_id: str, body: AssetVerifyIn,
                 user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                 db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    _assert_owner_in_scope(db, user, a.owner_type, a.owner_id)

    verification_status, new_status = _VERIFY_OUTCOMES[body.result]
    a.verification_status = verification_status
    if new_status:
        a.status = new_status
    a.last_verified_by = user.id
    a.last_verified_at = datetime.now(timezone.utc)
    if body.photo_url:
        a.photo_path = a.photo_path or body.photo_url
    db.add(AssetVerificationLog(
        asset_instance_id=a.id, checked_by_user_id=user.id, result=body.result,
        photo_url=body.photo_url, remarks=body.remarks or "",
    ))
    db.commit()
    return {"ok": True, "verification_status": a.verification_status, "status": a.status}


@router.get("/{asset_id}/verification-log")
def verification_log(asset_id: str, user: User = Depends(get_current_user),
                     db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN":
        _assert_owner_in_scope(db, user, a.owner_type, a.owner_id)
    elif user.role == "FIG_PRESIDENT":
        visible = _visible_owner_filter(db, user, db.query(AssetInstance).filter(
            AssetInstance.id == asset_id)).first()
        if not visible:
            raise HTTPException(403, "Out of scope")
    rows = db.query(AssetVerificationLog).filter(
        AssetVerificationLog.asset_instance_id == asset_id
    ).order_by(AssetVerificationLog.checked_at.desc()).all()
    names = {u.id: (u.name or u.mobile_no) for u in db.query(User).filter(
        User.id.in_([r.checked_by_user_id for r in rows] or [""])).all()}
    return [{"id": r.id, "result": r.result, "photo_url": r.photo_url, "remarks": r.remarks,
             "checked_at": r.checked_at, "checked_by": names.get(r.checked_by_user_id)}
            for r in rows]
