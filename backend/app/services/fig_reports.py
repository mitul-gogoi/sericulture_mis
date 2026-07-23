"""Query-building and row-shaping helpers for FIG Management's filter panel,
paginated table, and Excel/PDF export — shared by routers/figs.py (list_figs)
and routers/reports.py (export dispatcher's "figs" branch)."""
from typing import Optional
from sqlalchemy.orm import Query, Session
from app.models import Fig, FigMember, Farmer, District, SericultureCircle, SilkTypeActivityProduct, SilkType, Activity, Product


def apply_fig_filters(
    query: Query,
    stap_id: Optional[str] = None,
    formation_date_from: Optional[str] = None,
    formation_date_to: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Query:
    """Pure additive filter application — every param is optional and a no-op when None,
    so callers that never pass these (the legacy GET /figs consumers) are unaffected."""
    if stap_id:
        query = query.filter(Fig.stap_id == stap_id)
    if formation_date_from:
        query = query.filter(Fig.formation_date >= formation_date_from)
    if formation_date_to:
        query = query.filter(Fig.formation_date <= formation_date_to)
    if is_active is not None:
        query = query.filter(Fig.is_active == is_active)
    return query


def member_names_by_fig(fig_ids: list[str], db: Session) -> dict[str, list[str]]:
    """Active member display names ('First Last'), grouped by fig_id — used to populate
    the table's/export's "Members" column without a separate request per FIG."""
    rows = db.query(FigMember, Farmer).join(Farmer, Farmer.id == FigMember.farmer_id).filter(
        FigMember.fig_id.in_(fig_ids or [""]), FigMember.is_active,
    ).all()
    out: dict[str, list[str]] = {}
    for m, f in rows:
        out.setdefault(m.fig_id, []).append(" ".join(filter(None, [f.first_name, f.last_name])))
    return out


def president_by_fig(fig_ids: list[str], db: Session) -> dict[str, dict]:
    """Active FIG President per fig_id — same FigMember(role='President')+Farmer join
    already used to badge the president in the detail modal's Members table."""
    rows = db.query(FigMember, Farmer).join(Farmer, Farmer.id == FigMember.farmer_id).filter(
        FigMember.fig_id.in_(fig_ids or [""]), FigMember.is_active, FigMember.role == "President",
    ).all()
    return {m.fig_id: {"name": " ".join(filter(None, [f.first_name, f.last_name])),
                       "farmer_code": f.farmer_code, "mobile_no": f.mobile_no} for m, f in rows}


def fig_report_rows(query: Query, db: Session) -> list[dict]:
    """Unpaginated, export-shaped rows covering every field on the FIG Details export:
    joins in stap label (silk type · activity · product), district/circle names, member
    names, and the active president's name/code/mobile. `query` must already have every
    filter and role-scope applied (identical to the paginated on-screen query, minus
    .offset()/.limit())."""
    rows = query.order_by(Fig.created_at.desc()).all()
    district_names = {d.id: d.district_name for d in db.query(District).all()}
    circle_names = {c.id: c.circle_name for c in db.query(SericultureCircle).all()}
    silk_types = {s.id: s.silk_type_name for s in db.query(SilkType).all()}
    activities = {a.id: a.activity_name for a in db.query(Activity).all()}
    products = {p.id: p.product_name for p in db.query(Product).all()}
    staps = {s.id: s for s in db.query(SilkTypeActivityProduct).all()}
    fig_ids = [f.id for f in rows]
    members = member_names_by_fig(fig_ids, db)
    presidents = president_by_fig(fig_ids, db)

    def stap_label(stap_id: Optional[str]) -> Optional[str]:
        s = staps.get(stap_id)
        if not s:
            return None
        return f"{silk_types.get(s.silk_type_id)} · {activities.get(s.activity_id)} · {products.get(s.product_id)}"

    out = []
    for f in rows:
        pres = presidents.get(f.id)
        out.append({
            "fig_code": f.fig_code,
            "fig_name": f.fig_name,
            "stap_label": stap_label(f.stap_id),
            "district_name": district_names.get(f.district_id),
            "circle_name": circle_names.get(f.seri_circle_id),
            "formation_date": f.formation_date.isoformat() if f.formation_date else None,
            "contact_no": f.contact_no,
            "meeting_venue": f.meeting_venue,
            "total_members": len(members.get(f.id, [])),
            "member_names": ", ".join(members.get(f.id, [])) or None,
            "president_label": f"{pres['name']} ({pres['farmer_code']})" if pres else None,
            "president_mobile": pres["mobile_no"] if pres else None,
            "is_active": f.is_active,
        })
    return out
