"""Meetings + Yields."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.services.fiscal import fy_to_months
from app.services.stock import (
    upsert_stock_for_yield, upsert_stock_for_byproduct,
    reverse_stock_for_yield, reverse_stock_for_byproduct,
)
from app.services.notifications import create_notification
from app.services.meeting_reports import (
    submission_status_rows, fp_submission_history_rows, pending_corrections_rows,
)
from app.models import (
    Meeting, Attendance, Yield_, Fig, Farmer, FigMember, User, MeetingCorrection, Stock,
    SilkTypeActivityProduct, Product, ByproductEntry, YieldInputEntry, Scheme,
    InputSourceType, StapSourceType, Activity, LossReason, FarmerDraftEntry, _now,
)
from app.schemas import MeetingIn, MeetingCorrectionIn, MeetingCorrectionRejectIn
from app.core.scope import active_district

router = APIRouter(tags=["meetings_yields"])

_PAGE_SIZES = {10, 20, 50, 100}


def _paginate(rows: list[dict], page: int, page_size: Optional[int]) -> dict:
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = len(rows)
    start = (page - 1) * size
    return {"items": rows[start:start + size], "total": total}


def _month(d) -> str:
    return d.isoformat()[:7]


def _create_byproducts(db: Session, parent: Yield_, entries: list[dict]) -> list[ByproductEntry]:
    created: list[ByproductEntry] = []
    for e in entries:
        product = db.query(Product).filter(Product.id == e["product_id"]).first()
        if not product or not product.is_byproduct:
            raise HTTPException(400, f"Product {e.get('product_id')} is not a byproduct")
        qty = float(e.get("quantity", 0) or 0)
        if qty <= 0:
            continue
        planned = float(e.get("planned_quantity", 0) or 0)
        loss_reason_id = e.get("loss_reason_id") or None
        if planned > 0 and qty < planned * 0.5 and not loss_reason_id:
            raise HTTPException(400, f"Loss reason required for byproduct {product.id} on farmer {parent.farmer_id}")
        sold_qty = float(e.get("sold_quantity", 0) or 0)
        sold_rate = float(e.get("sold_rate", 0) or 0)
        row = ByproductEntry(
            parent_yield_id=parent.id, farmer_id=parent.farmer_id, fig_id=parent.fig_id,
            district_id=parent.district_id, seri_circle_id=parent.seri_circle_id,
            product_id=product.id, yield_month=parent.yield_month, unit_of_measure=product.unit_of_measure,
            quantity=qty, planned_quantity=planned,
            next_month_plan=float(e.get("next_month_plan", 0) or 0),
            stock_balance=float(e.get("stock_balance", 0) or 0),
            sold_quantity=sold_qty, sold_rate=sold_rate, earning=sold_qty * sold_rate,
            loss_reason_id=loss_reason_id, remarks=e.get("remarks", "") or "",
        )
        db.add(row)
        created.append(row)
    if created:
        db.flush()
        for row in created:
            upsert_stock_for_byproduct(db, row)
    return created


def _create_inputs(db: Session, parent: Yield_, stap: Optional[SilkTypeActivityProduct],
                   entries: list[dict]) -> list[YieldInputEntry]:
    created: list[YieldInputEntry] = []
    for e in entries:
        product = db.query(Product).filter(Product.id == e["product_id"]).first()
        valid_input = stap and db.query(SilkTypeActivityProduct).filter(
            SilkTypeActivityProduct.silk_type_id == stap.silk_type_id,
            SilkTypeActivityProduct.activity_id == stap.activity_id,
            SilkTypeActivityProduct.product_id == e.get("product_id"),
            SilkTypeActivityProduct.role == "INPUT",
            SilkTypeActivityProduct.is_active,
        ).first()
        if not product or not valid_input:
            raise HTTPException(400, f"Product {e.get('product_id')} is not a valid input for this activity")
        qty = float(e.get("quantity", 0) or 0)
        if qty <= 0:
            continue
        source_type_id = e.get("source_type_id")
        source_type = db.query(InputSourceType).filter(InputSourceType.id == source_type_id, InputSourceType.is_active).first()
        if not source_type:
            raise HTTPException(400, f"Invalid source_type_id: {source_type_id}")
        configured_ids = {sst.source_type_id for sst in db.query(StapSourceType).filter(StapSourceType.stap_id == valid_input.id).all()}
        # Mirrors master.py's stap_options._allowed_source_types 3-tier fallback exactly:
        # explicit StapSourceType config > the mapping's input_source_category_id > any active type.
        if configured_ids:
            if source_type.id not in configured_ids:
                raise HTTPException(400, f"'{source_type.source_name}' is not a valid source for {product.product_name}")
        elif valid_input.input_source_category_id:
            if source_type.category_id != valid_input.input_source_category_id:
                raise HTTPException(400, f"'{source_type.source_name}' is not a valid source for {product.product_name} (wrong category)")
        scheme_id = e.get("scheme_id") or None
        if source_type.requires_scheme:
            if not scheme_id:
                raise HTTPException(400, f"scheme_id is required when source_type is '{source_type.source_name}'")
            scheme = db.query(Scheme).filter(Scheme.id == scheme_id, Scheme.is_active).first()
            if not scheme:
                raise HTTPException(400, f"Scheme {scheme_id} not found or inactive")
        else:
            scheme_id = None
        row = YieldInputEntry(
            parent_yield_id=parent.id, farmer_id=parent.farmer_id, fig_id=parent.fig_id,
            district_id=parent.district_id, seri_circle_id=parent.seri_circle_id,
            product_id=product.id, yield_month=parent.yield_month, unit_of_measure=product.unit_of_measure,
            quantity=qty, source_type_id=source_type.id, scheme_id=scheme_id, remarks=e.get("remarks", "") or "",
        )
        db.add(row)
        created.append(row)
    return created


def _apply_yield_entries(db: Session, entries: list[dict], *, yield_month: str, fig_id: Optional[str],
                         meeting_id: Optional[str] = None, farmer_submission_id: Optional[str] = None) -> list[Yield_]:
    """Creates Yield_/ByproductEntry/YieldInputEntry rows (with Stock deltas) from raw entry
    dicts — the same shape MeetingIn's body uses. Shared by the FIG-meeting submission path
    (linked via meeting_id) and the solo-farmer submission path (linked via farmer_submission_id)
    so both run the exact same validation (including the loss-reason-required rule) exactly once,
    not two drifting copies. Exactly one of meeting_id/farmer_submission_id is set per call."""
    farmer_ids = {e["farmer_id"] for e in entries}
    stap_ids = {e["stap_id"] for e in entries}
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    staps = {s.id: s for s in db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id.in_(stap_ids or [""])).all()}

    created: list[Yield_] = []
    for e in entries:
        farmer = farmers.get(e["farmer_id"])
        stap = staps.get(e["stap_id"])
        if not farmer or not stap:
            db.rollback()
            raise HTTPException(400, f"Invalid farmer or activity for entry {e.get('farmer_id')}")
        if e["stap_id"] not in (farmer.stap_ids or []):
            db.rollback()
            raise HTTPException(400, f"Activity {e['stap_id']} is not assigned to farmer {farmer.id}")
        sold_qty = float(e.get("sold_qty", 0) or 0)
        sold_rate = float(e.get("sold_rate", 0) or 0)
        actual = float(e.get("actual", 0) or 0)
        planned = float(e.get("planned", 0) or 0)
        loss_reason_id = e.get("loss_reason_id") or None
        if planned > 0 and actual < planned * 0.5 and not loss_reason_id:
            db.rollback()
            raise HTTPException(400, f"Loss reason required for farmer {farmer.id}")
        row = Yield_(
            fig_id=fig_id, farmer_id=farmer.id, stap_id=stap.id,
            activity_id=stap.activity_id, product_id=stap.product_id,
            meeting_id=meeting_id, farmer_submission_id=farmer_submission_id,
            district_id=farmer.district_id, seri_circle_id=farmer.seri_circle_id,
            yield_month=yield_month,
            planned_yield=planned, actual_yield=actual,
            next_month_plan=float(e.get("next_plan", 0) or 0),
            stock_balance=float(e.get("stock", 0) or 0),
            sold_quantity=sold_qty, sold_rate=sold_rate, earning=sold_qty * sold_rate,
            loss_reason_id=loss_reason_id, remarks=e.get("remarks", "") or "",
        )
        db.add(row)
        db.flush()
        upsert_stock_for_yield(db, row)
        _create_byproducts(db, row, e.get("byproducts") or [])
        _create_inputs(db, row, stap, e.get("inputs") or [])
        created.append(row)
    return created


def _apply_meeting_entries(db: Session, meeting: Meeting, attendance: list[dict], entries: list[dict]) -> list[Yield_]:
    """Attendance roll-call + delegates the actual entry-creation loop to _apply_yield_entries —
    kept separate because attendance/present-filtering is a FIG-meeting-only concept that doesn't
    apply to a solo farmer's own submission."""
    present_ids: set[str] = set()
    for a in attendance:
        db.add(Attendance(meeting_id=meeting.id, fig_id=meeting.fig_id,
                          farmer_id=a["farmer_id"], is_present=bool(a.get("is_present", False))))
        if a.get("is_present"):
            present_ids.add(a["farmer_id"])

    present_entries = [e for e in entries if e["farmer_id"] in present_ids]
    return _apply_yield_entries(db, present_entries, yield_month=meeting.meeting_month,
                                fig_id=meeting.fig_id, meeting_id=meeting.id)


