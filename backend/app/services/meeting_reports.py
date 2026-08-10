"""Row-shaping helpers for the Monthly Submission Status/History pages — shared by
routers/meetings.py's list endpoints and routers/reports.py's export dispatcher, so
on-screen and exported data can never drift."""
from sqlalchemy.orm import Session
from app.models import (
    Fig, Meeting, MeetingCorrection, District, Farmer, FarmerSubmission, FarmerSubmissionCorrection,
    Yield_, ByproductEntry, YieldInputEntry, Activity, Product, LossReason, InputSourceType, Scheme,
    SilkTypeActivityProduct,
)


def submission_status_rows(db: Session, role: str, district_id: str | None, month: str) -> list[dict]:
    """One row per FIG that had already been formed by `month` (formed the same month or
    later never appears — a FIG isn't "Pending" before it exists). `district_id` scopes
    District Admin to their own district; None means unscoped (State Admin)."""
    query = db.query(Fig).filter(Fig.is_active)
    if district_id:
        query = query.filter(Fig.district_id == district_id)
    figs = query.order_by(Fig.fig_name).all()
    figs = [f for f in figs if f.formation_date.strftime("%Y-%m") < month]

    fig_ids = [f.id for f in figs]
    meetings = {
        m.fig_id: m for m in db.query(Meeting).filter(
            Meeting.fig_id.in_(fig_ids or [""]), Meeting.meeting_month == month
        ).all()
    }
    district_names = {d.id: d.district_name for d in db.query(District).all()}

    out = []
    for f in figs:
        m = meetings.get(f.id)
        out.append({
            "fig_id": f.id,
            "fig_name": f.fig_name,
            "district_name": district_names.get(f.district_id),
            "status": "Submitted" if m else "Pending",
            "submitted_on": m.submitted_at if m else None,
            "meeting_id": m.id if m else None,
        })
    return out


def fp_submission_history_rows(db: Session, fig_id: str) -> list[dict]:
    """One row per Meeting, plus one extra row per currently-outstanding correction
    (PENDING or REJECTED) for that meeting, flagged `re_submitted: "Yes"`. An ACCEPTED
    correction has already overwritten the live Meeting row in place (see
    routers/meetings.py's accept_correction), so it never needs a second row here —
    filtering to PENDING/REJECTED is all that's needed for the "collapses back to one
    row once approved" behavior."""
    meetings = db.query(Meeting).filter(Meeting.fig_id == fig_id).order_by(Meeting.meeting_month.desc()).all()
    meeting_ids = [m.id for m in meetings]
    corrections = db.query(MeetingCorrection).filter(
        MeetingCorrection.meeting_id.in_(meeting_ids or [""]),
        MeetingCorrection.status.in_(["PENDING", "REJECTED"]),
    ).order_by(MeetingCorrection.submitted_at.desc()).all()
    corrections_by_meeting: dict[str, list[MeetingCorrection]] = {}
    for c in corrections:
        corrections_by_meeting.setdefault(c.meeting_id, []).append(c)

    out = []
    for m in meetings:
        out.append({
            "meeting_id": m.id,
            "month": m.meeting_month,
            "meeting_title": m.meeting_title,
            "submitted_on": m.submitted_at,
            "venue": m.meeting_venue,
            "re_submitted": "No",
            "minutes_path": m.minutes_path,
        })
        for c in corrections_by_meeting.get(m.id, []):
            out.append({
                "meeting_id": m.id,
                "month": m.meeting_month,
                "meeting_title": m.meeting_title,
                "submitted_on": c.submitted_at,
                "venue": m.meeting_venue,
                "re_submitted": "Yes",
                "minutes_path": m.minutes_path,
            })
    out.sort(key=lambda r: r["month"], reverse=True)
    return out


