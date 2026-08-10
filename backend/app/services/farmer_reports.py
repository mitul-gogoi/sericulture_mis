"""Query-building and row-shaping helpers for Farmer Management's filter panel,
paginated table, and Excel/PDF export — shared by routers/farmers.py (list_farmers)
and routers/reports.py (export dispatcher's "farmers" branch)."""
from typing import Optional
from sqlalchemy import exists
from sqlalchemy.orm import Query, Session
from app.models import Farmer, Caste, Religion, EducationLevel, District, SericultureCircle, SilkTypeActivityProduct, Activity, FigMember, Fig


def apply_farmer_filters(
    query: Query,
    gender: Optional[str] = None,
    education_level_id: Optional[str] = None,
    caste_id: Optional[str] = None,
    religion_id: Optional[str] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    has_bank_details: Optional[bool] = None,
    is_active: Optional[bool] = None,
    has_fig: Optional[bool] = None,
) -> Query:
    """Pure additive filter application — every param is optional and a no-op when None,
    so callers that never pass these (the legacy GET /farmers consumers) are unaffected."""
    if gender:
        query = query.filter(Farmer.gender == gender)
    if education_level_id:
        query = query.filter(Farmer.education_level_id == education_level_id)
    if caste_id:
        query = query.filter(Farmer.caste_id == caste_id)
    if religion_id:
        query = query.filter(Farmer.religion_id == religion_id)
    if experience_min is not None:
        query = query.filter(Farmer.experience_years >= experience_min)
    if experience_max is not None:
        query = query.filter(Farmer.experience_years <= experience_max)
    if has_bank_details is not None:
        has_expr = Farmer.account_number.isnot(None) & (Farmer.account_number != "")
        query = query.filter(has_expr if has_bank_details else ~has_expr)
    if is_active is not None:
        query = query.filter(Farmer.is_active == is_active)
    if has_fig is not None:
        member_exists = exists().where(FigMember.farmer_id == Farmer.id, FigMember.is_active)
        query = query.filter(member_exists if has_fig else ~member_exists)
    return query


def fig_by_farmer(db: Session, farmer_ids: list[str]) -> dict[str, Fig]:
    """A farmer's *current* FIG, resolved via FigMember.is_active alone — the same
    "current membership" convention used everywhere else in this codebase. A farmer
    with no active membership (a solo farmer) is simply absent from the returned dict."""
    if not farmer_ids:
        return {}
    rows = (
        db.query(FigMember.farmer_id, Fig)
        .join(Fig, Fig.id == FigMember.fig_id)
        .filter(FigMember.farmer_id.in_(farmer_ids), FigMember.is_active)
        .all()
    )
    return {farmer_id: fig for farmer_id, fig in rows}


def farmer_report_rows(query: Query, db: Session) -> list[dict]:
    """Unpaginated, export-shaped rows covering every field on the Farmer Details
    export: joins in caste/religion/district/sericulture-circle names and resolves
    stap_id(s) to their Activity names. `query` must already have every filter and
    role-scope applied (identical to the paginated on-screen query, minus
    .offset()/.limit()) — used only by the export dispatcher, never by the
    on-screen table, which stays paginated."""
    rows = query.order_by(Farmer.created_at.desc()).all()
    caste_names = {c.id: c.caste_name for c in db.query(Caste).all()}
    religion_names = {r.id: r.religion_name for r in db.query(Religion).all()}
    education_level_names = {e.id: e.education_level_name for e in db.query(EducationLevel).all()}
    district_names = {d.id: d.district_name for d in db.query(District).all()}
    circle_names = {c.id: c.circle_name for c in db.query(SericultureCircle).all()}
    stap_activity = {
        stap.id: activity.activity_name
        for stap, activity in db.query(SilkTypeActivityProduct, Activity)
        .join(Activity, Activity.id == SilkTypeActivityProduct.activity_id).all()
    }
    fig_map = fig_by_farmer(db, [f.id for f in rows])
    out = []
    for f in rows:
        all_activities = []
        for sid in (f.stap_ids or []):
            name = stap_activity.get(sid)
            if name and name not in all_activities:
                all_activities.append(name)
        out.append({
            "farmer_code": f.farmer_code,
            "full_name": " ".join(filter(None, [f.first_name, f.middle_name, f.last_name])),
            "gender": f.gender,
            "date_of_birth": f.date_of_birth.isoformat() if f.date_of_birth else None,
            "mobile_no": f.mobile_no,
            "aadhaar_no": f.aadhaar_no,
            "pan_no": f.pan_no,
            "education_level_name": education_level_names.get(f.education_level_id),
            "experience_years": f.experience_years,
            "primary_activity": stap_activity.get(f.primary_stap_id) if f.primary_stap_id else None,
            "all_activities": ", ".join(all_activities) if all_activities else None,
            "caste_name": caste_names.get(f.caste_id),
            "religion_name": religion_names.get(f.religion_id),
            "family_member_male": f.family_member_male,
            "family_member_female": f.family_member_female,
            "village_name": f.village_name,
            "gaon_panchayat": f.gaon_panchayat,
            "development_block": f.development_block,
            "district_name": district_names.get(f.district_id),
            "circle_name": circle_names.get(f.seri_circle_id),
            "post_office": f.post_office,
            "police_station": f.police_station,
            "pin_code": f.pin_code,
            "account_number": f.account_number,
            "bank_name": f.bank_name,
            "branch_name": f.branch_name,
            "ifsc_code": f.ifsc_code,
            "is_active": f.is_active,
            "fig_name": fig_map[f.id].fig_name if f.id in fig_map else "Solo",
        })
    return out
