"""Reports & dashboards (PostgreSQL aggregations)."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.services.fiscal import period_months, fy_to_months
from app.services.export import rows_to_xlsx, rows_to_pdf
from app.services.analytics import dfl_efficiency_rows, byproduct_ratio_by_district, scope_district, inputs_by_district, activity_efficiency_rows
from app.services.farmer_reports import apply_farmer_filters, farmer_report_rows
from app.services.fig_reports import apply_fig_filters, fig_report_rows
from app.models import (
    Farmer, Fig, District, Land, Training, FigMember, Meeting, Yield_,
    User, Scheme, Allocation, Product, ByproductEntry, Stock, YieldInputEntry,
    SilkType, Activity, SilkTypeActivityProduct,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _submission_stats(db: Session, months: list[str]) -> dict:
    """Per-district FIG submission completeness over the given months."""
    figs = db.query(Fig.district_id, func.count(Fig.id).label("total")).filter(Fig.is_active).group_by(Fig.district_id).all()
    submitted = db.query(Fig.district_id, func.count(Meeting.id).label("done")).join(
        Meeting, Meeting.fig_id == Fig.id).filter(Meeting.meeting_month.in_(months), Fig.is_active).group_by(Fig.district_id).all()
    sub_map = {r.district_id: int(r.done) for r in submitted}
    out = {}
    for r in figs:
        total_figs = int(r.total or 0)
        expected = total_figs * len(months)
        done = sub_map.get(r.district_id, 0)
        pct = round((done / expected) * 100, 1) if expected else 0
        out[r.district_id] = {"total_figs": total_figs, "submitted": done, "pct": pct}
    return out


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if user.role == "STATE_ADMIN":
        cur_month = datetime.now(timezone.utc).strftime("%Y-%m")
        return {
            "farmers": db.query(func.count(Farmer.id)).filter(Farmer.is_active).scalar() or 0,
            "figs": db.query(func.count(Fig.id)).filter(Fig.is_active).scalar() or 0,
            "districts": db.query(func.count(District.id)).filter(District.is_active).scalar() or 0,
            "activities": db.query(func.count(Activity.id)).filter(Activity.is_active).scalar() or 0,
            "lands_pending": db.query(func.count(Land.id)).filter(Land.gps_verified == "Pending").scalar() or 0,
            "pending_trainings": db.query(func.count(Training.id)).filter(Training.status == "Pending").scalar() or 0,
            "current_month": cur_month,
            "monthly_submitted_count": db.query(func.count(Meeting.id)).filter(Meeting.meeting_month == cur_month).scalar() or 0,
        }
    if user.role == "DISTRICT_ADMIN":
        farmer_ids = [f.id for f in db.query(Farmer.id).filter(Farmer.district_id == user.district_id).all()]
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id, Fig.is_active).all()]
        cur_month = datetime.now(timezone.utc).strftime("%Y-%m")
        return {
            "farmers": db.query(func.count(Farmer.id)).filter(
                Farmer.district_id == user.district_id, Farmer.is_active).scalar() or 0,
            "figs": db.query(func.count(Fig.id)).filter(
                Fig.district_id == user.district_id, Fig.is_active).scalar() or 0,
            "activities": db.query(func.count(func.distinct(SilkTypeActivityProduct.activity_id))).join(
                Fig, Fig.stap_id == SilkTypeActivityProduct.id).filter(
                Fig.district_id == user.district_id, Fig.is_active).scalar() or 0,
            "total_members": db.query(func.count(FigMember.id)).filter(
                FigMember.fig_id.in_(fig_ids or [""]), FigMember.is_active).scalar() or 0,
            "lands_pending": db.query(func.count(Land.id)).filter(
                Land.farmer_id.in_(farmer_ids or [""]),
                Land.gps_verified == "Pending").scalar() or 0,
            "pending_trainings": db.query(func.count(Training.id)).filter(
                Training.district_id == user.district_id, Training.status == "Pending").scalar() or 0,
            "current_month": cur_month,
            "monthly_submitted_count": db.query(func.count(Meeting.id)).filter(
                Meeting.fig_id.in_(fig_ids or [""]), Meeting.meeting_month == cur_month).scalar() or 0,
        }
    if user.role == "FIG_PRESIDENT":
        fig = db.query(Fig).filter(Fig.id == user.fig_id).first()
        district = db.query(District).filter(District.id == user.district_id).first()
        members = db.query(func.count(FigMember.id)).filter(
            FigMember.fig_id == user.fig_id, FigMember.is_active).scalar() or 0
        meetings = db.query(func.count(Meeting.id)).filter(Meeting.fig_id == user.fig_id).scalar() or 0
        cur_month = datetime.now(timezone.utc).strftime("%Y-%m")
        submitted = db.query(Meeting).filter(Meeting.fig_id == user.fig_id,
                                              Meeting.meeting_month == cur_month).first() is not None
        return {"members": members, "meetings": meetings,
                "submitted_this_month": submitted, "current_month": cur_month,
                "fig_name": fig.fig_name if fig else None, "fig_code": fig.fig_code if fig else None,
                "district_name": district.district_name if district else None}
    return {}


@router.get("/silk-type-distribution")
def silk_type_distribution(user: User = Depends(require_roles("STATE_ADMIN")), db: Session = Depends(get_session)):
    rows = db.query(
        SilkTypeActivityProduct.silk_type_id, SilkType.silk_type_name,
        func.count(Fig.id).label("figs"),
    ).join(Fig, Fig.stap_id == SilkTypeActivityProduct.id).join(
        SilkType, SilkType.id == SilkTypeActivityProduct.silk_type_id
    ).filter(Fig.is_active).group_by(SilkTypeActivityProduct.silk_type_id, SilkType.silk_type_name).all()
    return [{"silk_type_id": r.silk_type_id, "silk_type_name": r.silk_type_name, "figs": int(r.figs)} for r in rows]


@router.get("/district-heatmap")
def district_heatmap(user: User = Depends(require_roles("STATE_ADMIN")),
                     month: Optional[str] = None, db: Session = Depends(get_session)):
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    stats = _submission_stats(db, [month])
    districts = {d.id: d.district_name for d in db.query(District).all()}
    out = [{
        "district_id": district_id,
        "district_name": districts.get(district_id, "?"),
        "total": s["total_figs"], "submitted": s["submitted"], "pct": s["pct"],
    } for district_id, s in stats.items()]
    out.sort(key=lambda x: -x["pct"])
    return out


def _scheme_utilization_rows(user: User, db: Session) -> list[dict]:
    schemes = db.query(Scheme).filter(Scheme.is_active).all()
    scheme_ids = [s.id for s in schemes]

    alloc_q = db.query(Allocation).filter(Allocation.scheme_id.in_(scheme_ids or [""]))
    totals_q = db.query(
        Allocation.scheme_id,
        func.sum(Allocation.allocated_amount_rs).label("allocated"),
        func.sum(Allocation.utilised).label("utilised"),
        func.sum(Allocation.remaining).label("remaining"),
    ).filter(Allocation.scheme_id.in_(scheme_ids or [""]))
    if user.role == "DISTRICT_ADMIN":
        alloc_q = alloc_q.filter(Allocation.district_id == user.district_id)
        totals_q = totals_q.filter(Allocation.district_id == user.district_id)
    by_scheme: dict[str, list] = {}
    for a in alloc_q.all():
        by_scheme.setdefault(a.scheme_id, []).append(a)
    totals = {r.scheme_id: r for r in totals_q.group_by(Allocation.scheme_id).all()}

    districts = {d.id: d.district_name for d in db.query(District).all()}
    out = []
    for s in schemes:
        allocs = by_scheme.get(s.id, [])
        if user.role == "DISTRICT_ADMIN" and not allocs:
            continue
        t = totals.get(s.id)
        out.append({
            "scheme_id": s.id, "scheme_name": s.scheme_name, "total_budget_rs": s.total_budget_rs,
            "allocated_rs": float(t.allocated or 0) if t else 0,
            "utilised_rs": float(t.utilised or 0) if t else 0,
            "remaining_rs": float(t.remaining or 0) if t else 0,
            "districts": [{
                "district_id": a.district_id, "district_name": districts.get(a.district_id, "?"),
                "allocated_rs": a.allocated_amount_rs, "utilised_rs": a.utilised or 0, "remaining_rs": a.remaining or 0,
            } for a in allocs],
        })
    return out


@router.get("/scheme-utilization")
def scheme_utilization(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _scheme_utilization_rows(user, db)


def _district_comparison_rows(month: Optional[str], fiscal_year: Optional[str], user: User, db: Session) -> dict:
    """Per-district rollup. Submission rate and yield achievement are scoped to the given
    period; GPS-verified % and scheme-utilization % are all-time snapshots (the underlying
    Land/Allocation records carry no month dimension)."""
    months = period_months(month, fiscal_year) or [datetime.now(timezone.utc).strftime("%Y-%m")]
    sub_stats = _submission_stats(db, months)
    districts = {d.id: d.district_name for d in db.query(District).all()}

    yield_by_district = {
        r.district_id: {"planned": float(r.planned or 0), "actual": float(r.actual or 0)}
        for r in db.query(
            Farmer.district_id,
            func.sum(Yield_.planned_yield).label("planned"),
            func.sum(Yield_.actual_yield).label("actual"),
        ).join(Farmer, Farmer.id == Yield_.farmer_id)
         .filter(Yield_.yield_month.in_(months))
         .group_by(Farmer.district_id).all()
    }

    gps_by_district = {
        r.district_id: {"total": int(r.total or 0), "verified": int(r.verified or 0)}
        for r in db.query(
            Farmer.district_id,
            func.count(Land.id).label("total"),
            func.sum(case((Land.gps_verified == "Verified", 1), else_=0)).label("verified"),
        ).join(Farmer, Farmer.id == Land.farmer_id)
         .group_by(Farmer.district_id).all()
    }

    alloc_by_district = {
        r.district_id: {"allocated": float(r.allocated or 0), "utilised": float(r.utilised or 0)}
        for r in db.query(
            Allocation.district_id,
            func.sum(Allocation.allocated_amount_rs).label("allocated"),
            func.sum(Allocation.utilised).label("utilised"),
        ).group_by(Allocation.district_id).all()
    }

    out = []
    for district_id, name in districts.items():
        sub = sub_stats.get(district_id, {"total_figs": 0, "submitted": 0, "pct": 0})
        yd = yield_by_district.get(district_id, {"planned": 0.0, "actual": 0.0})
        gd = gps_by_district.get(district_id, {"total": 0, "verified": 0})
        ad = alloc_by_district.get(district_id, {"allocated": 0.0, "utilised": 0.0})
        out.append({
            "district_id": district_id, "district_name": name,
            "total_figs": sub["total_figs"], "submission_pct": sub["pct"],
            "yield_achievement_pct": round((yd["actual"] / yd["planned"]) * 100, 1) if yd["planned"] else 0,
            "gps_verified_pct": round((gd["verified"] / gd["total"]) * 100, 1) if gd["total"] else 0,
            "scheme_utilization_pct": round((ad["utilised"] / ad["allocated"]) * 100, 1) if ad["allocated"] else 0,
        })
    out.sort(key=lambda x: -x["submission_pct"])
    return {"months": months, "districts": out}


@router.get("/district-comparison")
def district_comparison(month: Optional[str] = None, fiscal_year: Optional[str] = None,
                        user: User = Depends(require_roles("STATE_ADMIN")), db: Session = Depends(get_session)):
    return _district_comparison_rows(month, fiscal_year, user, db)


def _scope_yield_query(q, user: User, district_id: Optional[str], db: Session):
    """Shared FIG-scoping ladder used by every Yield_-based report endpoint."""
    if user.role == "FIG_PRESIDENT":
        return q.filter(Yield_.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
        return q.filter(Yield_.fig_id.in_(fig_ids or [""]))
    elif district_id:
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
        return q.filter(Yield_.fig_id.in_(fig_ids or [""]))
    return q


def _yield_summary_rows(month: Optional[str], fiscal_year: Optional[str], district_id: Optional[str],
                        user: User, db: Session) -> list[dict]:
    """Pure production rollup — planned/actual/earning only. Stock is a point-in-time
    balance, never summed across months, and is reported separately via
    GET /reports/analytics/stock (which has no period concept at all)."""
    months = period_months(month, fiscal_year)
    q = db.query(
        Yield_.product_id, Product.product_name,
        func.sum(Yield_.planned_yield).label("planned"),
        func.sum(Yield_.actual_yield).label("actual"),
        func.sum(Yield_.earning).label("earning"),
        func.count(Yield_.id).label("count"),
    ).join(Product, Product.id == Yield_.product_id)
    if months:
        q = q.filter(Yield_.yield_month.in_(months))
    q = _scope_yield_query(q, user, district_id, db)
    rows = q.group_by(Yield_.product_id, Product.product_name).all()
    return [{
        "product_id": r.product_id, "product": {"product_name": r.product_name},
        "planned": float(r.planned or 0), "actual": float(r.actual or 0),
        "earning": float(r.earning or 0), "count": r.count,
    } for r in rows]


@router.get("/yield-summary")
def yield_summary(month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _yield_summary_rows(month, fiscal_year, district_id, user, db)


def _product_summary_rows(month: Optional[str], fiscal_year: Optional[str], district_id: Optional[str],
                          user: User, db: Session) -> list[dict]:
    """Product-wise production totals for dashboard tiles. Production (Yield_) and byproduct
    (ByproductEntry) quantities are two DIFFERENT measurements and are never summed together —
    only merged side-by-side per product."""
    months = period_months(month, fiscal_year)

    y_q = db.query(
        Yield_.product_id,
        func.sum(Yield_.planned_yield).label("planned"),
        func.sum(Yield_.actual_yield).label("actual"),
        func.count(Yield_.id).label("count"),
    ).filter(Yield_.product_id.isnot(None))
    if months:
        y_q = y_q.filter(Yield_.yield_month.in_(months))
    y_q = _scope_yield_query(y_q, user, district_id, db)
    y_rows = {r.product_id: r for r in y_q.group_by(Yield_.product_id).all()}

    bp_q = db.query(
        ByproductEntry.product_id,
        func.sum(ByproductEntry.quantity).label("qty"),
        func.count(ByproductEntry.id).label("count"),
    )
    if months:
        bp_q = bp_q.filter(ByproductEntry.yield_month.in_(months))
    if user.role == "FIG_PRESIDENT":
        bp_q = bp_q.filter(ByproductEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
        bp_q = bp_q.filter(ByproductEntry.fig_id.in_(fig_ids or [""]))
    elif district_id:
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
        bp_q = bp_q.filter(ByproductEntry.fig_id.in_(fig_ids or [""]))
    bp_rows = {r.product_id: r for r in bp_q.group_by(ByproductEntry.product_id).all()}

    product_ids = set(y_rows) | set(bp_rows)
    products = {p.id: p for p in db.query(Product).filter(
        Product.id.in_(product_ids or [""]), Product.show_in_dashboard.is_(True)).all()}
    stap_rows = db.query(SilkTypeActivityProduct.product_id, SilkType.id, SilkType.silk_type_name) \
        .join(SilkType, SilkType.id == SilkTypeActivityProduct.silk_type_id) \
        .filter(SilkTypeActivityProduct.product_id.in_(product_ids or [""]), SilkTypeActivityProduct.is_active).distinct().all()
    silk_types_by_product: dict[str, list[dict]] = {}
    for pid, stid, stname in stap_rows:
        silk_types_by_product.setdefault(pid, []).append({"id": stid, "name": stname})

    out = []
    for pid in product_ids:
        if pid not in products:
            continue  # hidden via Product.show_in_dashboard
        p = products.get(pid)
        yr, br = y_rows.get(pid), bp_rows.get(pid)
        out.append({
            "product_id": pid, "product_name": p.product_name if p else None,
            "unit_of_measure": p.unit_of_measure if p else None, "is_byproduct": p.is_byproduct if p else None,
            "silk_types": silk_types_by_product.get(pid, []),
            "planned": float(yr.planned or 0) if yr else 0.0, "actual": float(yr.actual or 0) if yr else 0.0,
            "yield_count": int(yr.count) if yr else 0,
            "byproduct_qty": float(br.qty or 0) if br else 0.0, "byproduct_count": int(br.count) if br else 0,
        })
    out.sort(key=lambda r: (r["product_name"] or ""))
    return out


@router.get("/product-summary")
def product_summary(month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                    user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    months = period_months(month, fiscal_year)
    return {"months": months, "rows": _product_summary_rows(month, fiscal_year, district_id, user, db)}


def _stock_summary_rows(district_id: Optional[str], user: User, db: Session) -> list[dict]:
    """Current stock totals per product — point-in-time, no month/fiscal_year param exists here."""
    q = db.query(Stock.product_id, func.sum(Stock.closing_balance).label("stock"),
                 func.bool_or(Stock.is_perishable).label("is_perishable"))
    if user.role == "FIG_PRESIDENT":
        q = q.filter(Stock.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(Stock.fig_id.in_(fig_ids or [""]))
    elif district_id:
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
        q = q.filter(Stock.fig_id.in_(fig_ids or [""]))
    rows = q.group_by(Stock.product_id).all()
    product_ids = [r.product_id for r in rows]
    products = {p.id: p for p in db.query(Product).filter(
        Product.id.in_(product_ids or [""]), Product.show_in_dashboard.is_(True)).all()}
    rows = [r for r in rows if r.product_id in products]  # hidden via Product.show_in_dashboard
    out = [{
        "product_id": r.product_id, "product_name": products[r.product_id].product_name if r.product_id in products else None,
        "unit_of_measure": products[r.product_id].unit_of_measure if r.product_id in products else None,
        "stock": float(r.stock or 0), "is_perishable": bool(r.is_perishable),
    } for r in rows]
    out.sort(key=lambda r: (r["product_name"] or ""))
    return out


@router.get("/stock-summary")
def stock_summary(district_id: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return {"rows": _stock_summary_rows(district_id, user, db)}


def _input_summary_rows(month: Optional[str], fiscal_year: Optional[str], district_id: Optional[str],
                        user: User, db: Session) -> list[dict]:
    """Input-wise consumption totals for dashboard tiles — additive/time-bound like production."""
    months = period_months(month, fiscal_year)
    q = db.query(YieldInputEntry.product_id, func.sum(YieldInputEntry.quantity).label("qty"))
    if months:
        q = q.filter(YieldInputEntry.yield_month.in_(months))
    if user.role == "FIG_PRESIDENT":
        q = q.filter(YieldInputEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
    elif district_id:
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
        q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
    rows = q.group_by(YieldInputEntry.product_id).all()
    product_ids = [r.product_id for r in rows]
    products = {p.id: p for p in db.query(Product).filter(
        Product.id.in_(product_ids or [""]), Product.show_in_dashboard.is_(True)).all()}
    rows = [r for r in rows if r.product_id in products]  # hidden via Product.show_in_dashboard
    out = [{
        "product_id": r.product_id, "product_name": products[r.product_id].product_name if r.product_id in products else None,
        "unit_of_measure": products[r.product_id].unit_of_measure if r.product_id in products else None,
        "total_qty": float(r.qty or 0),
    } for r in rows]
    out.sort(key=lambda r: (r["product_name"] or ""))
    return out


@router.get("/input-summary")
def input_summary(month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    months = period_months(month, fiscal_year)
    return {"months": months, "rows": _input_summary_rows(month, fiscal_year, district_id, user, db)}


@router.get("/monthly-trend")
def monthly_trend(month: Optional[str] = None, fiscal_year: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    months = period_months(month, fiscal_year)
    q = db.query(
        Yield_.yield_month,
        func.sum(Yield_.planned_yield).label("planned"),
        func.sum(Yield_.actual_yield).label("actual"),
    )
    if months:
        q = q.filter(Yield_.yield_month.in_(months))
    if user.role == "FIG_PRESIDENT":
        q = q.filter(Yield_.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
        q = q.filter(Yield_.fig_id.in_(fig_ids or [""]))
    rows = q.group_by(Yield_.yield_month).order_by(Yield_.yield_month).all()
    return [{"month": r.yield_month, "planned": float(r.planned or 0), "actual": float(r.actual or 0)} for r in rows]


def _trailing_12_months() -> list[str]:
    now = datetime.now(timezone.utc)
    months = []
    y, m = now.year, now.month
    for _ in range(12):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def _product_monthly_trend_rows(metric: str, product_id: Optional[str], district_id: Optional[str],
                                user: User, db: Session) -> dict:
    """Last 12 calendar months (NOT fiscal-year-aligned — unlike yoy-trend) for one metric,
    optionally scoped to one product. Backs the Input & Output Overview page's
    Month-on-Month view."""
    if metric not in ("output", "input"):
        raise HTTPException(400, "metric must be 'output' or 'input'")
    months = _trailing_12_months()
    if metric == "output":
        q = db.query(Yield_.yield_month, func.sum(Yield_.actual_yield).label("value")).filter(
            Yield_.yield_month.in_(months))
        if product_id:
            q = q.filter(Yield_.product_id == product_id)
        q = _scope_yield_query(q, user, district_id, db)
        by_month = {r.yield_month: float(r.value or 0) for r in q.group_by(Yield_.yield_month).all()}
    else:  # input
        q = db.query(YieldInputEntry.yield_month, func.sum(YieldInputEntry.quantity).label("value")).filter(
            YieldInputEntry.yield_month.in_(months))
        if product_id:
            q = q.filter(YieldInputEntry.product_id == product_id)
        if user.role == "FIG_PRESIDENT":
            q = q.filter(YieldInputEntry.fig_id == user.fig_id)
        elif user.role == "DISTRICT_ADMIN":
            fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
            q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
        elif district_id:
            fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
            q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
        by_month = {r.yield_month: float(r.value or 0) for r in q.group_by(YieldInputEntry.yield_month).all()}
    return {"months": months, "metric": metric, "data": [{"month": m, "value": by_month.get(m, 0.0)} for m in months]}


@router.get("/product-monthly-trend")
def product_monthly_trend(metric: str = "output", product_id: Optional[str] = None, district_id: Optional[str] = None,
                          user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _product_monthly_trend_rows(metric, product_id, district_id, user, db)


def _onboarding_trend_rows(fiscal_year: Optional[str], district_id: Optional[str], user: User, db: Session) -> dict:
    """Farmer uses created_at (only date field available); FIG uses formation_date (the
    real-world onboarding date an admin sets, more meaningful than the system created_at)."""
    if fiscal_year:
        try:
            months = fy_to_months(fiscal_year)
        except ValueError as e:
            raise HTTPException(400, str(e))
    else:
        months = _trailing_12_months()

    farmer_q = db.query(Farmer)
    fig_q = db.query(Fig)
    if user.role == "DISTRICT_ADMIN":
        farmer_q = farmer_q.filter(Farmer.district_id == user.district_id)
        fig_q = fig_q.filter(Fig.district_id == user.district_id)
    elif user.role == "FIG_PRESIDENT":
        member_ids = [m.farmer_id for m in db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
        farmer_q = farmer_q.filter(Farmer.id.in_(member_ids or [""]))
        fig_q = fig_q.filter(Fig.id == user.fig_id)
    elif district_id:
        farmer_q = farmer_q.filter(Farmer.district_id == district_id)
        fig_q = fig_q.filter(Fig.district_id == district_id)

    farmer_rows = farmer_q.with_entities(
        func.to_char(Farmer.created_at, 'YYYY-MM').label("m"), func.count(Farmer.id).label("count")
    ).group_by("m").all()
    farmer_by_month = {r.m: int(r.count) for r in farmer_rows}

    fig_rows = fig_q.with_entities(
        func.to_char(Fig.formation_date, 'YYYY-MM').label("m"), func.count(Fig.id).label("count")
    ).group_by("m").all()
    fig_by_month = {r.m: int(r.count) for r in fig_rows}

    return {
        "months": months,
        "farmers_monthly": [farmer_by_month.get(m, 0) for m in months],
        "farmers_total_to_date": farmer_q.count(),
        "figs_monthly": [fig_by_month.get(m, 0) for m in months],
        "figs_total_to_date": fig_q.count(),
    }


@router.get("/onboarding-trend")
def onboarding_trend(fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                     user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT")),
                     db: Session = Depends(get_session)):
    return _onboarding_trend_rows(fiscal_year, district_id, user, db)


def _yoy_trend_rows(fiscal_years: list[str], product_id: Optional[str], metric: str,
                    district_id: Optional[str], user: User, db: Session) -> dict:
    if metric not in ("output", "input"):
        raise HTTPException(400, "metric must be 'output' or 'input'")
    if not fiscal_years or len(fiscal_years) > 6:
        raise HTTPException(400, "Provide 1-6 fiscal_years")
    try:
        fy_month_lists = {fy: fy_to_months(fy) for fy in fiscal_years}
    except ValueError as e:
        raise HTTPException(400, str(e))
    all_months = [m for months in fy_month_lists.values() for m in months]

    if metric == "output":
        q = db.query(Yield_.yield_month, func.sum(Yield_.planned_yield).label("planned"),
                     func.sum(Yield_.actual_yield).label("actual")).filter(Yield_.yield_month.in_(all_months))
        if product_id:
            q = q.filter(Yield_.product_id == product_id)
        q = _scope_yield_query(q, user, district_id, db)
        by_month = {r.yield_month: r for r in q.group_by(Yield_.yield_month).all()}
    else:  # input — same shape query against consumption, no "planned" concept
        q = db.query(YieldInputEntry.yield_month, func.sum(YieldInputEntry.quantity).label("actual")).filter(
            YieldInputEntry.yield_month.in_(all_months))
        if product_id:
            q = q.filter(YieldInputEntry.product_id == product_id)
        if user.role == "FIG_PRESIDENT":
            q = q.filter(YieldInputEntry.fig_id == user.fig_id)
        elif user.role == "DISTRICT_ADMIN":
            fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == user.district_id).all()]
            q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
        elif district_id:
            fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
            q = q.filter(YieldInputEntry.fig_id.in_(fig_ids or [""]))
        by_month = {r.yield_month: r for r in q.group_by(YieldInputEntry.yield_month).all()}

    labels = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
    series = []
    for fy, months in fy_month_lists.items():
        data = []
        for label, m in zip(labels, months):
            r = by_month.get(m)
            data.append({"label": label, "planned": float(getattr(r, "planned", 0) or 0) if r else 0.0,
                        "actual": float(r.actual or 0) if r else 0.0})
        series.append({"fiscal_year": fy, "data": data})
    return {"fiscal_years": fiscal_years, "metric": metric, "labels": labels, "series": series}


@router.get("/yoy-trend")
def yoy_trend(fiscal_years: list[str] = Query(...), product_id: Optional[str] = None, metric: str = "output",
             district_id: Optional[str] = None,
             user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return _yoy_trend_rows(fiscal_years, product_id, metric, district_id, user, db)


_EXPORT_MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


@router.get("/export")
def export_report(report: str, format: str,
                  month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                  seri_circle_id: Optional[str] = None, q: Optional[str] = None,
                  gender: Optional[str] = None, education_level_id: Optional[str] = None,
                  caste_id: Optional[str] = None, religion_id: Optional[str] = None,
                  experience_min: Optional[int] = None, experience_max: Optional[int] = None,
                  has_bank_details: Optional[bool] = None, is_active: Optional[bool] = None,
                  stap_id: Optional[str] = None, formation_date_from: Optional[str] = None,
                  formation_date_to: Optional[str] = None,
                  product_id: Optional[str] = None, activity_id: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """Shared Excel/PDF export dispatcher — every exportable report's row-fetching logic
    lives in a plain `_xxx_rows` function reused by both its JSON endpoint and this
    dispatcher, so the export always matches exactly what's on screen."""
    if format not in _EXPORT_MEDIA_TYPES:
        raise HTTPException(400, "format must be 'xlsx' or 'pdf'")

    if report == "yield-summary":
        rows = _yield_summary_rows(month, fiscal_year, district_id, user, db)
        headers = ["Product", "Planned", "Actual", "Earning", "Records"]
        data = [[r["product"]["product_name"], r["planned"], r["actual"], r["earning"], r["count"]] for r in rows]
    elif report == "product-summary":
        rows = _product_summary_rows(month, fiscal_year, district_id, user, db)
        headers = ["Product", "Unit", "Silk Types", "Planned", "Actual", "Byproduct Qty"]
        data = [[r["product_name"], r["unit_of_measure"], ", ".join(s["name"] for s in r["silk_types"]),
                r["planned"], r["actual"], r["byproduct_qty"]] for r in rows]
    elif report == "stock-summary":
        rows = _stock_summary_rows(district_id, user, db)
        headers = ["Product", "Unit", "Current Stock", "Perishable"]
        data = [[r["product_name"], r["unit_of_measure"], r["stock"], "Yes" if r["is_perishable"] else "No"] for r in rows]
    elif report == "input-summary":
        rows = _input_summary_rows(month, fiscal_year, district_id, user, db)
        headers = ["Product", "Unit", "Total Qty"]
        data = [[r["product_name"], r["unit_of_measure"], r["total_qty"]] for r in rows]
    elif report == "district-comparison":
        if user.role != "STATE_ADMIN":
            raise HTTPException(403, "State Admin only")
        result = _district_comparison_rows(month, fiscal_year, user, db)
        headers = ["District", "Total FIGs", "Submission %", "Yield Achievement %", "GPS Verified %", "Scheme Utilization %"]
        data = [[r["district_name"], r["total_figs"], r["submission_pct"], r["yield_achievement_pct"],
                r["gps_verified_pct"], r["scheme_utilization_pct"]] for r in result["districts"]]
    elif report == "scheme-utilization":
        rows = _scheme_utilization_rows(user, db)
        headers = ["Scheme", "Total Budget (Rs)", "Allocated (Rs)", "Utilised (Rs)", "Remaining (Rs)"]
        data = [[r["scheme_name"], r["total_budget_rs"], r["allocated_rs"], r["utilised_rs"], r["remaining_rs"]] for r in rows]
    elif report == "dfl-efficiency":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        months = period_months(month, fiscal_year)
        resolved_district = scope_district(user, district_id)
        rows = dfl_efficiency_rows(db, months, resolved_district)
        headers = ["Silk Type", "Cocoon Actual", "DFL Actual", "kg per DFL"]
        data = [[r["silk_type_name"], r["cocoon_actual"], r["dfl_actual"], r["kg_per_dfl"]] for r in rows]
    elif report == "byproduct-ratio":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        months = period_months(month, fiscal_year)
        resolved_district = scope_district(user, district_id)
        rows = byproduct_ratio_by_district(db, months, resolved_district)
        headers = ["District", "Byproduct", "Unit", "Byproduct Qty", "Parent Actual Yield", "Ratio %"]
        data = [[r["district_name"], r["product_name"], r["unit_of_measure"], r["byproduct_qty"],
                r["parent_actual_yield"], r["ratio_pct"]] for r in rows]
    elif report == "inputs":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        if not product_id:
            raise HTTPException(400, "product_id is required")
        if not db.query(Product).filter(Product.id == product_id).first():
            raise HTTPException(404, "Product not found")
        months = period_months(month, fiscal_year) or [datetime.now(timezone.utc).strftime("%Y-%m")]
        rows = inputs_by_district(db, product_id, months)
        if user.role == "DISTRICT_ADMIN":
            rows = [r for r in rows if r["id"] == user.district_id]
        headers = ["District", "Total Qty", "Purchased", "Government Scheme", "Own Source", "Government Land/Forest"]
        data = [[r["name"], r["total_qty"], r["by_source"]["Purchased"], r["by_source"]["Government Scheme"],
                r["by_source"]["Own Source"], r["by_source"]["Government Land/Forest"]] for r in rows]
    elif report == "activity-efficiency":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        if not activity_id:
            raise HTTPException(400, "activity_id is required")
        if not db.query(Activity).filter(Activity.id == activity_id).first():
            raise HTTPException(404, "Activity not found")
        months = period_months(month, fiscal_year) or [datetime.now(timezone.utc).strftime("%Y-%m")]
        resolved_district = scope_district(user, district_id)
        rows = activity_efficiency_rows(db, activity_id, months, resolved_district)
        headers = ["District", "Output Qty", "Input Qty", "Efficiency Ratio"]
        data = [[r["district_name"], r["output_qty"], r["input_qty"], r["efficiency_ratio"]] for r in rows]
    elif report == "onboarding-trend":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        result = _onboarding_trend_rows(fiscal_year, district_id, user, db)
        headers = ["Month", "Farmers Registered", "FIGs Formed"]
        data = [[m, result["farmers_monthly"][i], result["figs_monthly"][i]] for i, m in enumerate(result["months"])]
    elif report == "farmers":
        # Unlike every other report here, on-screen data IS paginated but the export never is —
        # exports are meant to be complete reports, not a dump of whatever page happens to be open.
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        query = db.query(Farmer)
        if user.role == "DISTRICT_ADMIN":
            query = query.filter(Farmer.district_id == user.district_id)
        elif user.role == "FIG_PRESIDENT":
            member_ids = [m.farmer_id for m in db.query(FigMember).filter(
                FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
            query = query.filter(Farmer.id.in_(member_ids or [""]))
        elif district_id:
            query = query.filter(Farmer.district_id == district_id)
        if seri_circle_id:
            query = query.filter(Farmer.seri_circle_id == seri_circle_id)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(Farmer.first_name.ilike(like), Farmer.last_name.ilike(like),
                                      Farmer.mobile_no.like(like), Farmer.farmer_code.ilike(like)))
        query = apply_farmer_filters(query, gender=gender, education_level_id=education_level_id,
                                      caste_id=caste_id, religion_id=religion_id,
                                      experience_min=experience_min, experience_max=experience_max,
                                      has_bank_details=has_bank_details, is_active=is_active)
        rows = farmer_report_rows(query, db)
        headers = ["Farmer Code", "Full Name", "Gender", "Date of Birth", "Mobile Number", "Aadhaar Number",
                   "PAN Number", "Education Level", "Farmer Experience (in Years)", "Primary Activities",
                   "All Activities", "Caste", "Religion", "Family Member Counts (male)",
                   "Family Member Counts (female)", "Village Name", "Panchayat", "Development Block",
                   "District", "Sericulture Circle", "Post Office", "Police Station", "PIN Code",
                   "Account Number", "Bank Name", "Branch Name", "IFSC Code", "Status"]
        data = [[r["farmer_code"], r["full_name"], r["gender"], r["date_of_birth"], r["mobile_no"], r["aadhaar_no"],
                 r["pan_no"], r["education_level_name"], r["experience_years"], r["primary_activity"],
                 r["all_activities"], r["caste_name"], r["religion_name"], r["family_member_male"],
                 r["family_member_female"], r["village_name"], r["gaon_panchayat"], r["development_block"],
                 r["district_name"], r["circle_name"], r["post_office"], r["police_station"], r["pin_code"],
                 r["account_number"], r["bank_name"], r["branch_name"], r["ifsc_code"],
                 "Active" if r["is_active"] else "Inactive"] for r in rows]
    elif report == "figs":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        query = db.query(Fig)
        if user.role == "DISTRICT_ADMIN":
            query = query.filter(Fig.district_id == user.district_id)
        elif user.role == "FIG_PRESIDENT":
            query = query.filter(Fig.id == user.fig_id)
        elif district_id:
            query = query.filter(Fig.district_id == district_id)
        if seri_circle_id:
            query = query.filter(Fig.seri_circle_id == seri_circle_id)
        if q:
            like = f"%{q}%"
            member_match = db.query(FigMember.fig_id).join(Farmer, Farmer.id == FigMember.farmer_id).filter(
                FigMember.is_active,
                or_(Farmer.farmer_code.ilike(like), Farmer.mobile_no.like(like),
                    Farmer.first_name.ilike(like), Farmer.last_name.ilike(like)),
            ).scalar_subquery()
            query = query.filter(or_(Fig.fig_code.ilike(like), Fig.fig_name.ilike(like), Fig.id.in_(member_match)))
        query = apply_fig_filters(query, stap_id=stap_id, formation_date_from=formation_date_from,
                                  formation_date_to=formation_date_to, is_active=is_active)
        rows = fig_report_rows(query, db)
        headers = ["FIG Code", "FIG Name", "Silk Type / Activity / Product", "District", "Sericulture Circle",
                   "Formation Date", "Contact Number", "Meeting Venue", "Total Members", "Members",
                   "FIG President", "FIG President Mobile Number", "Status"]
        data = [[r["fig_code"], r["fig_name"], r["stap_label"], r["district_name"], r["circle_name"],
                 r["formation_date"], r["contact_no"], r["meeting_venue"], r["total_members"],
                 r["member_names"], r["president_label"], r["president_mobile"],
                 "Active" if r["is_active"] else "Inactive"] for r in rows]
    else:
        raise HTTPException(404, f"Unknown report: {report}")

    title = report.replace("-", " ").title()
    generated_at = None
    filename = f"{report}.{format}"
    if report in ("farmers", "figs"):
        now = datetime.now(timezone.utc)
        generated_at = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        filename = f"{report}_{now.strftime('%Y%m%d_%H%M%S')}.{format}"
    body = (rows_to_xlsx(title, headers, data, generated_at=generated_at) if format == "xlsx"
            else rows_to_pdf(title, headers, data, generated_at=generated_at))
    return Response(
        content=body, media_type=_EXPORT_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