@router.post("/meetings")
def submit_meeting(body: MeetingIn, user: User = Depends(require_roles("FIG_PRESIDENT")),
                   db: Session = Depends(get_session)):
    if body.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    fig = db.query(Fig).filter(Fig.id == body.fig_id).first()
    if not fig:
        raise HTTPException(404, "FIG not found")
    m_month = _month(body.meeting_date)
    if db.query(Meeting).filter(Meeting.fig_id == body.fig_id, Meeting.meeting_month == m_month).first():
        raise HTTPException(400, "Meeting already submitted for this month")
    meeting = Meeting(
        fig_id=body.fig_id, meeting_title=body.meeting_title, meeting_date=body.meeting_date,
        meeting_time=body.meeting_time or "", meeting_venue=body.meeting_venue,
        meeting_details=body.meeting_details, minutes_path=body.minutes_path,
        next_meeting_date=body.next_meeting_date, meeting_month=m_month,
    )
    db.add(meeting)
    db.flush()

    created = _apply_meeting_entries(db, meeting, body.attendance, body.entries)
    _consume_fig_drafts(db, meeting.fig_id, m_month)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Duplicate yield for same farmer/activity-product/month")
    return {
        "meeting_id": meeting.id, "entries_count": len(created),
        "entries": [{"id": r.id, "farmer_id": r.farmer_id, "stap_id": r.stap_id} for r in created],
    }


