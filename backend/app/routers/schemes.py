"""Schemes + allocations + beneficiaries.

Scheme lifecycle: State Admin authors a scheme with targeting criteria (districts,
silk types, genders, farmer types, activities, beneficiary kind) and an optional
grants_asset_type_id; District Admin selects actual beneficiaries from the criteria-
matched candidate pool within their own district; publishing notifies targeted
FIG Presidents and District Admins.

Route ordering matters here: FastAPI matches path operations in registration order,
so every literal path (/allocations, /beneficiaries, /beneficiaries/bulk) MUST be
registered before the catch-all "/{scheme_id}" routes, or a request like
GET /schemes/beneficiaries would be swallowed by GET /schemes/{scheme_id} with
scheme_id="beneficiaries".
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.db import get_session, commit_or_conflict
from app.core.deps import get_current_user, require_roles
from app.models import Scheme, Allocation, Beneficiary, Farmer, Fig, User, AssetType, AssetInstance
from app.schemas import (
    SchemeIn, SchemeUpdateIn, AllocationIn, BeneficiaryIn, BeneficiaryBulkIn,
    BeneficiaryApprovalIn, BeneficiaryApprovalBulkIn,
)
from app.services.assets import check_asset_cooldown, resolve_owner_for_asset
from app.services.scheme_targeting import scheme_targets_district, candidate_farmers, candidate_figs
from app.services.notifications import create_notification

router = APIRouter(prefix="/schemes", tags=["schemes"])


class ActiveToggleIn(BaseModel):
    is_active: bool


def _scheme_or_404(db: Session, scheme_id: str) -> Scheme:
    s = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not s:
        raise HTTPException(404, "Scheme not found")
    return s


@router.post("")
def create_scheme(body: SchemeIn, user: User = Depends(require_roles("STATE_ADMIN")),
                  db: Session = Depends(get_session)):
    s = Scheme(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("")
def list_schemes(all: bool = False, include_archived: bool = False, q: Optional[str] = None,
                 support_type: Optional[str] = None,
                 user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    query = db.query(Scheme)
    if not include_archived:
        query = query.filter(Scheme.is_archived == False)  # noqa: E712
    if not all:
        query = query.filter(Scheme.is_active)
    if q:
        query = query.filter(Scheme.scheme_name.ilike(f"%{q}%"))
    if support_type:
        query = query.filter(Scheme.support_type == support_type)
    rows = query.order_by(Scheme.created_at.desc()).all()
    if user.role == "DISTRICT_ADMIN":
        rows = [s for s in rows if scheme_targets_district(s, user.district_id)]
    return rows


# ---------- Allocations (literal paths — must precede /{scheme_id}) ----------
@router.post("/allocations")
def create_allocation(body: AllocationIn, user: User = Depends(require_roles("STATE_ADMIN")),
                      db: Session = Depends(get_session)):
    scheme = _scheme_or_404(db, body.scheme_id)
    warning = None
    if scheme.total_budget_rs:
        already_allocated = db.query(func.sum(Allocation.allocated_amount_rs)).filter(
            Allocation.scheme_id == body.scheme_id).scalar() or 0
        total_after = already_allocated + body.allocated_amount_rs
        if total_after > scheme.total_budget_rs:
            over_by = total_after - scheme.total_budget_rs
            warning = f"Total allocations for this scheme now exceed its budget by ₹{over_by:,.2f}"
    a = Allocation(scheme_id=body.scheme_id, district_id=body.district_id,
                   allocated_amount_rs=body.allocated_amount_rs,
                   remaining=body.allocated_amount_rs)
    db.add(a)
    commit_or_conflict(db, "An allocation already exists for this scheme and district")
    db.refresh(a)
    return {"id": a.id, "warning": warning}


@router.get("/allocations")
def list_allocations(scheme_id: Optional[str] = None,
                     user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(Allocation)
    if scheme_id:
        q = q.filter(Allocation.scheme_id == scheme_id)
    if user.role == "DISTRICT_ADMIN":
        q = q.filter(Allocation.district_id == user.district_id)
    return q.all()


# ---------- Beneficiaries (literal paths — must precede /{scheme_id}) ----------
def _register_one(db: Session, scheme: Scheme, user: User, beneficiary_type: str,
                  farmer_id: Optional[str], fig_id: Optional[str], benefit_amount: float,
                  benefit_material: Optional[str], disbursement_date, remarks: Optional[str],
                  cooldown_override_reason: Optional[str]) -> Beneficiary:
    if beneficiary_type != scheme.beneficiary_kind:
        raise HTTPException(400, f"This scheme targets {scheme.beneficiary_kind} beneficiaries, not {beneficiary_type}")

    if beneficiary_type == "FARMER":
        if not farmer_id:
            raise HTTPException(400, "farmer_id is required for a farmer-beneficiary scheme")
        owner = db.query(Farmer).filter(Farmer.id == farmer_id).first()
        if not owner:
            raise HTTPException(404, "Farmer not found")
        district_id = owner.district_id
    else:
        if not fig_id:
            raise HTTPException(400, "fig_id is required for a FIG-beneficiary scheme")
        owner = db.query(Fig).filter(Fig.id == fig_id).first()
        if not owner:
            raise HTTPException(404, "FIG not found")
        district_id = owner.district_id

    if user.role == "DISTRICT_ADMIN" and district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if not scheme_targets_district(scheme, district_id):
        raise HTTPException(400, "This scheme does not target this district")

    alloc = db.query(Allocation).filter(Allocation.scheme_id == scheme.id,
                                        Allocation.district_id == district_id).first()
    if not alloc:
        raise HTTPException(400, "No budget allocation exists for this scheme in this district — allocate budget first")
    if benefit_amount > (alloc.remaining or 0):
        raise HTTPException(400, "Benefit amount exceeds the district's remaining allocation for this scheme")

    asset_type: Optional[AssetType] = None
    if scheme.grants_asset_type_id:
        asset_type = db.query(AssetType).filter(AssetType.id == scheme.grants_asset_type_id).first()
        cooldown_owner_type = "FIG" if beneficiary_type == "FIG" else "FARMER"
        cooldown_owner_id = fig_id if beneficiary_type == "FIG" else farmer_id
        cooldown = check_asset_cooldown(db, cooldown_owner_type, cooldown_owner_id, scheme.grants_asset_type_id)
        if not cooldown["eligible"] and not cooldown_override_reason:
            raise HTTPException(400, f"Cooldown not satisfied: {cooldown['reason']}. "
                                     f"Provide cooldown_override_reason to proceed anyway.")

    # Training-support-type schemes require State Admin approval before disbursement is
    # committed — the allocation-feasibility check above still applies at nomination time
    # (as a sanity check), but the actual debit + asset grant are deferred to approval
    # (_finalize_beneficiary_approval) so a rejected nomination has zero side effects.
    is_training = scheme.support_type == "Training"

    b = Beneficiary(scheme_id=scheme.id, beneficiary_type=beneficiary_type,
                    farmer_id=farmer_id if beneficiary_type == "FARMER" else None,
                    fig_id=fig_id if beneficiary_type == "FIG" else None,
                    district_id=district_id, benefit_amount=benefit_amount,
                    benefit_material=benefit_material, disbursement_date=disbursement_date,
                    remarks=remarks, cooldown_override_reason=cooldown_override_reason,
                    status="PENDING_APPROVAL" if is_training else "APPROVED",
                    created_by_user_id=user.id)
    db.add(b)
    db.flush()

    if is_training:
        return b

    alloc.utilised = (alloc.utilised or 0) + benefit_amount
    alloc.remaining = (alloc.remaining or 0) - benefit_amount

    if asset_type:
        try:
            owner_type, owner_id = resolve_owner_for_asset(db, asset_type, beneficiary_type, farmer_id, fig_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
        db.add(AssetInstance(
            asset_type_id=asset_type.id, owner_type=owner_type, owner_id=owner_id, quantity=1,
            acquisition_date=disbursement_date, acquisition_mode="SCHEME_DISBURSEMENT",
            scheme_id=scheme.id, beneficiary_id=b.id, created_by_user_id=user.id,
        ))
    return b


def _finalize_beneficiary_approval(db: Session, beneficiary: Beneficiary, scheme: Scheme, user: User) -> None:
    """Commits the disbursement a Training-scheme nomination represents — the same budget
    debit + asset grant that _register_one() applies immediately for Cash/Kind, just deferred
    here until a State Admin approves. Both the allocation and cooldown checks are re-run live
    (not reused from nomination time) since either could have shifted while the nomination sat
    pending."""
    alloc = db.query(Allocation).filter(Allocation.scheme_id == scheme.id,
                                        Allocation.district_id == beneficiary.district_id).first()
    if not alloc:
        raise HTTPException(400, "No budget allocation exists for this scheme in this district — allocate budget first")
    if beneficiary.benefit_amount > (alloc.remaining or 0):
        raise HTTPException(400, "Benefit amount exceeds the district's remaining allocation for this scheme")
    alloc.utilised = (alloc.utilised or 0) + beneficiary.benefit_amount
    alloc.remaining = (alloc.remaining or 0) - beneficiary.benefit_amount

    if scheme.grants_asset_type_id:
        asset_type = db.query(AssetType).filter(AssetType.id == scheme.grants_asset_type_id).first()
        cooldown_owner_type = "FIG" if beneficiary.beneficiary_type == "FIG" else "FARMER"
        cooldown_owner_id = beneficiary.fig_id if beneficiary.beneficiary_type == "FIG" else beneficiary.farmer_id
        cooldown = check_asset_cooldown(db, cooldown_owner_type, cooldown_owner_id, scheme.grants_asset_type_id)
        if not cooldown["eligible"] and not beneficiary.cooldown_override_reason:
            raise HTTPException(400, f"Cooldown not satisfied: {cooldown['reason']}. "
                                     f"The nomination did not include a cooldown_override_reason.")
        try:
            owner_type, owner_id = resolve_owner_for_asset(
                db, asset_type, beneficiary.beneficiary_type, beneficiary.farmer_id, beneficiary.fig_id)
        except ValueError as e:
            raise HTTPException(400, str(e))
        db.add(AssetInstance(
            asset_type_id=asset_type.id, owner_type=owner_type, owner_id=owner_id, quantity=1,
            acquisition_date=beneficiary.disbursement_date, acquisition_mode="SCHEME_DISBURSEMENT",
            scheme_id=scheme.id, beneficiary_id=beneficiary.id, created_by_user_id=user.id,
        ))

    beneficiary.status = "APPROVED"
    beneficiary.approved_by_user_id = user.id
    beneficiary.approved_at = datetime.now(timezone.utc)


def _notify_sa_of_nomination(db: Session, user: User, scheme: Scheme, count: int) -> None:
    if count <= 0:
        return
    create_notification(
        db, user, title=f"Training nomination submitted: {scheme.scheme_name}",
        details=f"{count} beneficiary nomination(s) for '{scheme.scheme_name}' are awaiting your approval.",
        recipient_type="ALL_SA",
    )


@router.post("/beneficiaries")
def register_beneficiary(body: BeneficiaryIn,
                         user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                         db: Session = Depends(get_session)):
    scheme = _scheme_or_404(db, body.scheme_id)
    b = _register_one(db, scheme, user, body.beneficiary_type, body.farmer_id, body.fig_id,
                      body.benefit_amount, body.benefit_material, body.disbursement_date,
                      body.remarks, body.cooldown_override_reason)
    if b.status == "PENDING_APPROVAL":
        _notify_sa_of_nomination(db, user, scheme, 1)
    db.commit()
    db.refresh(b)
    return {"id": b.id}


@router.post("/beneficiaries/bulk")
def register_beneficiaries_bulk(body: BeneficiaryBulkIn,
                                user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                                db: Session = Depends(get_session)):
    scheme = _scheme_or_404(db, body.scheme_id)
    created_ids = []
    errors = []
    pending_count = 0
    for i, item in enumerate(body.items):
        try:
            b = _register_one(db, scheme, user, item.beneficiary_type, item.farmer_id, item.fig_id,
                              item.benefit_amount, item.benefit_material, item.disbursement_date,
                              item.remarks, item.cooldown_override_reason)
            db.flush()
            created_ids.append(b.id)
            if b.status == "PENDING_APPROVAL":
                pending_count += 1
        except HTTPException as e:
            errors.append({"index": i, "detail": e.detail})
    _notify_sa_of_nomination(db, user, scheme, pending_count)
    db.commit()
    return {"created": created_ids, "errors": errors}


@router.post("/beneficiaries/approve/bulk")
def approve_beneficiaries_bulk(body: BeneficiaryApprovalBulkIn,
                               user: User = Depends(require_roles("STATE_ADMIN")),
                               db: Session = Depends(get_session)):
    approved_ids = []
    errors = []
    notify_da_ids: set[str] = set()
    for bid in body.beneficiary_ids:
        try:
            b = db.query(Beneficiary).filter(Beneficiary.id == bid).first()
            if not b:
                raise HTTPException(404, "Beneficiary not found")
            if b.status != "PENDING_APPROVAL":
                raise HTTPException(400, f"Not pending approval (status: {b.status})")
            scheme = _scheme_or_404(db, b.scheme_id)
            _finalize_beneficiary_approval(db, b, scheme, user)
            db.flush()
            approved_ids.append(bid)
            if b.created_by_user_id:
                notify_da_ids.add(b.created_by_user_id)
        except HTTPException as e:
            errors.append({"beneficiary_id": bid, "detail": e.detail})
    if notify_da_ids:
        create_notification(
            db, user, title="Training nomination(s) approved",
            details=f"{len(approved_ids)} of your nominated beneficiaries have been approved.",
            recipient_type="SELECTED_DA", recipient_ids=list(notify_da_ids),
        )
    db.commit()
    return {"approved": approved_ids, "errors": errors}


@router.post("/beneficiaries/{beneficiary_id}/approve")
def approve_beneficiary(beneficiary_id: str, user: User = Depends(require_roles("STATE_ADMIN")),
                        db: Session = Depends(get_session)):
    b = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not b:
        raise HTTPException(404, "Beneficiary not found")
    if b.status != "PENDING_APPROVAL":
        raise HTTPException(400, f"This beneficiary is not pending approval (status: {b.status})")
    scheme = _scheme_or_404(db, b.scheme_id)
    _finalize_beneficiary_approval(db, b, scheme, user)
    if b.created_by_user_id:
        create_notification(
            db, user, title=f"Nomination approved: {scheme.scheme_name}",
            details=f"Your nomination for '{scheme.scheme_name}' has been approved.",
            recipient_type="SELECTED_DA", recipient_ids=[b.created_by_user_id],
        )
    db.commit()
    return {"ok": True, "status": b.status}


@router.post("/beneficiaries/{beneficiary_id}/reject")
def reject_beneficiary(beneficiary_id: str, body: BeneficiaryApprovalIn,
                       user: User = Depends(require_roles("STATE_ADMIN")),
                       db: Session = Depends(get_session)):
    b = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id).first()
    if not b:
        raise HTTPException(404, "Beneficiary not found")
    if b.status != "PENDING_APPROVAL":
        raise HTTPException(400, f"This beneficiary is not pending approval (status: {b.status})")
    if not body.rejection_reason:
        raise HTTPException(400, "rejection_reason is required")
    scheme = _scheme_or_404(db, b.scheme_id)
    b.status = "REJECTED"
    b.rejection_reason = body.rejection_reason
    b.approved_by_user_id = user.id
    b.approved_at = datetime.now(timezone.utc)
    if b.created_by_user_id:
        create_notification(
            db, user, title=f"Nomination rejected: {scheme.scheme_name}",
            details=f"Your nomination for '{scheme.scheme_name}' was rejected: {body.rejection_reason}",
            recipient_type="SELECTED_DA", recipient_ids=[b.created_by_user_id],
        )
    db.commit()
    return {"ok": True, "status": b.status}


@router.get("/beneficiaries")
def list_beneficiaries(scheme_id: Optional[str] = None, status: Optional[str] = None,
                       user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(Beneficiary)
    if scheme_id:
        q = q.filter(Beneficiary.scheme_id == scheme_id)
    if status:
        q = q.filter(Beneficiary.status == status)
    if user.role == "DISTRICT_ADMIN":
        q = q.filter(Beneficiary.district_id == user.district_id)
    rows = q.order_by(Beneficiary.created_at.desc()).limit(500).all()
    farmer_ids = [b.farmer_id for b in rows if b.farmer_id]
    fig_ids = [b.fig_id for b in rows if b.fig_id]
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    figs = {g.id: g for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}
    out = []
    for b in rows:
        d = b.model_dump()
        if b.farmer_id and farmers.get(b.farmer_id):
            fr = farmers[b.farmer_id]
            d["farmer"] = {"id": fr.id, "first_name": fr.first_name, "last_name": fr.last_name,
                           "farmer_code": fr.farmer_code}
        if b.fig_id and figs.get(b.fig_id):
            fg = figs[b.fig_id]
            d["fig"] = {"id": fg.id, "fig_name": fg.fig_name, "fig_code": fg.fig_code}
        out.append(d)
    return out


# ---------- Single-scheme routes (catch-all — must come LAST) ----------
@router.get("/{scheme_id}")
def get_scheme(scheme_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    s = _scheme_or_404(db, scheme_id)
    if user.role == "DISTRICT_ADMIN" and not scheme_targets_district(s, user.district_id):
        raise HTTPException(403, "This scheme does not target your district")
    return s


@router.patch("/{scheme_id}")
def update_scheme(scheme_id: str, body: SchemeUpdateIn,
                  user: User = Depends(require_roles("STATE_ADMIN")),
                  db: Session = Depends(get_session)):
    s = _scheme_or_404(db, scheme_id)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    s.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(s)
    return s


@router.patch("/{scheme_id}/active")
def toggle_scheme(scheme_id: str, body: ActiveToggleIn,
                  user: User = Depends(require_roles("STATE_ADMIN")),
                  db: Session = Depends(get_session)):
    s = _scheme_or_404(db, scheme_id)
    s.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": s.is_active}


@router.patch("/{scheme_id}/archive")
def archive_scheme(scheme_id: str, user: User = Depends(require_roles("STATE_ADMIN")),
                   db: Session = Depends(get_session)):
    s = _scheme_or_404(db, scheme_id)
    if s.is_active:
        raise HTTPException(400, "Deactivate this scheme before archiving it")
    s.is_archived = True
    s.archived_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "is_archived": True}


@router.post("/{scheme_id}/publish")
def publish_scheme(scheme_id: str, user: User = Depends(require_roles("STATE_ADMIN")),
                   db: Session = Depends(get_session)):
    s = _scheme_or_404(db, scheme_id)
    q = db.query(User).filter(User.role.in_(["FIG_PRESIDENT", "DISTRICT_ADMIN"]), User.is_active)
    if not s.target_all_districts:
        q = q.filter(User.district_id.in_(s.target_district_ids or [""]))
    recipient_ids = [u.id for u in q.all()]

    result = create_notification(
        db, user, title=f"New Scheme: {s.scheme_name}",
        details=(s.description or f"A new scheme '{s.scheme_name}' is now available."),
        recipient_type="SELECTED_DA_AND_FP", recipient_ids=recipient_ids,
    )
    s.notified_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "notified": result["sent_to"]}


@router.get("/{scheme_id}/candidates")
def scheme_candidates(scheme_id: str, user: User = Depends(require_roles("DISTRICT_ADMIN")),
                      db: Session = Depends(get_session)):
    s = _scheme_or_404(db, scheme_id)
    if not scheme_targets_district(s, user.district_id):
        raise HTTPException(403, "This scheme does not target your district")
    if s.beneficiary_kind == "FIG":
        return {"beneficiary_kind": "FIG", "candidates": candidate_figs(db, s, user.district_id)}
    return {"beneficiary_kind": "FARMER", "candidates": candidate_farmers(db, s, user.district_id)}
