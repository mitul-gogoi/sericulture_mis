"""District/State Admin visibility into solo-farmer submissions + the District-Admin-only
resubmission-correction approval workflow — the individual-farmer analog of meetings.py's
admin-facing Monthly Submission Status / Resubmission Requests sections."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_session
from app.core.deps import require_roles
from app.models import (
    Farmer, FarmerSubmission, FarmerSubmissionCorrection, User, Yield_, ByproductEntry,
    YieldInputEntry, Stock, _now,
)
from app.schemas import MeetingCorrectionRejectIn
from app.services.meeting_reports import (
    farmer_submission_rows, pending_farmer_corrections_rows, _serialize_farmer_submission_detail,
    serialize_farmer_correction_preview,
)
from app.services.stock import reverse_stock_for_yield, reverse_stock_for_byproduct
from app.services.notifications import create_notification
from app.routers.meetings import _apply_yield_entries, _validate_entries_readonly
from app.core.scope import active_district

router = APIRouter(prefix="/farmer-submissions", tags=["farmer_submissions"])

_PAGE_SIZES = {10, 20, 50, 100}


def _paginate(rows: list[dict], page: int, page_size: Optional[int]) -> dict:
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = len(rows)
    start = (page - 1) * size
    return {"items": rows[start:start + size], "total": total}


@router.get("")
def list_farmer_submissions(month: Optional[str] = None, page: int = Query(1, ge=1),
                            page_size: Optional[int] = None,
                            user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                            db: Session = Depends(get_session)):
    district_id = active_district(user) if user.role == "DISTRICT_ADMIN" else None
    rows = farmer_submission_rows(db, user.role, district_id, month)
    return _paginate(rows, page, page_size)


@router.get("/corrections/pending")
def get_pending_farmer_corrections(user: User = Depends(require_roles("DISTRICT_ADMIN")),
                                   db: Session = Depends(get_session)):
    return pending_farmer_corrections_rows(db, active_district(user))


def _submission_or_404_scoped(submission_id: str, user: User, db: Session) -> FarmerSubmission:
    submission = db.query(FarmerSubmission).filter(FarmerSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(404, "Submission not found")
    if user.role == "DISTRICT_ADMIN":
        farmer = db.query(Farmer).filter(Farmer.id == submission.farmer_id).first()
        if not farmer or farmer.district_id != active_district(user):
            raise HTTPException(403, "District scope mismatch")
    return submission


@router.get("/{submission_id}")
def get_farmer_submission_detail(submission_id: str, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                                 db: Session = Depends(get_session)):
    submission = _submission_or_404_scoped(submission_id, user, db)
    return _serialize_farmer_submission_detail(db, submission)


def _correction_or_404_scoped(correction_id: str, user: User, db: Session) -> tuple[FarmerSubmissionCorrection, FarmerSubmission]:
    correction = db.query(FarmerSubmissionCorrection).filter(FarmerSubmissionCorrection.id == correction_id).first()
    if not correction:
        raise HTTPException(404, "Correction not found")
    submission = _submission_or_404_scoped(correction.farmer_submission_id, user, db)
    return correction, submission


@router.get("/corrections/{correction_id}/preview")
def preview_farmer_correction(correction_id: str, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                              db: Session = Depends(get_session)):
    correction, submission = _correction_or_404_scoped(correction_id, user, db)
    return serialize_farmer_correction_preview(db, submission, correction)


@router.post("/corrections/{correction_id}/accept")
def accept_farmer_correction(correction_id: str, user: User = Depends(require_roles("DISTRICT_ADMIN")),
                             db: Session = Depends(get_session)):
    correction, submission = _correction_or_404_scoped(correction_id, user, db)
    if correction.status != "PENDING":
        raise HTTPException(400, f"This correction is not pending review (status: {correction.status})")

    payload_entries = [{**e, "farmer_id": submission.farmer_id} for e in (correction.payload.get("entries") or [])]

    old_yields = db.query(Yield_).filter(Yield_.farmer_submission_id == submission.id).all()
    old_yield_ids = [y.id for y in old_yields]
    old_byproducts = db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id.in_(old_yield_ids or [""])).all()
    old_byproduct_ids = [bp.id for bp in old_byproducts]
    for bp in old_byproducts:
        reverse_stock_for_byproduct(db, bp)
    for y in old_yields:
        reverse_stock_for_yield(db, y)
    db.query(Stock).filter(Stock.last_source_yield_id.in_(old_yield_ids or [""])) \
        .update({"last_source_yield_id": None}, synchronize_session=False)
    db.query(Stock).filter(Stock.last_source_byproduct_id.in_(old_byproduct_ids or [""])) \
        .update({"last_source_byproduct_id": None}, synchronize_session=False)
    db.query(YieldInputEntry).filter(YieldInputEntry.parent_yield_id.in_(old_yield_ids or [""])).delete(synchronize_session=False)
    db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id.in_(old_yield_ids or [""])).delete(synchronize_session=False)
    db.query(Yield_).filter(Yield_.farmer_submission_id == submission.id).delete(synchronize_session=False)

    _apply_yield_entries(db, payload_entries, yield_month=submission.submission_month,
                         fig_id=None, farmer_submission_id=submission.id)

    correction.status = "ACCEPTED"
    correction.reviewed_by_user_id = user.id
    correction.reviewed_at = _now()
    db.add(correction)

    create_notification(
        db, user, "Resubmission accepted",
        f"Your resubmission for {submission.submission_month} has been accepted.",
        "SELECTED_FARMER", recipient_ids=[correction.submitted_by_user_id],
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Duplicate yield for same activity-product/month")
    return {"ok": True, "status": correction.status}


@router.post("/corrections/{correction_id}/reject")
def reject_farmer_correction(correction_id: str, body: MeetingCorrectionRejectIn,
                             user: User = Depends(require_roles("DISTRICT_ADMIN")),
                             db: Session = Depends(get_session)):
    correction, submission = _correction_or_404_scoped(correction_id, user, db)
    if correction.status != "PENDING":
        raise HTTPException(400, f"This correction is not pending review (status: {correction.status})")

    correction.status = "REJECTED"
    correction.rejection_reason = body.rejection_reason
    correction.reviewed_by_user_id = user.id
    correction.reviewed_at = _now()
    db.add(correction)

    create_notification(
        db, user, "Resubmission rejected",
        f"Your resubmission for {submission.submission_month} was rejected: {body.rejection_reason}",
        "SELECTED_FARMER", recipient_ids=[correction.submitted_by_user_id],
    )
    db.commit()
    return {"ok": True, "status": correction.status}
