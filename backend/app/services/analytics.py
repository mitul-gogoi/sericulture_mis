"""Query-building and role-scoping helpers for the Analytics drill-down module.

Every function here returns a single SQL GROUP BY query's rows — no per-row
Python loops over full tables (that anti-pattern was the reason this module
exists as a separate, carefully-built layer; see reports.py's district-comparison
history for what NOT to do at this data volume).
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Farmer, Fig, FigMember, District, SericultureCircle, User, SilkType, SilkTypeActivityProduct
from app.core.scope import active_district


def scope_district(user: User, district_id: Optional[str]) -> Optional[str]:
    """DISTRICT_ADMIN is pinned to their own district; STATE_ADMIN may pass any (or none, for state level)."""
    if user.role == "DISTRICT_ADMIN":
        if district_id and district_id != active_district(user):
            raise HTTPException(403, "Cannot access another district's analytics")
        return active_district(user)
    return district_id


def scope_fig(user: User, fig_id: Optional[str]) -> str:
    """FIG_PRESIDENT is pinned to their own FIG; other roles must supply one explicitly."""
    if user.role == "FIG_PRESIDENT":
        if fig_id and fig_id != user.fig_id:
            raise HTTPException(403, "Cannot access another FIG's analytics")
        return user.fig_id
    if not fig_id:
        raise HTTPException(400, "fig_id is required at this level")
    return fig_id


# ---- Farmers ----
def farmers_by_district(db: Session) -> list[dict]:
    rows = db.query(Farmer.district_id, District.district_name, func.count(Farmer.id).label("count")) \
        .join(District, District.id == Farmer.district_id) \
        .filter(Farmer.is_active) \
        .group_by(Farmer.district_id, District.district_name) \
        .order_by(District.district_name).all()
    return [{"id": r.district_id, "name": r.district_name, "count": int(r.count)} for r in rows]


def farmers_by_circle(db: Session, district_id: str) -> list[dict]:
    rows = db.query(Farmer.seri_circle_id, SericultureCircle.circle_name, func.count(Farmer.id).label("count")) \
        .join(SericultureCircle, SericultureCircle.id == Farmer.seri_circle_id) \
        .filter(Farmer.is_active, Farmer.district_id == district_id) \
        .group_by(Farmer.seri_circle_id, SericultureCircle.circle_name) \
        .order_by(SericultureCircle.circle_name).all()
    return [{"id": r.seri_circle_id, "name": r.circle_name, "count": int(r.count)} for r in rows]


# ---- FIGs ----
def figs_by_district(db: Session) -> list[dict]:
    rows = db.query(Fig.district_id, District.district_name, func.count(Fig.id).label("count")) \
        .join(District, District.id == Fig.district_id) \
        .filter(Fig.is_active) \
        .group_by(Fig.district_id, District.district_name) \
        .order_by(District.district_name).all()
    return [{"id": r.district_id, "name": r.district_name, "count": int(r.count)} for r in rows]


def figs_by_circle(db: Session, district_id: str) -> list[dict]:
    rows = db.query(Fig.seri_circle_id, SericultureCircle.circle_name, func.count(Fig.id).label("count")) \
        .join(SericultureCircle, SericultureCircle.id == Fig.seri_circle_id) \
        .filter(Fig.is_active, Fig.district_id == district_id) \
        .group_by(Fig.seri_circle_id, SericultureCircle.circle_name) \
        .order_by(SericultureCircle.circle_name).all()
    return [{"id": r.seri_circle_id, "name": r.circle_name, "count": int(r.count)} for r in rows]


def figs_in_circle(db: Session, seri_circle_id: str) -> list[dict]:
    """Terminal level of the FIGs drill-down — individual FIGs within a circle, with enough
    detail (code, silk type, live member count, formation date) to stand in for a mini FIG
    profile without a further click-through."""
    rows = db.query(
        Fig.id, Fig.fig_name, Fig.fig_code, Fig.formation_date, SilkType.silk_type_name,
        func.count(func.distinct(FigMember.id)).label("member_count"),
    ).join(SilkTypeActivityProduct, SilkTypeActivityProduct.id == Fig.stap_id) \
     .join(SilkType, SilkType.id == SilkTypeActivityProduct.silk_type_id) \
     .outerjoin(FigMember, (FigMember.fig_id == Fig.id) & (FigMember.is_active)) \
     .filter(Fig.is_active, Fig.seri_circle_id == seri_circle_id) \
     .group_by(Fig.id, Fig.fig_name, Fig.fig_code, Fig.formation_date, SilkType.silk_type_name) \
     .order_by(Fig.fig_name).all()
    return [{
        "id": r.id, "name": r.fig_name, "fig_code": r.fig_code,
        "silk_type_name": r.silk_type_name, "member_count": int(r.member_count),
        "formation_date": r.formation_date.isoformat() if r.formation_date else None,
    } for r in rows]


