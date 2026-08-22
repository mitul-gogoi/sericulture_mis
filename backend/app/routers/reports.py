"""Reports & dashboards (PostgreSQL aggregations)."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.services.fiscal import period_months, fy_to_months, month_range
from app.services.export import rows_to_xlsx, rows_to_pdf
from app.services.analytics import scope_district
from app.services.farmer_reports import apply_farmer_filters, farmer_report_rows, activity_onboarding_rows
from app.services.fig_reports import apply_fig_filters, fig_report_rows
from app.services.land_reports import land_report_rows
from app.services.meeting_reports import submission_status_rows, fp_submission_history_rows
from app.services.assets import asset_report_rows
from app.services import yield_matrix
from app.core.scope import active_district
from app.models import (
    Farmer, Fig, District, Land, Training, FigMember, Meeting, Yield_,
    User, Product, ByproductEntry, Stock, MeetingCorrection,
    SilkType, Activity, SilkTypeActivityProduct, AssetInstance, FigActivity,
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
            "pending_corrections": db.query(func.count(MeetingCorrection.id)).filter(MeetingCorrection.status == "PENDING").scalar() or 0,
            "current_month": cur_month,
            "monthly_submitted_count": db.query(func.count(Meeting.id)).filter(Meeting.meeting_month == cur_month).scalar() or 0,
        }
    if user.role == "DISTRICT_ADMIN":
        farmer_ids = [f.id for f in db.query(Farmer.id).filter(Farmer.district_id == active_district(user)).all()]
        fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == active_district(user), Fig.is_active).all()]
        cur_month = datetime.now(timezone.utc).strftime("%Y-%m")
        return {
            "farmers": db.query(func.count(Farmer.id)).filter(
                Farmer.district_id == active_district(user), Farmer.is_active).scalar() or 0,
            "figs": db.query(func.count(Fig.id)).filter(
                Fig.district_id == active_district(user), Fig.is_active).scalar() or 0,
            "activities": db.query(func.count(func.distinct(FigActivity.activity_id))).join(
                Fig, Fig.id == FigActivity.fig_id).filter(
                Fig.district_id == active_district(user), Fig.is_active).scalar() or 0,
            "total_members": db.query(func.count(FigMember.id)).filter(
                FigMember.fig_id.in_(fig_ids or [""]), FigMember.is_active).scalar() or 0,
            "lands_pending": db.query(func.count(Land.id)).filter(
                Land.farmer_id.in_(farmer_ids or [""]),
                Land.gps_verified == "Pending").scalar() or 0,
            "assets_gps_pending": db.query(func.count(AssetInstance.id)).filter(
                AssetInstance.owner_id.in_((farmer_ids + fig_ids) or [""]),
                AssetInstance.gps_status == "Pending").scalar() or 0,
            "pending_trainings": db.query(func.count(Training.id)).filter(
                Training.district_id == active_district(user), Training.status == "Pending").scalar() or 0,
            "current_month": cur_month,
            "monthly_submitted_count": db.query(func.count(Meeting.id)).filter(
                Meeting.fig_id.in_(fig_ids or [""]), Meeting.meeting_month == cur_month).scalar() or 0,
        }
    if user.role == "FIG_PRESIDENT":
        fig = db.query(Fig).filter(Fig.id == user.fig_id).first()
        district = db.query(District).filter(District.id == active_district(user)).first()
        members = db.query(func.count(FigMember.id)).filter(
            FigMember.fig_id == user.fig_id, FigMember.is_active).scalar() or 0
        meetings = db.query(func.count(Meeting.id)).filter(Meeting.fig_id == user.fig_id).scalar() or 0
        cur_month = datetime.now(timezone.utc).strftime("%Y-%m")
        submitted = db.query(Meeting).filter(Meeting.fig_id == user.fig_id,
                                              Meeting.meeting_month == cur_month).first() is not None
        member_ids = [m.farmer_id for m in db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
        # "Needs GPS" = never submitted or a prior submission was rejected — Pending/Verified
        # already have a live or in-review submission and don't belong in a Quick Actions backlog.
        lands_needing_gps = db.query(func.count(Land.id)).filter(
            Land.farmer_id.in_(member_ids or [""]),
            Land.gps_verified.in_(("Not Submitted", "Failed"))).scalar() or 0
        assets_needing_gps = db.query(func.count(AssetInstance.id)).filter(
            AssetInstance.owner_id.in_((member_ids + [user.fig_id or ""]) or [""]),
            AssetInstance.gps_status.in_(("Not Submitted", "Failed"))).scalar() or 0
        return {"members": members, "meetings": meetings,
                "submitted_this_month": submitted, "current_month": cur_month,
                "fig_name": fig.fig_name if fig else None, "fig_code": fig.fig_code if fig else None,
                "district_name": district.district_name if district else None,
                "lands_needing_gps": lands_needing_gps, "assets_needing_gps": assets_needing_gps}
    return {}


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




def _scope_yield_query(q, user: User, district_id: Optional[str], db: Session):
    """Shared FIG-scoping ladder used by every Yield_-based report endpoint."""
    if user.role == "FARMER":
        return q.filter(Yield_.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        return q.filter(Yield_.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        return q.filter(Yield_.district_id == active_district(user))
    elif district_id:
        return q.filter(Yield_.district_id == district_id)
    return q


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
    if user.role == "FARMER":
        bp_q = bp_q.filter(ByproductEntry.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        bp_q = bp_q.filter(ByproductEntry.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        bp_q = bp_q.filter(ByproductEntry.district_id == active_district(user))
    elif district_id:
        bp_q = bp_q.filter(ByproductEntry.district_id == district_id)
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
    if user.role == "FARMER":
        q = q.filter(Stock.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        q = q.filter(Stock.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        q = q.filter(Stock.district_id == active_district(user))
    elif district_id:
        q = q.filter(Stock.district_id == district_id)
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
        farmer_q = farmer_q.filter(Farmer.district_id == active_district(user))
        fig_q = fig_q.filter(Fig.district_id == active_district(user))
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


@router.get("/activity-onboarding")
def activity_onboarding(district_id: Optional[str] = None, month: Optional[str] = None,
                        from_date: Optional[str] = None, to_date: Optional[str] = None,
                        user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                        db: Session = Depends(get_session)):
    """Distinct farmers per activity. No period params at all means all-time (cumulative)."""
    if month and (from_date or to_date):
        raise HTTPException(400, "Provide either month or a from_date/to_date range, not both")
    return activity_onboarding_rows(db, user, district_id, month, from_date, to_date)


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
                  has_fig: Optional[bool] = None,
                  stap_id: Optional[str] = None, formation_date_from: Optional[str] = None,
                  formation_date_to: Optional[str] = None,
                  product_id: Optional[str] = None, activity_id: Optional[str] = None,
                  level: Optional[str] = None, from_month: Optional[str] = None, to_month: Optional[str] = None,
                  from_date: Optional[str] = None, to_date: Optional[str] = None,
                  product_ids: Optional[str] = None,
                  owner_type: Optional[str] = None, asset_type_id: Optional[str] = None,
                  status: Optional[str] = None, verification_status: Optional[str] = None,
                  confidence: Optional[str] = None, gps_status: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """Shared Excel/PDF export dispatcher — every exportable report's row-fetching logic
    lives in a plain `_xxx_rows` function reused by both its JSON endpoint and this
    dispatcher, so the export always matches exactly what's on screen."""
    if format not in _EXPORT_MEDIA_TYPES:
        raise HTTPException(400, "format must be 'xlsx' or 'pdf'")

    if report == "product-summary":
        rows = _product_summary_rows(month, fiscal_year, district_id, user, db)
        headers = ["Product", "Unit", "Silk Types", "Planned", "Actual", "Byproduct Qty"]
        data = [[r["product_name"], r["unit_of_measure"], ", ".join(s["name"] for s in r["silk_types"]),
                r["planned"], r["actual"], r["byproduct_qty"]] for r in rows]
    elif report == "stock-summary":
        rows = _stock_summary_rows(district_id, user, db)
        headers = ["Product", "Unit", "Current Stock", "Perishable"]
        data = [[r["product_name"], r["unit_of_measure"], r["stock"], "Yes" if r["is_perishable"] else "No"] for r in rows]
    elif report == "farmers":
        # Unlike every other report here, on-screen data IS paginated but the export never is —
        # exports are meant to be complete reports, not a dump of whatever page happens to be open.
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        query = db.query(Farmer)
        if user.role == "DISTRICT_ADMIN":
            query = query.filter(Farmer.district_id == active_district(user))
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
                                      has_bank_details=has_bank_details, is_active=is_active, has_fig=has_fig)
        rows = farmer_report_rows(query, db)
        headers = ["Farmer Code", "Full Name", "Gender", "Date of Birth", "Mobile Number", "Aadhaar (masked)",
                   "PAN Number", "Education Level", "Farmer Experience (in Years)",
                   "Activities", "Caste", "Religion", "Family Member Counts (male)",
                   "Family Member Counts (female)", "Village Name", "Panchayat", "Development Block",
                   "District", "Sericulture Circle", "Post Office", "PIN Code",
                   "Account Number", "Bank Name", "Branch Name", "IFSC Code", "Status", "FIG Membership"]
        data = [[r["farmer_code"], r["full_name"], r["gender"], r["date_of_birth"], r["mobile_no"], r["aadhaar_masked"],
                 r["pan_no"], r["education_level_name"], r["experience_years"],
                 r["all_activities"], r["caste_name"], r["religion_name"], r["family_member_male"],
                 r["family_member_female"], r["village_name"], r["gaon_panchayat"], r["development_block"],
                 r["district_name"], r["circle_name"], r["post_office"], r["pin_code"],
                 r["account_number"], r["bank_name"], r["branch_name"], r["ifsc_code"],
                 "Active" if r["is_active"] else "Inactive", r["fig_name"]] for r in rows]
    elif report == "activity-onboarding":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        result = activity_onboarding_rows(db, user, district_id, month, from_date, to_date)
        headers = ["Silk Type", "Activity", "Farmers Onboarded"]
        data = [[r["silk_type_name"], r["activity_name"], r["farmers"]] for r in result["items"]]
        # A farmer doing several activities is counted in each, so this total is intentionally
        # larger than the headcount — spell that out rather than let the reader guess.
        data.append(["", "Distinct farmers (counted once each)", result["distinct_farmers"]])
    elif report == "figs":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        query = db.query(Fig)
        if user.role == "DISTRICT_ADMIN":
            query = query.filter(Fig.district_id == active_district(user))
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
                   "FIG President", "FIG President Mobile Number", "Documents", "Status"]
        data = [[r["fig_code"], r["fig_name"], r["stap_label"], r["district_name"], r["circle_name"],
                 r["formation_date"], r["contact_no"], r["meeting_venue"], r["total_members"],
                 r["member_names"], r["president_label"], r["president_mobile"], r["documents"],
                 "Active" if r["is_active"] else "Inactive"] for r in rows]
    elif report == "lands":
        # View access mirrors GET /lands' own role scoping exactly — State Admin is
        # view-only for verify/reject (see POST /lands/verify) but exporting is a view
        # action, so SA keeps unscoped export access same as the on-screen table.
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        query = db.query(Land)
        if user.role == "DISTRICT_ADMIN":
            farmer_ids = [f.id for f in db.query(Farmer).filter(Farmer.district_id == active_district(user)).all()]
            query = query.filter(Land.farmer_id.in_(farmer_ids or [""]))
        elif user.role == "FIG_PRESIDENT":
            member_ids = [m.farmer_id for m in db.query(FigMember).filter(
                FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
            query = query.filter(Land.farmer_id.in_(member_ids or [""]))
        rows = land_report_rows(query.order_by(Land.created_at.desc()).all(), db)
        headers = ["Dag No", "Patta No", "Farmer Code", "Farmer Name", "Area (Bigha)", "Area (Hectare)",
                   "Village Name", "Panchayat", "Development Block", "Sericulture Circle", "District"]
        data = [[r["dag_no"], r["patta_no"], r["farmer_code"], r["farmer_name"],
                 r["land_area_bigha"], r["land_area_hectare"], r["village_name"],
                 r["gaon_panchayat"], r["development_block"], r["circle_name"], r["district_name"]]
                for r in rows]
    elif report == "assets":
        # Exporting is a view action — State Admin keeps unscoped access same as the
        # on-screen table, even though SA has no write actions on Assets (see POST/PATCH
        # /assets role gates, DISTRICT_ADMIN-only).
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN", "FIG_PRESIDENT"):
            raise HTTPException(403, "State/District Admin/FIG President only")
        query = db.query(AssetInstance)
        if owner_type:
            query = query.filter(AssetInstance.owner_type == owner_type)
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
        if q or district_id or seri_circle_id:
            farmer_q = db.query(Farmer.id)
            fig_q = db.query(Fig.id)
            if district_id:
                farmer_q = farmer_q.filter(Farmer.district_id == district_id)
                fig_q = fig_q.filter(Fig.district_id == district_id)
            if seri_circle_id:
                farmer_q = farmer_q.filter(Farmer.seri_circle_id == seri_circle_id)
                fig_q = fig_q.filter(Fig.seri_circle_id == seri_circle_id)
            if q:
                like = f"%{q}%"
                farmer_q = farmer_q.filter(or_(
                    Farmer.farmer_code.ilike(like), Farmer.mobile_no.ilike(like),
                    Farmer.first_name.ilike(like), Farmer.last_name.ilike(like)))
                fig_q = fig_q.filter(or_(Fig.fig_code.ilike(like), Fig.fig_name.ilike(like)))
            farmer_ids = [r[0] for r in farmer_q.all()]
            fig_ids = [r[0] for r in fig_q.all()]
            query = query.filter(or_(
                and_(AssetInstance.owner_type == "FARMER", AssetInstance.owner_id.in_(farmer_ids or [""])),
                and_(AssetInstance.owner_type == "FIG", AssetInstance.owner_id.in_(fig_ids or [""])),
            ))
        if user.role == "DISTRICT_ADMIN":
            farmer_ids2 = [f.id for f in db.query(Farmer).filter(Farmer.district_id == active_district(user)).all()]
            fig_ids2 = [g.id for g in db.query(Fig).filter(Fig.district_id == active_district(user)).all()]
            query = query.filter(AssetInstance.owner_id.in_((farmer_ids2 + fig_ids2) or [""]))
        elif user.role == "FIG_PRESIDENT":
            member_ids = [m.farmer_id for m in db.query(FigMember).filter(
                FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
            query = query.filter(AssetInstance.owner_id.in_((member_ids + [user.fig_id or ""]) or [""]))
        rows = asset_report_rows(query.order_by(AssetInstance.created_at.desc()).all(), db)
        headers = ["Asset Code", "Asset Type", "Qty", "Owner Type", "Owner Code", "Owner Name",
                   "Acquired Date", "Age Left (days)", "Acquired Mode", "Name of the Scheme",
                   "Confidence Mode", "District", "Sericulture Circle", "GPS Status", "Latitude",
                   "Longitude", "Verification Status", "Verified By", "Status", "Remarks"]
        data = [[r["asset_code"], r["asset_type_name"], r["quantity"], r["owner_type"], r["owner_code"],
                 r["owner_name"], r["acquisition_date"], r["age_left_days"], r["acquisition_mode"],
                 r["scheme_name"], r["confidence"], r["district_name"], r["circle_name"],
                 r["gps_status"], r["latitude"], r["longitude"], r["verification_status"],
                 r["last_verified_by_name"], r["status"], r["remarks"]]
                for r in rows]
    elif report == "submission-status":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        if not month:
            raise HTTPException(400, "month is required")
        district_scope = active_district(user) if user.role == "DISTRICT_ADMIN" else None
        rows = submission_status_rows(db, user.role, district_scope, month)
        headers = ["FIG", "District", "Status", "Submitted On"]
        data = [[r["fig_name"], r["district_name"], r["status"], r["submitted_on"]] for r in rows]
    elif report == "submission-history":
        if user.role != "FIG_PRESIDENT":
            raise HTTPException(403, "FIG President only")
        rows = fp_submission_history_rows(db, user.fig_id)
        headers = ["Month", "Meeting Title", "Submission Date", "Venue", "Re-submitted"]
        data = [[r["month"], r["meeting_title"], r["submitted_on"], r["venue"], r["re_submitted"]] for r in rows]
    elif report == "yield-matrix":
        if user.role not in ("STATE_ADMIN", "DISTRICT_ADMIN"):
            raise HTTPException(403, "State/District Admin only")
        if not level or level not in yield_matrix.LEVELS:
            raise HTTPException(400, f"level must be one of: {', '.join(yield_matrix.LEVELS)}")
        if level == "state" and user.role != "STATE_ADMIN":
            raise HTTPException(403, "State Admin only")
        months = period_months(month, fiscal_year)
        if months is None and from_month and to_month:
            months = month_range(from_month, to_month)
        if months is None:
            months = [datetime.now(timezone.utc).strftime("%Y-%m")]
        district_scope = scope_district(user, None)
        requested = [p for p in product_ids.split(",") if p] if product_ids else None

        # Export is never paginated — reuses the full unpaginated entity universe so the
        # download always matches the on-screen filters exactly, just not the on-screen page.
        entities, _ = yield_matrix.entities_page(db, level, district_scope, page=1, page_size=1_000_000)
        avail = yield_matrix.available_products(db, level, district_scope, months)
        input_ids, output_ids, stock_ids = yield_matrix.resolve_column_ids(avail, requested)
        input_sources = yield_matrix.available_input_sources(db, level, district_scope, months, input_ids)
        matrix = yield_matrix.build_matrix(db, level, entities, months, input_ids, output_ids, stock_ids, input_sources)

        # "meeting" doesn't fit the generic "Entity + breadcrumbs" shape every other level
        # uses (row["name"] is a farmer, but Meeting ID/Month need to come *before* it, and it
        # carries its own raw-record-only Excel columns) — handled as its own branch throughout.
        is_meeting = level == "meeting"
        if is_meeting:
            headers = ["Meeting ID", "Meeting Month", "Farmer", "Farmer Code",
                       "District", "Sericulture Circle", "FIG", "FIG Code",
                       "Meeting Title", "Meeting Date", "Meeting Venue", "Farmer Mobile Number"]
        else:
            context_labels = {
                "state": [],
                "farmer": ["Farmer Code", "District", "Sericulture Circle", "FIG", "FIG Code"],
                "fig": ["FIG Code", "District", "Sericulture Circle"],
                "sericulture_circle": ["District"],
                "district": [],
            }[level]
            context_keys = {
                "state": [],
                "farmer": ["farmer_code", "district_name", "seri_circle_name", "fig_name", "fig_code"],
                "fig": ["fig_code", "district_name", "seri_circle_name"],
                "sericulture_circle": ["district_name"],
                "district": [],
            }[level]
            headers = ["Entity"] + context_labels

        # Excel always carries every possible column (full INPUT per-source breakdown, every
        # OUTPUT sub-field) regardless of what the on-screen YieldMatrixTable trims — this
        # dispatcher is deliberately NOT kept in lockstep with the on-screen column set.
        for p in matrix["input_products"]:
            headers.append(f"{p['product_name']} (Input Total, {p['unit_of_measure']})")
            for source in p["sources"]:
                headers.append(f"{p['product_name']} — {source} (Input, {p['unit_of_measure']})")
        for p in matrix["output_products"]:
            headers.append(f"{p['product_name']} (Planned)")
            headers.append(f"{p['product_name']} (Actual)")
            for er in p["expected_ranges"]:
                headers.append(f"{p['product_name']} (Expected, via {er['input_product_name']})")
            headers.append(f"{p['product_name']} (Loss Reason)")
            headers.append(f"{p['product_name']} (Next Plan)")
            headers.append(f"{p['product_name']} (Sold Qty)")
            headers.append(f"{p['product_name']} (Sold Rate)")
            headers.append(f"{p['product_name']} (Total Earned)")
        # "meeting" rows carry the historical stock_balance from that one record, not a live
        # snapshot — labelled distinctly so it's never confused with every other level's Stock.
        stock_suffix = "at submission" if is_meeting else None
        headers += [f"{p['product_name']} (Stock, {stock_suffix or p['unit_of_measure']})" for p in matrix["stock_products"]]

        data = []
        for row in matrix["items"]:
            if is_meeting:
                line = [row.get("meeting_id") or "—", row.get("meeting_month") or "—",
                        row["name"], row.get("farmer_code") or "—",
                        row.get("district_name") or "—", row.get("seri_circle_name") or "—",
                        row.get("fig_name") or "—", row.get("fig_code") or "—",
                        row.get("meeting_title") or "—", row.get("meeting_date") or "—",
                        row.get("meeting_venue") or "—", row.get("farmer_mobile") or "—"]
            else:
                line = [row["name"]] + [row.get(k) or "—" for k in context_keys]
            for p in matrix["input_products"]:
                cell = row["input"].get(p["id"], {"total": 0, "by_source": {}})
                line.append(cell["total"])
                for source in p["sources"]:
                    line.append(cell["by_source"].get(source, 0))
            for p in matrix["output_products"]:
                cell = row["output"].get(p["id"], {"planned": 0, "actual": 0, "expected_ranges": {},
                                                     "next_month_plan": 0, "sold_quantity": 0,
                                                     "earning": 0, "sold_rate": None, "loss_reason_name": None})
                line.append(cell["planned"])
                line.append(cell["actual"])
                for er in p["expected_ranges"]:
                    rng = cell["expected_ranges"].get(er["standard_id"])
                    line.append(f"{rng['min']}–{rng['max']}" if rng else "—")
                line.append(cell["loss_reason_name"] or "—")
                line.append(cell["next_month_plan"])
                line.append(cell["sold_quantity"])
                line.append(cell["sold_rate"] if cell["sold_rate"] is not None else "—")
                line.append(cell["earning"])
            line += [row["stock"].get(p["id"], 0) for p in matrix["stock_products"]]
            data.append(line)
    else:
        raise HTTPException(404, f"Unknown report: {report}")

    title = report.replace("-", " ").title()
    generated_at = None
    filename = f"{report}.{format}"
    if report in ("farmers", "figs", "lands", "assets", "submission-status", "submission-history",
                  "activity-onboarding"):
        now = datetime.now(timezone.utc)
        generated_at = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        filename = f"{report}_{now.strftime('%Y%m%d_%H%M%S')}.{format}"
    body = (rows_to_xlsx(title, headers, data, generated_at=generated_at) if format == "xlsx"
            else rows_to_pdf(title, headers, data, generated_at=generated_at))
    return Response(
        content=body, media_type=_EXPORT_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
