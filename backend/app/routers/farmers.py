"""Farmers."""
from datetime import datetime, timezone, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.core.security import hash_password, DEFAULT_FARMER_PASSWORD
from app.core.aadhaar import normalize_aadhaar, aadhaar_hash, aadhaar_fields, aadhaar_decrypt
from app.models import (
    Farmer, User, FigMember, SilkTypeActivityProduct, Land, AssetInstance, AssetType,
    Fig, Meeting, FarmerSubmission, FarmerSubmissionCorrection, FarmerDraftEntry, _now,
    District, SericultureCircle, Caste, Religion, EducationLevel,
)
from app.schemas import (
    FarmerIn, FarmerUpdateIn, FarmerPasswordResetIn, FarmerSubmissionIn, FarmerSubmissionCorrectionIn,
    FarmerDraftIn,
)
from app.services.farmer_reports import apply_farmer_filters, fig_by_farmer, public_farmer_dict
from app.services.assets import next_asset_seq, asset_code
from app.services.meeting_reports import fp_submission_history_rows, _serialize_farmer_submission_detail
from app.services.notifications import create_notification
from app.routers.lands import VALID_LAND_TYPES
from app.routers.meetings import _apply_yield_entries, _validate_entries_readonly
from app.core.scope import active_district

_PAGE_SIZES = {10, 20, 50, 100}

router = APIRouter(prefix="/farmers", tags=["farmers"])


class ActiveToggleIn(BaseModel):
    is_active: bool


def _fcode(seq: int) -> str:
    return f"SERI-FRM-{seq:06d}"


def _set_aadhaar(f: Farmer, digits: str) -> None:
    """Write the three derived columns; the raw digits are never stored."""
    for field, value in aadhaar_fields(digits).items():
        setattr(f, field, value)


def _aadhaar_digits_or_400(raw: str) -> str:
    try:
        return normalize_aadhaar(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


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
    if user.role == "DISTRICT_ADMIN" and body.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    if db.query(Farmer).filter(Farmer.mobile_no == body.mobile_no).first():
        raise HTTPException(400, "Mobile already registered")
    if db.query(User).filter(User.mobile_no == body.mobile_no).first():
        raise HTTPException(400, "Mobile already registered")
    aadhaar_digits = None
    if body.aadhaar_no:
        aadhaar_digits = _aadhaar_digits_or_400(body.aadhaar_no)
        if db.query(Farmer).filter(Farmer.aadhaar_hash == aadhaar_hash(aadhaar_digits)).first():
            raise HTTPException(400, "Aadhaar already registered")
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
    data.pop("aadhaar_no", None)  # write-only input — stored as the three derived columns below
    farmer = Farmer(farmer_code=_fcode(seq), **data)
    if aadhaar_digits:
        _set_aadhaar(farmer, aadhaar_digits)
    db.add(farmer)
    db.flush()
    db.add(User(
        mobile_no=farmer.mobile_no, password_hash=hash_password(DEFAULT_FARMER_PASSWORD),
        role="FARMER", farmer_id=farmer.id, district_id=farmer.district_id,
        name=f"{farmer.first_name} {farmer.last_name}".strip(),
    ))
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
            asset_code=asset_code(next_asset_seq(db)),
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
    has_fig: Optional[bool] = None,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    query = db.query(Farmer)
    if user.role == "DISTRICT_ADMIN":
        query = query.filter(Farmer.district_id == active_district(user))
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
        has_bank_details=has_bank_details, is_active=is_active, has_fig=has_fig,
    )
    query = query.order_by(Farmer.created_at.desc())

    # Only opt-in via `page` triggers the new paginated {items,total} shape; omitting it
    # preserves the exact legacy flat-array contract relied on by yields/figs/lands/
    # schemes-beneficiaries pages, none of which ever pass `page`.
    if page is None:
        return [public_farmer_dict(r) for r in query.limit(limit).all()]
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    fig_map = fig_by_farmer(db, [r.id for r in rows])
    items = [
        {**public_farmer_dict(r), "fig_id": fig_map[r.id].id if r.id in fig_map else None,
         "fig_name": fig_map[r.id].fig_name if r.id in fig_map else None}
        for r in rows
    ]
    return {"items": items, "total": total}