@router.get("/meetings")
def list_meetings(fig_id: Optional[str] = None, month: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(Meeting)
    if user.role == "FIG_PRESIDENT":
        q = q.filter(Meeting.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig).filter(Fig.district_id == active_district(user)).all()]
        q = q.filter(Meeting.fig_id.in_(fig_ids or [""]))
        if fig_id:
            q = q.filter(Meeting.fig_id == fig_id)
    elif fig_id:
        q = q.filter(Meeting.fig_id == fig_id)
    if month:
        q = q.filter(Meeting.meeting_month == month)
    return q.order_by(Meeting.meeting_date.desc()).all()


@router.get("/meetings/submission-status")
def get_submission_status(month: str, page: int = Query(1, ge=1), page_size: Optional[int] = None,
                          user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                          db: Session = Depends(get_session)):
    district_id = active_district(user) if user.role == "DISTRICT_ADMIN" else None
    rows = submission_status_rows(db, user.role, district_id, month)
    return _paginate(rows, page, page_size)


@router.get("/meetings/submission-history")
def get_submission_history(page: int = Query(1, ge=1), page_size: Optional[int] = None,
                           user: User = Depends(require_roles("FIG_PRESIDENT")),
                           db: Session = Depends(get_session)):
    rows = fp_submission_history_rows(db, user.fig_id)
    return _paginate(rows, page, page_size)


@router.get("/meetings/corrections/pending")
def get_pending_corrections(user: User = Depends(require_roles("STATE_ADMIN")), db: Session = Depends(get_session)):
    return pending_corrections_rows(db)


@router.get("/meetings/drafts")
def get_fig_drafts(fig_id: str, month: str, user: User = Depends(require_roles("FIG_PRESIDENT")),
                   db: Session = Depends(get_session)):
    if fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    drafts = db.query(FarmerDraftEntry).filter(
        FarmerDraftEntry.fig_id == fig_id, FarmerDraftEntry.draft_month == month).all()
    return {d.farmer_id: (d.payload.get("entries") or []) for d in drafts}


def _consume_fig_drafts(db: Session, fig_id: str, month: str) -> None:
    """Deletes every FIG member's staged draft for this FIG+month once the FIG President's real
    Meeting for that month is (re)submitted — the draft's whole purpose was to feed the wizard's
    pre-fill, and it has now been superseded by live data."""
    db.query(FarmerDraftEntry).filter(
        FarmerDraftEntry.fig_id == fig_id, FarmerDraftEntry.draft_month == month
    ).delete(synchronize_session=False)


