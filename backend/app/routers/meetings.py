"""Meetings + Yields."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.services.fiscal import fy_to_months
from app.services.stock import upsert_stock_for_yield, upsert_stock_for_byproduct
from app.models import (
    Meeting, Attendance, Yield_, Fig, Farmer, User,
    SilkTypeActivityProduct, Product, ByproductEntry, YieldInputEntry, Scheme,
    InputSourceType, StapSourceType,
)
from app.schemas import MeetingIn

router = APIRouter(tags=["meetings_yields"])


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
            product_id=product.id, yield_month=parent.yield_month, unit_of_measure=product.unit_of_measure,
            quantity=qty, source_type_id=source_type.id, scheme_id=scheme_id, remarks=e.get("remarks", "") or "",
        )
        db.add(row)
        created.append(row)
    return created


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
    present_ids: set[str] = set()
    for a in body.attendance:
        db.add(Attendance(meeting_id=meeting.id, fig_id=body.fig_id,
                          farmer_id=a["farmer_id"], is_present=bool(a.get("is_present", False))))
        if a.get("is_present"):
            present_ids.add(a["farmer_id"])

    entries = [e for e in body.entries if e["farmer_id"] in present_ids]
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
            fig_id=body.fig_id, farmer_id=farmer.id, stap_id=stap.id,
            activity_id=stap.activity_id, product_id=stap.product_id,
            meeting_id=meeting.id, yield_month=m_month,
            is_primary_stage=(stap.id == farmer.primary_stap_id),
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
        fig_ids = [f.id for f in db.query(Fig).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(Meeting.fig_id.in_(fig_ids or [""]))
        if fig_id:
            q = q.filter(Meeting.fig_id == fig_id)
    elif fig_id:
        q = q.filter(Meeting.fig_id == fig_id)
    if month:
        q = q.filter(Meeting.meeting_month == month)
    return q.order_by(Meeting.meeting_date.desc()).all()


@router.get("/yields")
def list_yields(fig_id: Optional[str] = None, month: Optional[str] = None,
                fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if month and fiscal_year:
        raise HTTPException(400, "Provide either month or fiscal_year, not both")
    q = db.query(Yield_)
    if user.role == "FIG_PRESIDENT":
        q = q.filter(Yield_.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(Yield_.fig_id.in_(fig_ids or [""]))
    else:
        if district_id:
            fig_ids = [f.id for f in db.query(Fig).filter(Fig.district_id == district_id).all()]
            q = q.filter(Yield_.fig_id.in_(fig_ids or [""]))
        elif fig_id:
            q = q.filter(Yield_.fig_id == fig_id)
    if fiscal_year:
        q = q.filter(Yield_.yield_month.in_(fy_to_months(fiscal_year)))
    elif month:
        q = q.filter(Yield_.yield_month == month)
    return q.order_by(Yield_.yield_month.desc()).limit(2000).all()


def _fig_scoped_yield_query(db: Session, user: User):
    q = db.query(ByproductEntry)
    if user.role == "FIG_PRESIDENT":
        q = q.filter(ByproductEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(ByproductEntry.fig_id.in_(fig_ids or [""]))
    return q


@router.get("/yields/{yield_id}/byproducts")
def get_yield_byproducts(yield_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    parent = db.query(Yield_).filter(Yield_.id == yield_id).first()
    if not parent:
        raise HTTPException(404, "Yield entry not found")
    if user.role == "FIG_PRESIDENT" and parent.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    if user.role == "DISTRICT_ADMIN":
        fig = db.query(Fig).filter(Fig.id == parent.fig_id).first()
        if not fig or fig.district_id != user.district_id:
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
    if user.role == "FIG_PRESIDENT" and parent.fig_id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    if user.role == "DISTRICT_ADMIN":
        fig = db.query(Fig).filter(Fig.id == parent.fig_id).first()
        if not fig or fig.district_id != user.district_id:
            raise HTTPException(403, "District scope mismatch")
    rows = db.query(YieldInputEntry).filter(YieldInputEntry.parent_yield_id == yield_id).all()
    return _with_scheme_name(db, rows)


@router.get("/inputs")
def list_inputs(fig_id: Optional[str] = None, month: Optional[str] = None,
                farmer_id: Optional[str] = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(YieldInputEntry)
    if user.role == "FIG_PRESIDENT":
        q = q.filter(YieldInputEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
    elif fig_id:
        q = q.filter(YieldInputEntry.fig_id == fig_id)
    if farmer_id:
        q = q.filter(YieldInputEntry.farmer_id == farmer_id)
    if month:
        q = q.filter(YieldInputEntry.yield_month == month)
    rows = q.order_by(YieldInputEntry.yield_month.desc()).limit(2000).all()
    return _with_scheme_name(db, rows)
