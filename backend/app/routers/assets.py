"""Asset instances — recording, listing, physical verification, and GPS capture/approval.

Assets are created (both at Register Farmer/FIG time and later, for a self-procured
addition) and verified/edited/deleted by District Admin only — State Admin is view-only
here, matching Land & GIS's own SA-view-only convention. Scheme-disbursed assets are never
posted here — the scheme module creates them automatically when a beneficiary is
registered. GPS is a separate lifecycle from the physical-condition check: a FIG President
captures an asset's location (never at registration time), a District Admin approves or
rejects it — mirroring Land.gps_verified exactly, just for a single point instead of a
boundary polygon.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.db import get_session, delete_or_conflict
from app.core.deps import get_current_user, require_roles
from app.models import (
    AssetInstance, AssetType, AssetVerificationLog, Farmer, Fig, FigMember, User, AssetGpsDraft,
)
from app.schemas import (
    AssetInstanceIn, AssetInstanceUpdateIn, AssetVerifyIn, AssetGpsSubmitIn, AssetGpsVerifyIn,
)
from app.services.assets import check_asset_cooldown, asset_report_rows, next_asset_seq, asset_code
from app.core.scope import active_district

router = APIRouter(prefix="/assets", tags=["assets"])

_PAGE_SIZES = {10, 20, 50, 100}

# result -> (verification_status, status override or None)
_VERIFY_OUTCOMES = {
    "CONFIRMED_PRESENT": ("CIRCLE_VERIFIED", "FUNCTIONAL"),
    "PARTIALLY_FUNCTIONAL": ("CIRCLE_VERIFIED", "UNDER_REPAIR"),
    "NOT_FOUND": ("DISPUTED", None),
}


def _owner_district_circle(db: Session, owner_type: str, owner_id: str) -> tuple[str, str, str]:
    """Return (district_id, seri_circle_id, display_name) for an asset owner, 404 if missing."""
    if owner_type == "FARMER":
        f = db.query(Farmer).filter(Farmer.id == owner_id).first()
        if not f:
            raise HTTPException(404, "Farmer not found")
        return f.district_id, f.seri_circle_id, f"{f.first_name} {f.last_name}".strip()
    fig = db.query(Fig).filter(Fig.id == owner_id).first()
    if not fig:
        raise HTTPException(404, "FIG not found")
    return fig.district_id, fig.seri_circle_id, fig.fig_name


def _assert_owner_in_scope(db: Session, user: User, owner_type: str, owner_id: str) -> None:
    district_id, _, _ = _owner_district_circle(db, owner_type, owner_id)
    if user.role == "DISTRICT_ADMIN" and district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")


def _assert_owner_is_own_fig(db: Session, user: User, owner_type: str, owner_id: str) -> None:
    """FIG President scope: the asset must belong to their own FIG or one of its active members."""
    member_ids = {m.farmer_id for m in db.query(FigMember).filter(
        FigMember.fig_id == user.fig_id, FigMember.is_active).all()}
    in_scope = (owner_type == "FIG" and owner_id == user.fig_id) or \
               (owner_type == "FARMER" and owner_id in member_ids)
    if not in_scope:
        raise HTTPException(403, "Out of scope")


def _active_fig_member(db: Session, farmer_id: str) -> Optional[FigMember]:
    return db.query(FigMember).filter(
        FigMember.farmer_id == farmer_id, FigMember.is_active).first()


def _consume_asset_gps_draft(db: Session, asset_id: str) -> None:
    draft = db.query(AssetGpsDraft).filter(AssetGpsDraft.asset_id == asset_id).first()
    if draft:
        db.delete(draft)


def _visible_owner_filter(db: Session, user: User, q):
    """Restrict a query to the assets this user may see."""
    if user.role == "STATE_ADMIN":
        return q
    if user.role == "DISTRICT_ADMIN":
        farmer_ids = [f.id for f in db.query(Farmer).filter(Farmer.district_id == active_district(user)).all()]
        fig_ids = [g.id for g in db.query(Fig).filter(Fig.district_id == active_district(user)).all()]
        return q.filter(AssetInstance.owner_id.in_((farmer_ids + fig_ids) or [""]))
    if user.role == "FARMER":
        return q.filter(AssetInstance.owner_type == "FARMER", AssetInstance.owner_id == user.farmer_id)
    # FIG President — own FIG plus its active members
    member_ids = [m.farmer_id for m in db.query(FigMember).filter(
        FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
    return q.filter(AssetInstance.owner_id.in_((member_ids + [user.fig_id or ""]) or [""]))


def _serialize(a: AssetInstance, at: Optional[AssetType], owner_name: Optional[str],
               verifier_name: Optional[str] = None) -> dict:
    return {
        "id": a.id, "asset_code": a.asset_code, "asset_type_id": a.asset_type_id,
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
        "latitude": a.latitude, "longitude": a.longitude, "gps_status": a.gps_status,
        "gps_failure_reason": a.gps_failure_reason,
    }


@router.post("")
def create_asset(body: AssetInstanceIn,
                 user: User = Depends(require_roles("DISTRICT_ADMIN")),
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
        asset_code=asset_code(next_asset_seq(db)),
        asset_type_id=body.asset_type_id, owner_type=body.owner_type, owner_id=body.owner_id,
        quantity=body.quantity, acquisition_date=body.acquisition_date,
        acquisition_mode=body.acquisition_mode, confidence=body.confidence,
        photo_path=body.photo_path, remarks=body.remarks or "",
        created_by_user_id=user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "asset_code": a.asset_code}


def _owner_id_filters(db: Session, q_text: Optional[str], district_id: Optional[str],
                      seri_circle_id: Optional[str]):
    """Resolve q/district/circle into an owner-scoped filter clause, or None if none apply."""
    if not (q_text or district_id or seri_circle_id):
        return None

    farmer_q = db.query(Farmer.id)
    fig_q = db.query(Fig.id)
    if district_id:
        farmer_q = farmer_q.filter(Farmer.district_id == district_id)
        fig_q = fig_q.filter(Fig.district_id == district_id)
    if seri_circle_id:
        farmer_q = farmer_q.filter(Farmer.seri_circle_id == seri_circle_id)
        fig_q = fig_q.filter(Fig.seri_circle_id == seri_circle_id)
    if q_text:
        like = f"%{q_text}%"
        farmer_q = farmer_q.filter(or_(
            Farmer.farmer_code.ilike(like), Farmer.mobile_no.ilike(like),
            Farmer.first_name.ilike(like), Farmer.last_name.ilike(like),
        ))
        fig_q = fig_q.filter(or_(Fig.fig_code.ilike(like), Fig.fig_name.ilike(like)))

    farmer_ids = [r[0] for r in farmer_q.all()]
    fig_ids = [r[0] for r in fig_q.all()]
    return or_(
        and_(AssetInstance.owner_type == "FARMER", AssetInstance.owner_id.in_(farmer_ids or [""])),
        and_(AssetInstance.owner_type == "FIG", AssetInstance.owner_id.in_(fig_ids or [""])),
    )


@router.get("")
def list_assets(owner_type: Optional[str] = None, owner_id: Optional[str] = None,
                asset_type_id: Optional[str] = None, status: Optional[str] = None,
                verification_status: Optional[str] = None, confidence: Optional[str] = None,
                gps_status: Optional[str] = None, q: Optional[str] = None,
                district_id: Optional[str] = None, seri_circle_id: Optional[str] = None,
                page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    query = db.query(AssetInstance)
    if owner_type:
        query = query.filter(AssetInstance.owner_type == owner_type)
    if owner_id:
        query = query.filter(AssetInstance.owner_id == owner_id)
    if asset_type_id:
        query = query.filter(AssetInstance.asset_type_id == asset_type_id)
    if status:
        query = query.filter(AssetInstance.status == status)
    if verification_status:
        query = query.filter(AssetInstance.verification_status == verification_status)
    if confidence:
        query = query.filter(AssetInstance.confidence == confidence)
    if gps_status:
        query = query.filter(AssetInstance.gps_status == gps_status)
    owner_clause = _owner_id_filters(db, q, district_id, seri_circle_id)
    if owner_clause is not None:
        query = query.filter(owner_clause)
    query = _visible_owner_filter(db, user, query)
    query = query.order_by(AssetInstance.created_at.desc())

    # Only opt-in via `page` triggers the new paginated {items,total} shape; omitting it
    # preserves the exact legacy flat-array contract, matching lands.py's own convention.
    show_drafts = user.role in ("FIG_PRESIDENT", "DISTRICT_ADMIN", "STATE_ADMIN")
    if page is None:
        rows = query.limit(500).all()
        types = {t.id: t for t in db.query(AssetType).all()}
        farmer_ids = [r.owner_id for r in rows if r.owner_type == "FARMER"]
        fig_ids = [r.owner_id for r in rows if r.owner_type == "FIG"]
        farmers = {f.id: f"{f.first_name} {f.last_name}".strip()
                   for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
        figs = {g.id: g.fig_name for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}
        verifier_ids = [r.last_verified_by for r in rows if r.last_verified_by]
        verifiers = {u.id: (u.name or u.mobile_no)
                     for u in db.query(User).filter(User.id.in_(verifier_ids or [""])).all()}
        draft_asset_ids = set()
        if show_drafts:
            draft_asset_ids = {r[0] for r in db.query(AssetGpsDraft.asset_id).filter(
                AssetGpsDraft.asset_id.in_([r.id for r in rows] or [""])).all()}
        out = []
        for r in rows:
            owner_name = farmers.get(r.owner_id) if r.owner_type == "FARMER" else figs.get(r.owner_id)
            row = _serialize(r, types.get(r.asset_type_id), owner_name,
                             verifiers.get(r.last_verified_by) if r.last_verified_by else None)
            if show_drafts:
                row["has_gps_draft"] = r.id in draft_asset_ids
            out.append(row)
        return out

    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = query.count()
    page_assets = query.offset((page - 1) * size).limit(size).all()
    rows = asset_report_rows(page_assets, db)
    if show_drafts:
        draft_asset_ids = {r[0] for r in db.query(AssetGpsDraft.asset_id).filter(
            AssetGpsDraft.asset_id.in_([a.id for a in page_assets] or [""])).all()}
        for row in rows:
            row["has_gps_draft"] = row["id"] in draft_asset_ids
    return {"items": rows, "total": total}


@router.get("/cooldown-check")
def cooldown_check(owner_type: str, owner_id: str, asset_type_id: str,
                   user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if owner_type not in ("FARMER", "FIG"):
        raise HTTPException(400, "owner_type must be FARMER or FIG")
    return check_asset_cooldown(db, owner_type, owner_id, asset_type_id)


@router.patch("/{asset_id}")
def update_asset(asset_id: str, body: AssetInstanceUpdateIn,
                 user: User = Depends(require_roles("DISTRICT_ADMIN")),
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
def delete_asset(asset_id: str, user: User = Depends(require_roles("DISTRICT_ADMIN")),
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
                 user: User = Depends(require_roles("DISTRICT_ADMIN")),
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


@router.post("/{asset_id}/gps/draft")
def save_asset_gps_draft(asset_id: str, body: AssetGpsSubmitIn, user: User = Depends(require_roles("FARMER")),
                         db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    if not (a.owner_type == "FARMER" and a.owner_id == user.farmer_id):
        raise HTTPException(403, "Out of scope")
    member = _active_fig_member(db, user.farmer_id)
    if not member:
        raise HTTPException(400, "You have no active FIG — submit directly via POST /assets/{id}/gps instead")
    draft = db.query(AssetGpsDraft).filter(AssetGpsDraft.asset_id == asset_id).first()
    if draft:
        draft.latitude = body.latitude
        draft.longitude = body.longitude
        draft.updated_at = datetime.now(timezone.utc)
    else:
        db.add(AssetGpsDraft(farmer_id=user.farmer_id, asset_id=asset_id, fig_id=member.fig_id,
                             latitude=body.latitude, longitude=body.longitude))
    db.commit()
    return {"ok": True}


@router.get("/{asset_id}/gps/draft")
def get_asset_gps_draft(asset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    if user.role == "FARMER":
        if not (a.owner_type == "FARMER" and a.owner_id == user.farmer_id):
            raise HTTPException(403, "Out of scope")
    elif user.role == "FIG_PRESIDENT":
        _assert_owner_is_own_fig(db, user, a.owner_type, a.owner_id)
    else:
        raise HTTPException(403, "Not permitted")
    draft = db.query(AssetGpsDraft).filter(AssetGpsDraft.asset_id == asset_id).first()
    if not draft:
        return None
    return {"latitude": draft.latitude, "longitude": draft.longitude,
            "updated_at": draft.updated_at, "farmer_id": draft.farmer_id}


@router.post("/{asset_id}/gps")
def submit_asset_gps(asset_id: str, body: AssetGpsSubmitIn,
                     user: User = Depends(require_roles("FARMER", "FIG_PRESIDENT")),
                     db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    if user.role == "FARMER":
        if not (a.owner_type == "FARMER" and a.owner_id == user.farmer_id):
            raise HTTPException(403, "Out of scope")
        if _active_fig_member(db, user.farmer_id):
            raise HTTPException(400, "You have an active FIG — save this as a draft for your FIG President instead of submitting directly")
    else:
        _assert_owner_is_own_fig(db, user, a.owner_type, a.owner_id)
    a.latitude = body.latitude
    a.longitude = body.longitude
    a.gps_status = "Pending"
    a.gps_failure_reason = None
    a.gps_verified_by = None
    a.gps_verified_at = None
    _consume_asset_gps_draft(db, a.id)
    db.commit()
    return {"ok": True, "gps_status": a.gps_status}


@router.post("/{asset_id}/gps/verify")
def verify_asset_gps(asset_id: str, body: AssetGpsVerifyIn,
                     user: User = Depends(require_roles("DISTRICT_ADMIN")),
                     db: Session = Depends(get_session)):
    a = db.query(AssetInstance).filter(AssetInstance.id == asset_id).first()
    if not a:
        raise HTTPException(404, "Not found")
    _assert_owner_in_scope(db, user, a.owner_type, a.owner_id)
    if a.gps_status != "Pending":
        raise HTTPException(400, "No pending GPS submission to review")
    if body.decision == "verified":
        a.gps_status = "Verified"
        a.gps_failure_reason = None
    else:
        a.gps_status = "Failed"
        a.gps_failure_reason = body.reason
    a.gps_verified_by = user.id
    a.gps_verified_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "gps_status": a.gps_status}


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