@router.get("/me")
def get_own_farmer(user: User = Depends(require_roles("FARMER")), db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == user.farmer_id).first()
    if not f:
        raise HTTPException(404, "Farmer profile not found")
    member = db.query(FigMember).filter(FigMember.farmer_id == f.id, FigMember.is_active).first()
    fig = db.query(Fig).filter(Fig.id == member.fig_id).first() if member else None
    data = public_farmer_dict(f)
    data["fig_id"] = fig.id if fig else None
    data["fig_name"] = fig.fig_name if fig else None
    data["fig_code"] = fig.fig_code if fig else None
    # The ONE place the real Aadhaar is decrypted — a farmer viewing their own record.
    data["aadhaar_full"] = aadhaar_decrypt(f.aadhaar_enc) if f.aadhaar_enc else None
    # Resolved display names so the My Profile page never renders raw UUIDs.
    def _name(model, col, fk):
        row = db.query(model).filter(model.id == fk).first() if fk else None
        return getattr(row, col) if row else None
    data["district_name"] = _name(District, "district_name", f.district_id)
    data["circle_name"] = _name(SericultureCircle, "circle_name", f.seri_circle_id)
    data["caste_name"] = _name(Caste, "caste_name", f.caste_id)
    data["religion_name"] = _name(Religion, "religion_name", f.religion_id)
    data["education_level_name"] = _name(EducationLevel, "education_level_name", f.education_level_id)
    return data


@router.get("/me/summary")
def get_own_summary(user: User = Depends(require_roles("FARMER")), db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == user.farmer_id).first()
    if not f:
        raise HTTPException(404, "Farmer profile not found")
    member = db.query(FigMember).filter(FigMember.farmer_id == f.id, FigMember.is_active).first()
    fig = db.query(Fig).filter(Fig.id == member.fig_id).first() if member else None
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    has_draft_this_month = False
    if fig:
        submitted_this_month = db.query(Meeting).filter(
            Meeting.fig_id == fig.id, Meeting.meeting_month == current_month).first() is not None
        has_draft_this_month = db.query(FarmerDraftEntry).filter(
            FarmerDraftEntry.farmer_id == f.id, FarmerDraftEntry.draft_month == current_month).first() is not None
    else:
        submitted_this_month = db.query(FarmerSubmission).filter(
            FarmerSubmission.farmer_id == f.id, FarmerSubmission.submission_month == current_month).first() is not None
    land_count = db.query(Land).filter(Land.farmer_id == f.id).count()
    lands_needing_gps = db.query(Land).filter(
        Land.farmer_id == f.id, Land.gps_verified == "Not Submitted").count()
    asset_count = db.query(AssetInstance).filter(
        AssetInstance.owner_type == "FARMER", AssetInstance.owner_id == f.id).count()
    return {
        "fig_id": fig.id if fig else None, "fig_name": fig.fig_name if fig else None,
        "has_draft_this_month": has_draft_this_month,
        "fig_code": fig.fig_code if fig else None,
        "current_month": current_month, "submitted_this_month": submitted_this_month,
        "land_count": land_count, "lands_needing_gps": lands_needing_gps, "asset_count": asset_count,
    }


@router.get("/me/meetings")
def get_own_meetings(user: User = Depends(require_roles("FARMER")), db: Session = Depends(get_session)):
    member = db.query(FigMember).filter(FigMember.farmer_id == user.farmer_id, FigMember.is_active).first()
    if not member:
        return []
    return fp_submission_history_rows(db, member.fig_id)


def _next_submission_seq(db: Session) -> int:
    last = db.query(FarmerSubmission.submission_code).order_by(FarmerSubmission.submission_code.desc()).first()
    if not last:
        return 1
    try:
        return int(last[0].rsplit("-", 1)[-1]) + 1
    except (ValueError, AttributeError):
        return 1