def _serialize_meeting_detail(db: Session, meeting: Meeting) -> dict:
    fig = db.query(Fig).filter(Fig.id == meeting.fig_id).first()

    attendance_rows = db.query(Attendance).filter(Attendance.meeting_id == meeting.id).all()
    yield_rows = db.query(Yield_).filter(Yield_.meeting_id == meeting.id).all()
    yield_ids = [y.id for y in yield_rows]
    byproduct_rows = db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id.in_(yield_ids or [""])).all()
    input_rows = db.query(YieldInputEntry).filter(YieldInputEntry.parent_yield_id.in_(yield_ids or [""])).all()

    farmer_ids = {a.farmer_id for a in attendance_rows} | {y.farmer_id for y in yield_rows}
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    activities = {a.id: a.activity_name for a in db.query(Activity).filter(
        Activity.id.in_({y.activity_id for y in yield_rows if y.activity_id} or [""])).all()}
    product_ids = ({y.product_id for y in yield_rows if y.product_id}
                   | {b.product_id for b in byproduct_rows} | {i.product_id for i in input_rows})
    products = {p.id: p.product_name for p in db.query(Product).filter(Product.id.in_(product_ids or [""])).all()}
    loss_reason_ids = ({y.loss_reason_id for y in yield_rows if y.loss_reason_id}
                        | {b.loss_reason_id for b in byproduct_rows if b.loss_reason_id})
    loss_reasons = {r.id: r.reason_name for r in db.query(LossReason).filter(LossReason.id.in_(loss_reason_ids or [""])).all()}
    source_types = {s.id: s.source_name for s in db.query(InputSourceType).filter(
        InputSourceType.id.in_({i.source_type_id for i in input_rows if i.source_type_id} or [""])).all()}
    schemes = {s.id: s.scheme_name for s in db.query(Scheme).filter(
        Scheme.id.in_({i.scheme_id for i in input_rows if i.scheme_id} or [""])).all()}

    def _farmer_name(farmer_id: str) -> str:
        f = farmers.get(farmer_id)
        return f"{f.first_name} {f.last_name}" if f else "—"

    byproducts_by_yield: dict[str, list[dict]] = {}
    for b in byproduct_rows:
        byproducts_by_yield.setdefault(b.parent_yield_id, []).append({
            "product_id": b.product_id, "product_name": products.get(b.product_id, "—"),
            "quantity": b.quantity, "planned_quantity": b.planned_quantity,
            "next_month_plan": b.next_month_plan, "stock_balance": b.stock_balance,
            "sold_quantity": b.sold_quantity, "sold_rate": b.sold_rate, "earning": b.earning,
            "loss_reason_id": b.loss_reason_id, "loss_reason_name": loss_reasons.get(b.loss_reason_id),
        })

    inputs_by_yield: dict[str, list[dict]] = {}
    for i in input_rows:
        inputs_by_yield.setdefault(i.parent_yield_id, []).append({
            "product_id": i.product_id, "product_name": products.get(i.product_id, "—"), "quantity": i.quantity,
            "unit_of_measure": i.unit_of_measure,
            "source_type_id": i.source_type_id, "source_type_name": source_types.get(i.source_type_id),
            "scheme_id": i.scheme_id, "scheme_name": schemes.get(i.scheme_id),
        })

    entries = [
        {
            "farmer_id": y.farmer_id, "farmer_name": _farmer_name(y.farmer_id),
            "stap_id": y.stap_id, "activity_name": activities.get(y.activity_id, "—"),
            "is_primary_stage": y.is_primary_stage,
            "output": {
                "product_name": products.get(y.product_id, "—"),
                "planned_yield": y.planned_yield, "actual_yield": y.actual_yield,
                "next_month_plan": y.next_month_plan, "stock_balance": y.stock_balance,
                "sold_quantity": y.sold_quantity, "sold_rate": y.sold_rate, "earning": y.earning,
                "loss_reason_id": y.loss_reason_id, "loss_reason_name": loss_reasons.get(y.loss_reason_id),
            },
            "byproducts": byproducts_by_yield.get(y.id, []),
            "inputs": inputs_by_yield.get(y.id, []),
        }
        for y in yield_rows
    ]

    return {
        "meeting": {
            "id": meeting.id, "fig_id": meeting.fig_id, "fig_name": fig.fig_name if fig else "—",
            "meeting_title": meeting.meeting_title, "meeting_date": meeting.meeting_date,
            "meeting_time": meeting.meeting_time, "meeting_venue": meeting.meeting_venue,
            "meeting_details": meeting.meeting_details, "minutes_path": meeting.minutes_path,
            "next_meeting_date": meeting.next_meeting_date, "meeting_month": meeting.meeting_month,
            "submitted_at": meeting.submitted_at,
        },
        "attendance": [
            {"farmer_id": a.farmer_id, "farmer_name": _farmer_name(a.farmer_id),
             "mobile": farmers[a.farmer_id].mobile_no if a.farmer_id in farmers else "",
             "is_present": a.is_present}
            for a in attendance_rows
        ],
        "entries": entries,
    }


def _meeting_or_404_scoped(meeting_id: str, user: User, db: Session) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    if user.role == "FIG_PRESIDENT" and meeting.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    if user.role == "FARMER":
        member = db.query(FigMember).filter(
            FigMember.farmer_id == user.farmer_id, FigMember.fig_id == meeting.fig_id, FigMember.is_active).first()
        if not member:
            raise HTTPException(403, "FIG scope mismatch")
    if user.role == "DISTRICT_ADMIN":
        fig = db.query(Fig).filter(Fig.id == meeting.fig_id).first()
        if not fig or fig.district_id != active_district(user):
            raise HTTPException(403, "District scope mismatch")
    return meeting