def pending_corrections_rows(db: Session) -> list[dict]:
    """Every PENDING correction, joined to its FIG/District — powers State Admin's
    'Resubmission Requests' section."""
    corrections = db.query(MeetingCorrection).filter(MeetingCorrection.status == "PENDING") \
        .order_by(MeetingCorrection.submitted_at.desc()).all()
    meeting_ids = [c.meeting_id for c in corrections]
    meetings = {m.id: m for m in db.query(Meeting).filter(Meeting.id.in_(meeting_ids or [""])).all()}
    fig_ids = [m.fig_id for m in meetings.values()]
    figs = {f.id: f for f in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}
    district_names = {d.id: d.district_name for d in db.query(District).all()}

    out = []
    for c in corrections:
        m = meetings.get(c.meeting_id)
        f = figs.get(m.fig_id) if m else None
        out.append({
            "correction_id": c.id,
            "meeting_id": c.meeting_id,
            "fig_name": f.fig_name if f else None,
            "district_name": district_names.get(f.district_id) if f else None,
            "month": m.meeting_month if m else None,
            "submitted_on": c.submitted_at,
        })
    return out


def farmer_submission_rows(db: Session, role: str, district_id: str | None, month: str | None) -> list[dict]:
    """One row per FarmerSubmission — the solo-farmer analog of submission_status_rows, but
    since a solo farmer submits (or doesn't) independently, not against a fixed roster the way
    FIGs are, this only lists submissions that actually exist (no 'Pending' placeholder rows)."""
    query = db.query(FarmerSubmission)
    if month:
        query = query.filter(FarmerSubmission.submission_month == month)
    farmer_ids = None
    if district_id:
        farmer_ids = {f.id for f in db.query(Farmer.id).filter(Farmer.district_id == district_id).all()}
        query = query.filter(FarmerSubmission.farmer_id.in_(farmer_ids or [""]))
    rows = query.order_by(FarmerSubmission.submitted_at.desc()).all()

    farmers = {f.id: f for f in db.query(Farmer).filter(
        Farmer.id.in_({r.farmer_id for r in rows} or [""])).all()}
    district_names = {d.id: d.district_name for d in db.query(District).all()}

    out = []
    for r in rows:
        f = farmers.get(r.farmer_id)
        out.append({
            "submission_id": r.id,
            "submission_code": r.submission_code,
            "farmer_id": r.farmer_id,
            "farmer_name": f"{f.first_name} {f.last_name}" if f else "—",
            "farmer_code": f.farmer_code if f else None,
            "district_name": district_names.get(f.district_id) if f else None,
            "month": r.submission_month,
            "submitted_on": r.submitted_at,
        })
    return out


def pending_farmer_corrections_rows(db: Session, district_id: str) -> list[dict]:
    """Every PENDING FarmerSubmissionCorrection in `district_id` — powers District Admin's
    'Pending Farmer Resubmission Requests' section (the solo-farmer analog of
    pending_corrections_rows, deliberately District-Admin-scoped rather than State-Admin-wide,
    per this workflow's different approver)."""
    farmer_ids = {f.id for f in db.query(Farmer.id).filter(Farmer.district_id == district_id).all()}
    corrections = db.query(FarmerSubmissionCorrection).filter(
        FarmerSubmissionCorrection.status == "PENDING",
        FarmerSubmissionCorrection.farmer_id.in_(farmer_ids or [""]),
    ).order_by(FarmerSubmissionCorrection.submitted_at.desc()).all()
    submission_ids = [c.farmer_submission_id for c in corrections]
    submissions = {s.id: s for s in db.query(FarmerSubmission).filter(FarmerSubmission.id.in_(submission_ids or [""])).all()}
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    district_names = {d.id: d.district_name for d in db.query(District).all()}

    out = []
    for c in corrections:
        s = submissions.get(c.farmer_submission_id)
        f = farmers.get(c.farmer_id)
        out.append({
            "correction_id": c.id,
            "farmer_submission_id": c.farmer_submission_id,
            "farmer_name": f"{f.first_name} {f.last_name}" if f else "—",
            "farmer_code": f.farmer_code if f else None,
            "district_name": district_names.get(f.district_id) if f else None,
            "month": s.submission_month if s else None,
            "submitted_on": c.submitted_at,
        })
    return out


