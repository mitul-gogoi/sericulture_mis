"""Query-building and row-shaping helpers for Farmer Management's filter panel,
paginated table, and Excel/PDF export — shared by routers/farmers.py (list_farmers)
and routers/reports.py (export dispatcher's "farmers" branch)."""
from typing import Optional
from fastapi import HTTPException
from datetime import date, timedelta
from sqlalchemy import exists, func
from sqlalchemy.orm import Query, Session
from app.core.aadhaar import mask_aadhaar
from app.models import Farmer, Caste, Religion, EducationLevel, District, SericultureCircle, SilkTypeActivityProduct, Activity, SilkType, FigMember, Fig
from app.core.scope import active_district


def public_farmer_dict(f: Farmer) -> dict:
    """`model_dump()` with the Aadhaar internals stripped and replaced by a masked
    display string. THE choke point every farmer-returning endpoint must go through:
    `aadhaar_enc` must never leave the server, and `aadhaar_hash` is brute-forceable
    offline over a 12-digit space by anyone holding the key. The only endpoint allowed
    to add more than the mask is GET /farmers/me, which layers `aadhaar_full` on top."""
    d = f.model_dump()
    d.pop("aadhaar_hash", None)
    d.pop("aadhaar_enc", None)
    d.pop("aadhaar_last4", None)
    d["aadhaar_masked"] = mask_aadhaar(f.aadhaar_last4)
    return d


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
            "aadhaar_masked": mask_aadhaar(f.aadhaar_last4),
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
            "pin_code": f.pin_code,
            "account_number": f.account_number,
            "bank_name": f.bank_name,
            "branch_name": f.branch_name,
            "ifsc_code": f.ifsc_code,
            "is_active": f.is_active,
            "fig_name": fig_map[f.id].fig_name if f.id in fig_map else "Solo",
        })
    return out


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, f"{field} must be a date in YYYY-MM-DD format")


def activity_onboarding_rows(db: Session, user, district_id: Optional[str] = None,
                             month: Optional[str] = None, from_date: Optional[str] = None,
                             to_date: Optional[str] = None) -> dict:
    """How many farmers are onboarded per sericulture activity.

    Three separate double-counting hazards have to be handled, and all three are real:

    1. One activity can produce several products, so it has several STAP rows (Eri Rearing
       -> Eri Cocoon AND Eri Pupa). A farmer holding both must count ONCE for Eri Rearing.
       Handled by mapping stap_id -> activity_id before counting.
    2. `activity_name` is unique only per silk type, so "Food Plant Plantation" is three
       different activities. Grouping keys on activities.id, never the name.
    3. A farmer may genuinely do several activities and is counted in each — this is what
       the user asked for, so the per-activity figures deliberately sum to MORE than the
       headcount. `distinct_farmers` is returned alongside so the two can be reconciled.

    Timing caveat: Farmer.created_at is the only date a farmer has, and nothing records
    when an activity was added to them. So a month figure means "registered in that month
    and doing this activity today", not "started this activity that month".
    """
    stap_activity = dict(
        db.query(SilkTypeActivityProduct.id, SilkTypeActivityProduct.activity_id).all())

    activities = (db.query(Activity, SilkType)
                  .join(SilkType, SilkType.id == Activity.silk_type_id)
                  .filter(Activity.is_active)
                  .order_by(SilkType.silk_type_name, Activity.step_no).all())

    q = db.query(Farmer.id, Farmer.district_id, Farmer.stap_ids)
    if user.role == "DISTRICT_ADMIN":
        q = q.filter(Farmer.district_id == active_district(user))
    elif district_id:
        q = q.filter(Farmer.district_id == district_id)
    if month:
        q = q.filter(func.to_char(Farmer.created_at, "YYYY-MM") == month)
    if from_date:
        q = q.filter(Farmer.created_at >= _parse_date(from_date, "from_date"))
    if to_date:
        # created_at carries a time component, so "<= to_date" would drop everything
        # registered later that same day. Compare against the start of the NEXT day instead.
        q = q.filter(Farmer.created_at < _parse_date(to_date, "to_date") + timedelta(days=1))

    # Only three columns, not whole ORM rows: stap_ids is a `json` column (not `jsonb`), so
    # Postgres containment operators and GIN indexes are unavailable and membership has to be
    # resolved in Python — the same approach every other consumer of this column already takes.
    by_activity: dict[str, set] = {}
    farmer_ids = set()
    for fid, _district, stap_ids in q.all():
        farmer_ids.add(fid)
        for sid in (stap_ids or []):
            aid = stap_activity.get(sid)
            if aid:
                by_activity.setdefault(aid, set()).add(fid)

    items = [{
        "activity_id": a.id,
        "silk_type_name": st.silk_type_name,
        "activity_name": a.activity_name,
        "step_no": a.step_no,
        "farmers": len(by_activity.get(a.id, ())),
    } for a, st in activities]

    return {"items": items, "distinct_farmers": len(farmer_ids)}