@router.get("/meetings/{meeting_id}")
def get_meeting_detail(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    meeting = _meeting_or_404_scoped(meeting_id, user, db)
    return _serialize_meeting_detail(db, meeting)


def _validate_entries_readonly(db: Session, present_ids: set[str], entries: list[dict]) -> None:
    """Read-only pass over the same core validation submit_meeting enforces (farmer/activity
    existence, assignment, and the loss-reason-required rule) — used to fail fast when a
    correction is queued, without writing anything (the authoritative, full validation — including
    the byproduct/input-specific rules — still runs for real inside _apply_meeting_entries at
    accept time, safely rolling back if it fails there instead)."""
    present_entries = [e for e in entries if e["farmer_id"] in present_ids]
    farmer_ids = {e["farmer_id"] for e in present_entries}
    stap_ids = {e["stap_id"] for e in present_entries}
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    staps = {s.id: s for s in db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id.in_(stap_ids or [""])).all()}
    for e in present_entries:
        farmer = farmers.get(e["farmer_id"])
        stap = staps.get(e["stap_id"])
        if not farmer or not stap:
            raise HTTPException(400, f"Invalid farmer or activity for entry {e.get('farmer_id')}")
        if e["stap_id"] not in (farmer.stap_ids or []):
            raise HTTPException(400, f"Activity {e['stap_id']} is not assigned to farmer {farmer.id}")
        actual = float(e.get("actual", 0) or 0)
        planned = float(e.get("planned", 0) or 0)
        if planned > 0 and actual < planned * 0.5 and not (e.get("loss_reason_id") or None):
            raise HTTPException(400, f"Loss reason required for farmer {farmer.id}")