def _serialize_farmer_submission_detail(db: Session, submission: FarmerSubmission) -> dict:
    """The solo-farmer analog of routers/meetings.py's _serialize_meeting_detail — same
    entries[] shape (output/byproducts/inputs per activity), just no meeting/attendance
    sections since a solo submission has neither."""
    farmer = db.query(Farmer).filter(Farmer.id == submission.farmer_id).first()
    yield_rows = db.query(Yield_).filter(Yield_.farmer_submission_id == submission.id).all()
    yield_ids = [y.id for y in yield_rows]
    byproduct_rows = db.query(ByproductEntry).filter(ByproductEntry.parent_yield_id.in_(yield_ids or [""])).all()
    input_rows = db.query(YieldInputEntry).filter(YieldInputEntry.parent_yield_id.in_(yield_ids or [""])).all()

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
        "submission": {
            "id": submission.id, "submission_code": submission.submission_code,
            "submission_month": submission.submission_month, "submitted_at": submission.submitted_at,
            "farmer_id": submission.farmer_id,
            "farmer_name": f"{farmer.first_name} {farmer.last_name}" if farmer else "—",
            "farmer_code": farmer.farmer_code if farmer else None,
        },
        "entries": entries,
    }


def serialize_farmer_correction_preview(db: Session, submission: FarmerSubmission,
                                        correction: FarmerSubmissionCorrection) -> dict:
    """Normalizes a pending FarmerSubmissionCorrection's raw payload into the exact same
    response shape _serialize_farmer_submission_detail returns, mirroring routers/meetings.py's
    _serialize_correction_preview — so a District Admin reviewing a resubmission sees real
    product/activity names, not raw ids."""
    farmer = db.query(Farmer).filter(Farmer.id == submission.farmer_id).first()
    entries_raw = correction.payload.get("entries") or []

    stap_ids = {e["stap_id"] for e in entries_raw}
    staps = {s.id: s for s in db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id.in_(stap_ids or [""])).all()}
    activities = {a.id: a.activity_name for a in db.query(Activity).filter(
        Activity.id.in_({s.activity_id for s in staps.values() if s.activity_id} or [""])).all()}
    product_ids = {s.product_id for s in staps.values() if s.product_id}
    products = {p.id: p.product_name for p in db.query(Product).filter(Product.id.in_(product_ids or [""])).all()}
    loss_reason_ids = {e["loss_reason_id"] for e in entries_raw if e.get("loss_reason_id")}
    loss_reasons = {r.id: r.reason_name for r in db.query(LossReason).filter(LossReason.id.in_(loss_reason_ids or [""])).all()}

    entries = []
    for e in entries_raw:
        stap = staps.get(e["stap_id"])
        sold_qty = float(e.get("sold_qty", 0) or 0)
        sold_rate = float(e.get("sold_rate", 0) or 0)
        entries.append({
            "stap_id": e["stap_id"], "activity_name": activities.get(stap.activity_id, "—") if stap else "—",
            "is_primary_stage": bool(stap and stap.id == (farmer.primary_stap_id if farmer else None)),
            "output": {
                "product_name": products.get(stap.product_id, "—") if stap else "—",
                "planned_yield": float(e.get("planned", 0) or 0), "actual_yield": float(e.get("actual", 0) or 0),
                "next_month_plan": float(e.get("next_plan", 0) or 0), "stock_balance": float(e.get("stock", 0) or 0),
                "sold_quantity": sold_qty, "sold_rate": sold_rate, "earning": sold_qty * sold_rate,
                "loss_reason_id": e.get("loss_reason_id"), "loss_reason_name": loss_reasons.get(e.get("loss_reason_id")),
            },
            "byproducts": [], "inputs": [],
        })

    return {
        "submission": {
            "id": submission.id, "submission_code": submission.submission_code,
            "submission_month": submission.submission_month, "submitted_at": correction.submitted_at,
            "farmer_id": submission.farmer_id,
            "farmer_name": f"{farmer.first_name} {farmer.last_name}" if farmer else "—",
            "farmer_code": farmer.farmer_code if farmer else None,
        },
        "entries": entries,
    }