@router.post("/me/submissions")
def create_own_submission(body: FarmerSubmissionIn, user: User = Depends(require_roles("FARMER")),
                          db: Session = Depends(get_session)):
    if db.query(FigMember).filter(FigMember.farmer_id == user.farmer_id, FigMember.is_active).first():
        raise HTTPException(400, "FIG members submit via their FIG President's monthly meeting, not directly")
    if db.query(FarmerSubmission).filter(
        FarmerSubmission.farmer_id == user.farmer_id, FarmerSubmission.submission_month == body.submission_month
    ).first():
        raise HTTPException(400, "You have already submitted for this month")

    seq = _next_submission_seq(db)
    submission = FarmerSubmission(
        farmer_id=user.farmer_id, submission_code=f"SERI-SUB-{seq:06d}",
        submission_month=body.submission_month,
    )
    db.add(submission)
    db.flush()

    entries = [{**e, "farmer_id": user.farmer_id} for e in body.entries]
    created = _apply_yield_entries(db, entries, yield_month=body.submission_month,
                                   fig_id=None, farmer_submission_id=submission.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Duplicate yield for same activity-product/month")
    return {"id": submission.id, "submission_code": submission.submission_code, "entries_count": len(created)}


@router.get("/me/submissions")
def list_own_submissions(page: int = Query(1, ge=1), page_size: Optional[int] = None,
                         user: User = Depends(require_roles("FARMER")), db: Session = Depends(get_session)):
    q = db.query(FarmerSubmission).filter(FarmerSubmission.farmer_id == user.farmer_id) \
        .order_by(FarmerSubmission.submission_month.desc())
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    return {"items": rows, "total": total}


@router.get("/me/submissions/{submission_id}")
def get_own_submission_detail(submission_id: str, user: User = Depends(require_roles("FARMER")),
                              db: Session = Depends(get_session)):
    submission = db.query(FarmerSubmission).filter(
        FarmerSubmission.id == submission_id, FarmerSubmission.farmer_id == user.farmer_id).first()
    if not submission:
        raise HTTPException(404, "Not found")
    return _serialize_farmer_submission_detail(db, submission)


@router.post("/me/submissions/{submission_id}/resubmit")
def resubmit_own_submission(submission_id: str, body: FarmerSubmissionCorrectionIn,
                            user: User = Depends(require_roles("FARMER")), db: Session = Depends(get_session)):
    submission = db.query(FarmerSubmission).filter(
        FarmerSubmission.id == submission_id, FarmerSubmission.farmer_id == user.farmer_id).first()
    if not submission:
        raise HTTPException(404, "Not found")
    if db.query(FarmerSubmissionCorrection).filter(
        FarmerSubmissionCorrection.farmer_submission_id == submission_id,
        FarmerSubmissionCorrection.status == "PENDING",
    ).first():
        raise HTTPException(400, "A resubmission is already pending review for this submission")

    entries = [{**e, "farmer_id": user.farmer_id} for e in body.entries]
    _validate_entries_readonly(db, {user.farmer_id}, entries)

    correction = FarmerSubmissionCorrection(
        farmer_submission_id=submission_id, farmer_id=user.farmer_id, submitted_by_user_id=user.id,
        payload={"entries": entries},
    )
    db.add(correction)

    farmer = db.query(Farmer).filter(Farmer.id == user.farmer_id).first()
    da_ids = [u.id for u in db.query(User).filter(
        User.role == "DISTRICT_ADMIN", User.district_id == farmer.district_id, User.is_active).all()] if farmer else []
    if da_ids:
        create_notification(
            db, user, "Farmer resubmission pending review",
            f"{farmer.first_name} {farmer.last_name} submitted a correction for {submission.submission_month} — please review.",
            "SELECTED_DA", recipient_ids=da_ids,
        )
    db.commit()
    return {"correction_id": correction.id, "status": correction.status}


@router.post("/me/drafts")
def upsert_own_draft(body: FarmerDraftIn, user: User = Depends(require_roles("FARMER")),
                     db: Session = Depends(get_session)):
    member = db.query(FigMember).filter(FigMember.farmer_id == user.farmer_id, FigMember.is_active).first()
    if not member:
        raise HTTPException(400, "Only FIG members save a draft — a solo farmer submits directly")
    draft = db.query(FarmerDraftEntry).filter(
        FarmerDraftEntry.farmer_id == user.farmer_id, FarmerDraftEntry.draft_month == body.draft_month).first()
    if draft:
        draft.payload = {"entries": body.entries}
        draft.updated_at = _now()
    else:
        draft = FarmerDraftEntry(
            farmer_id=user.farmer_id, fig_id=member.fig_id, draft_month=body.draft_month,
            payload={"entries": body.entries},
        )
        db.add(draft)
    db.commit()
    return {"ok": True}


@router.get("/me/drafts")
def get_own_draft(month: str, user: User = Depends(require_roles("FARMER")), db: Session = Depends(get_session)):
    draft = db.query(FarmerDraftEntry).filter(
        FarmerDraftEntry.farmer_id == user.farmer_id, FarmerDraftEntry.draft_month == month).first()
    if not draft:
        return None
    return {"draft_month": draft.draft_month, "entries": draft.payload.get("entries") or [], "updated_at": draft.updated_at}


@router.get("/{farmer_id}")
def get_farmer(farmer_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    # Previously unscoped — any authenticated user of any role could fetch any farmer's
    # full record by id. Mirrors list_farmers' existing scoping ladder.
    if user.role == "DISTRICT_ADMIN" and f.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    if user.role == "FIG_PRESIDENT" and not db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.farmer_id == f.id, FigMember.is_active).first():
        raise HTTPException(403, "FIG scope mismatch")
    if user.role == "FARMER" and f.id != user.farmer_id:
        raise HTTPException(403, "Not your record")
    return public_farmer_dict(f)


@router.patch("/{farmer_id}")
def update_farmer(farmer_id: str, body: FarmerUpdateIn,
                  user: User = Depends(require_roles("DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and f.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    data = body.model_dump(exclude_unset=True)
    login = None
    if data.get("mobile_no") and data["mobile_no"] != f.mobile_no:
        if db.query(Farmer).filter(Farmer.mobile_no == data["mobile_no"], Farmer.id != farmer_id).first():
            raise HTTPException(400, "Mobile already registered")
        if db.query(User).filter(User.mobile_no == data["mobile_no"]).first():
            raise HTTPException(400, "Mobile already registered")
        login = db.query(User).filter(User.farmer_id == farmer_id).first()
        if login:
            login.mobile_no = data["mobile_no"]
    # Absent, None, or "" all mean "leave the Aadhaar unchanged" — the edit form PATCHes the
    # whole record, so an untouched masked field must never overwrite the stored value. There
    # is deliberately no clear-to-empty path.
    aadhaar_raw = data.pop("aadhaar_no", None)
    aadhaar_digits = None
    if aadhaar_raw:
        aadhaar_digits = _aadhaar_digits_or_400(aadhaar_raw)
        new_hash = aadhaar_hash(aadhaar_digits)
        if new_hash != f.aadhaar_hash and db.query(Farmer).filter(
                Farmer.aadhaar_hash == new_hash, Farmer.id != farmer_id).first():
            raise HTTPException(400, "Aadhaar already registered")
    if "stap_ids" in data:
        _require_output_staps(db, data["stap_ids"])
    for k, v in data.items():
        setattr(f, k, v)
    if aadhaar_digits:
        _set_aadhaar(f, aadhaar_digits)
    f.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(f)
    return public_farmer_dict(f)


@router.patch("/{farmer_id}/active")
def toggle_farmer(farmer_id: str, body: ActiveToggleIn,
                  user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and f.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    f.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": f.is_active}


@router.post("/{farmer_id}/reset-password")
def reset_farmer_password(farmer_id: str, body: FarmerPasswordResetIn,
                          user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                          db: Session = Depends(get_session)):
    f = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and f.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    login = db.query(User).filter(User.farmer_id == farmer_id).first()
    if not login:
        raise HTTPException(400, "This farmer does not have a login account yet")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    login.password_hash = hash_password(body.password)
    db.commit()
    return {"ok": True}