def _serialize_correction_preview(db: Session, meeting: Meeting, correction: MeetingCorrection) -> dict:
    """Normalizes a pending correction's raw payload into the exact same response shape
    _serialize_meeting_detail returns, so the frontend can feed either into the same shared
    read-only detail component."""
    payload = correction.payload
    attendance_raw = payload.get("attendance") or []
    entries_raw = payload.get("entries") or []
    fig = db.query(Fig).filter(Fig.id == meeting.fig_id).first()

    farmer_ids = {a["farmer_id"] for a in attendance_raw} | {e["farmer_id"] for e in entries_raw}
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    stap_ids = {e["stap_id"] for e in entries_raw}
    staps = {s.id: s for s in db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id.in_(stap_ids or [""])).all()}
    activities = {a.id: a.activity_name for a in db.query(Activity).filter(
        Activity.id.in_({s.activity_id for s in staps.values() if s.activity_id} or [""])).all()}

    product_ids: set[str] = {s.product_id for s in staps.values() if s.product_id}
    for e in entries_raw:
        product_ids |= {b.get("product_id") for b in (e.get("byproducts") or []) if b.get("product_id")}
        product_ids |= {i.get("product_id") for i in (e.get("inputs") or []) if i.get("product_id")}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids or [""])).all()}

    loss_reason_ids: set[str] = set()
    for e in entries_raw:
        if e.get("loss_reason_id"):
            loss_reason_ids.add(e["loss_reason_id"])
        loss_reason_ids |= {b.get("loss_reason_id") for b in (e.get("byproducts") or []) if b.get("loss_reason_id")}
    loss_reasons = {r.id: r.reason_name for r in db.query(LossReason).filter(LossReason.id.in_(loss_reason_ids or [""])).all()}

    source_type_ids = {i.get("source_type_id") for e in entries_raw for i in (e.get("inputs") or []) if i.get("source_type_id")}
    source_types = {s.id: s.source_name for s in db.query(InputSourceType).filter(InputSourceType.id.in_(source_type_ids or [""])).all()}
    scheme_ids = {i.get("scheme_id") for e in entries_raw for i in (e.get("inputs") or []) if i.get("scheme_id")}
    schemes = {s.id: s.scheme_name for s in db.query(Scheme).filter(Scheme.id.in_(scheme_ids or [""])).all()}

    def _farmer_name(fid: str) -> str:
        f = farmers.get(fid)
        return f"{f.first_name} {f.last_name}" if f else "—"

    def _product_name(pid: Optional[str]) -> str:
        p = products.get(pid)
        return p.product_name if p else "—"

    entries = []
    for e in entries_raw:
        stap = staps.get(e["stap_id"])
        farmer = farmers.get(e["farmer_id"])
        sold_qty = float(e.get("sold_qty", 0) or 0)
        sold_rate = float(e.get("sold_rate", 0) or 0)
        entries.append({
            "farmer_id": e["farmer_id"], "farmer_name": _farmer_name(e["farmer_id"]),
            "stap_id": e["stap_id"], "activity_name": activities.get(stap.activity_id, "—") if stap else "—",
            "output": {
                "product_name": _product_name(stap.product_id) if stap else "—",
                "planned_yield": float(e.get("planned", 0) or 0), "actual_yield": float(e.get("actual", 0) or 0),
                "next_month_plan": float(e.get("next_plan", 0) or 0), "stock_balance": float(e.get("stock", 0) or 0),
                "sold_quantity": sold_qty, "sold_rate": sold_rate, "earning": sold_qty * sold_rate,
                "loss_reason_id": e.get("loss_reason_id"), "loss_reason_name": loss_reasons.get(e.get("loss_reason_id")),
            },
            "byproducts": [
                {
                    "product_id": b.get("product_id"), "product_name": _product_name(b.get("product_id")),
                    "quantity": float(b.get("quantity", 0) or 0), "planned_quantity": float(b.get("planned_quantity", 0) or 0),
                    "next_month_plan": float(b.get("next_month_plan", 0) or 0), "stock_balance": float(b.get("stock_balance", 0) or 0),
                    "sold_quantity": float(b.get("sold_quantity", 0) or 0), "sold_rate": float(b.get("sold_rate", 0) or 0),
                    "earning": float(b.get("sold_quantity", 0) or 0) * float(b.get("sold_rate", 0) or 0),
                    "loss_reason_id": b.get("loss_reason_id"), "loss_reason_name": loss_reasons.get(b.get("loss_reason_id")),
                }
                for b in (e.get("byproducts") or [])
            ],
            "inputs": [
                {
                    "product_id": i.get("product_id"), "product_name": _product_name(i.get("product_id")),
                    "quantity": float(i.get("quantity", 0) or 0),
                    "unit_of_measure": products[i["product_id"]].unit_of_measure if i.get("product_id") in products else "",
                    "source_type_id": i.get("source_type_id"), "source_type_name": source_types.get(i.get("source_type_id")),
                    "scheme_id": i.get("scheme_id"), "scheme_name": schemes.get(i.get("scheme_id")),
                }
                for i in (e.get("inputs") or [])
            ],
        })

    meeting_date = payload.get("meeting_date") or ""
    return {
        "meeting": {
            "id": meeting.id, "fig_id": meeting.fig_id, "fig_name": fig.fig_name if fig else "—",
            "meeting_title": payload.get("meeting_title"), "meeting_date": meeting_date,
            "meeting_time": payload.get("meeting_time"), "meeting_venue": payload.get("meeting_venue"),
            "meeting_details": payload.get("meeting_details"), "minutes_path": payload.get("minutes_path"),
            "next_meeting_date": payload.get("next_meeting_date"), "meeting_month": meeting_date[:7],
            "submitted_at": correction.submitted_at,
        },
        "attendance": [
            {"farmer_id": a["farmer_id"], "farmer_name": _farmer_name(a["farmer_id"]),
             "mobile": farmers[a["farmer_id"]].mobile_no if a["farmer_id"] in farmers else "",
             "is_present": bool(a.get("is_present", False))}
            for a in attendance_raw
        ],
        "entries": entries,
    }


@router.post("/meetings/{meeting_id}/corrections")
def submit_correction(meeting_id: str, body: MeetingCorrectionIn,
                      user: User = Depends(require_roles("FIG_PRESIDENT")),
                      db: Session = Depends(get_session)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    if meeting.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    if db.query(MeetingCorrection).filter(
        MeetingCorrection.meeting_id == meeting_id, MeetingCorrection.status == "PENDING"
    ).first():
        raise HTTPException(400, "A correction is already pending review for this submission")

    present_ids = {a["farmer_id"] for a in body.attendance if a.get("is_present")}
    _validate_entries_readonly(db, present_ids, body.entries)

    correction = MeetingCorrection(
        meeting_id=meeting_id, fig_id=meeting.fig_id, submitted_by_user_id=user.id,
        payload=body.model_dump(mode="json"),
    )
    db.add(correction)

    fig = db.query(Fig).filter(Fig.id == meeting.fig_id).first()
    da_ids = [u.id for u in db.query(User).filter(
        User.role == "DISTRICT_ADMIN", User.district_id == fig.district_id, User.is_active).all()] if fig else []
    if da_ids:
        create_notification(
            db, user, "Correction pending review",
            f"{fig.fig_name} submitted a correction for {meeting.meeting_month} — please review.",
            "SELECTED_DA", recipient_ids=da_ids,
        )
    db.commit()
    return {"correction_id": correction.id, "status": correction.status}


@router.get("/meetings/{meeting_id}/corrections")
def list_meeting_corrections(meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    _meeting_or_404_scoped(meeting_id, user, db)
    return db.query(MeetingCorrection).filter(MeetingCorrection.meeting_id == meeting_id) \
        .order_by(MeetingCorrection.submitted_at.desc()).all()


def _correction_or_404_scoped(correction_id: str, user: User, db: Session) -> tuple[MeetingCorrection, Meeting]:
    correction = db.query(MeetingCorrection).filter(MeetingCorrection.id == correction_id).first()
    if not correction:
        raise HTTPException(404, "Correction not found")
    meeting = _meeting_or_404_scoped(correction.meeting_id, user, db)
    return correction, meeting


@router.get("/meetings/corrections/{correction_id}/preview")
def preview_correction(correction_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    correction, meeting = _correction_or_404_scoped(correction_id, user, db)
    return _serialize_correction_preview(db, meeting, correction)


@router.post("/meetings/corrections/{correction_id}/accept")
def accept_correction(correction_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if user.role != "STATE_ADMIN":
        raise HTTPException(403, "Only State Admin can accept a correction")
    correction, meeting = _correction_or_404_scoped(correction_id, user, db)
    if correction.status != "PENDING":
        raise HTTPException(400, f"This correction is not pending review (status: {correction.status})")

    payload = correction.payload

    # Reverse the old rows' stock contribution, then delete them — safe because the correction's
    # entries are recreated via _apply_meeting_entries below, in the same transaction, committed
    # (or rolled back) atomically as one unit.
    old_yields = db.query(Yield_).filter(Yield_.meeting_id == meeting.id).all()
    old_yield_ids = [y.id for y in old_yields]
    old_byproducts = db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id.in_(old_yield_ids or [""])).all()
    old_byproduct_ids = [bp.id for bp in old_byproducts]
    for bp in old_byproducts:
        reverse_stock_for_byproduct(db, bp)
    for y in old_yields:
        reverse_stock_for_yield(db, y)
    # Stock.last_source_yield_id/last_source_byproduct_id are FKs that still point at the rows
    # we're about to delete (set by the original submission's upsert, and re-set to the same
    # value by the reversal calls above) — clear them first or the deletes below violate the FK.
    db.query(Stock).filter(Stock.last_source_yield_id.in_(old_yield_ids or [""])) \
        .update({"last_source_yield_id": None}, synchronize_session=False)
    db.query(Stock).filter(Stock.last_source_byproduct_id.in_(old_byproduct_ids or [""])) \
        .update({"last_source_byproduct_id": None}, synchronize_session=False)
    db.query(YieldInputEntry).filter(YieldInputEntry.parent_yield_id.in_(old_yield_ids or [""])).delete(synchronize_session=False)
    db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id.in_(old_yield_ids or [""])).delete(synchronize_session=False)
    db.query(Yield_).filter(Yield_.meeting_id == meeting.id).delete(synchronize_session=False)
    db.query(Attendance).filter(Attendance.meeting_id == meeting.id).delete(synchronize_session=False)

    meeting.meeting_title = payload["meeting_title"]
    meeting.meeting_date = payload["meeting_date"]
    meeting.meeting_time = payload.get("meeting_time") or ""
    meeting.meeting_venue = payload["meeting_venue"]
    meeting.meeting_details = payload.get("meeting_details")
    meeting.minutes_path = payload.get("minutes_path")
    meeting.next_meeting_date = payload.get("next_meeting_date")
    meeting.meeting_month = payload["meeting_date"][:7]
    db.add(meeting)

    _apply_meeting_entries(db, meeting, payload.get("attendance") or [], payload.get("entries") or [])
    _consume_fig_drafts(db, meeting.fig_id, meeting.meeting_month)

    correction.status = "ACCEPTED"
    correction.reviewed_by_user_id = user.id
    correction.reviewed_at = _now()
    db.add(correction)

    create_notification(
        db, user, "Correction accepted",
        f"Your correction for {meeting.meeting_month} has been accepted.",
        "SELECTED_FP", recipient_ids=[correction.submitted_by_user_id],
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Duplicate yield for same farmer/activity-product/month")
    return {"ok": True, "status": correction.status}


@router.post("/meetings/corrections/{correction_id}/reject")
def reject_correction(correction_id: str, body: MeetingCorrectionRejectIn,
                      user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if user.role != "STATE_ADMIN":
        raise HTTPException(403, "Only State Admin can reject a correction")
    correction, meeting = _correction_or_404_scoped(correction_id, user, db)
    if correction.status != "PENDING":
        raise HTTPException(400, f"This correction is not pending review (status: {correction.status})")

    correction.status = "REJECTED"
    correction.rejection_reason = body.rejection_reason
    correction.reviewed_by_user_id = user.id
    correction.reviewed_at = _now()
    db.add(correction)

    create_notification(
        db, user, "Correction rejected",
        f"Your correction for {meeting.meeting_month} was rejected: {body.rejection_reason}",
        "SELECTED_FP", recipient_ids=[correction.submitted_by_user_id],
    )
    db.commit()
    return {"ok": True, "status": correction.status}


@router.get("/yields")
def list_yields(fig_id: Optional[str] = None, month: Optional[str] = None,
                fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if month and fiscal_year:
        raise HTTPException(400, "Provide either month or fiscal_year, not both")
    q = db.query(Yield_)
    if user.role == "FARMER":
        q = q.filter(Yield_.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        q = q.filter(Yield_.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        q = q.filter(Yield_.district_id == active_district(user))
    else:
        if district_id:
            q = q.filter(Yield_.district_id == district_id)
        elif fig_id:
            q = q.filter(Yield_.fig_id == fig_id)
    if fiscal_year:
        q = q.filter(Yield_.yield_month.in_(fy_to_months(fiscal_year)))
    elif month:
        q = q.filter(Yield_.yield_month == month)
    return q.order_by(Yield_.yield_month.desc()).limit(2000).all()


def _fig_scoped_yield_query(db: Session, user: User):
    q = db.query(ByproductEntry)
    if user.role == "FARMER":
        q = q.filter(ByproductEntry.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        q = q.filter(ByproductEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        q = q.filter(ByproductEntry.district_id == active_district(user))
    return q


@router.get("/yields/{yield_id}/byproducts")
def get_yield_byproducts(yield_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    parent = db.query(Yield_).filter(Yield_.id == yield_id).first()
    if not parent:
        raise HTTPException(404, "Yield entry not found")
    if user.role == "FARMER" and parent.farmer_id != user.farmer_id:
        raise HTTPException(403, "Farmer scope mismatch")
    if user.role == "FIG_PRESIDENT" and parent.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    if user.role == "DISTRICT_ADMIN" and parent.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    return db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id == yield_id).all()


@router.get("/byproducts")
def list_byproducts(fig_id: Optional[str] = None, month: Optional[str] = None,
                    farmer_id: Optional[str] = None,
                    user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = _fig_scoped_yield_query(db, user)
    if user.role not in ("FIG_PRESIDENT", "DISTRICT_ADMIN") and fig_id:
        q = q.filter(ByproductEntry.fig_id == fig_id)
    if farmer_id:
        q = q.filter(ByproductEntry.farmer_id == farmer_id)
    if month:
        q = q.filter(ByproductEntry.yield_month == month)
    return q.order_by(ByproductEntry.yield_month.desc()).limit(2000).all()


def _with_scheme_name(db: Session, rows: list[YieldInputEntry]) -> list[dict]:
    scheme_ids = {r.scheme_id for r in rows if r.scheme_id}
    schemes = {s.id: s.scheme_name for s in db.query(Scheme).filter(Scheme.id.in_(scheme_ids or [""])).all()}
    source_type_ids = {r.source_type_id for r in rows if r.source_type_id}
    source_types = {s.id: s.source_name for s in db.query(InputSourceType).filter(InputSourceType.id.in_(source_type_ids or [""])).all()}
    out = []
    for r in rows:
        d = r.model_dump()
        d["scheme_name"] = schemes.get(r.scheme_id)
        d["source_type_name"] = source_types.get(r.source_type_id)
        out.append(d)
    return out


@router.get("/yields/{yield_id}/inputs")
def get_yield_inputs(yield_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    parent = db.query(Yield_).filter(Yield_.id == yield_id).first()
    if not parent:
        raise HTTPException(404, "Yield entry not found")
    if user.role == "FARMER" and parent.farmer_id != user.farmer_id:
        raise HTTPException(403, "Farmer scope mismatch")
    if user.role == "FIG_PRESIDENT" and parent.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    if user.role == "DISTRICT_ADMIN" and parent.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    rows = db.query(YieldInputEntry).filter(YieldInputEntry.parent_yield_id == yield_id).all()
    return _with_scheme_name(db, rows)


@router.get("/inputs")
def list_inputs(fig_id: Optional[str] = None, month: Optional[str] = None,
                farmer_id: Optional[str] = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(YieldInputEntry)
    if user.role == "FARMER":
        q = q.filter(YieldInputEntry.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        q = q.filter(YieldInputEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        q = q.filter(YieldInputEntry.district_id == active_district(user))
    elif fig_id:
        q = q.filter(YieldInputEntry.fig_id == fig_id)
    if farmer_id:
        q = q.filter(YieldInputEntry.farmer_id == farmer_id)
    if month:
        q = q.filter(YieldInputEntry.yield_month == month)
    rows = q.order_by(YieldInputEntry.yield_month.desc()).limit(2000).all()
    return _with_scheme_name(db, rows)
