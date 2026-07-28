"""Analytics: drill-down reports for Farmers, FIGs, Lands, Yields/Stock."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.services.fiscal import period_months, month_range
from app.services.analytics import (
    scope_district, scope_fig,
    farmers_by_district, farmers_by_circle,
    figs_by_district, figs_by_circle, figs_in_circle,
    lands_by_district, lands_by_circle,
    products_by_district, products_by_circle, products_by_fig, products_by_farmer,
    stock_by_district, stock_by_circle, stock_by_fig, stock_by_farmer,
    inputs_by_district, inputs_by_circle, inputs_by_fig, inputs_by_farmer,
    dfl_efficiency_rows, byproduct_ratio_by_district, activity_efficiency_rows,
)
from app.models import User, SericultureCircle, Fig, Product, Activity

router = APIRouter(prefix="/reports/analytics", tags=["analytics"])


def _require_level(level: str, allowed: set[str]):
    if level not in allowed:
        raise HTTPException(400, f"level must be one of: {', '.join(sorted(allowed))}")


def _levels_for(user: User, base: set[str]) -> set[str]:
    if user.role == "DISTRICT_ADMIN":
        return base - {"district"}
    return base


def _validate_circle_in_district(db: Session, seri_circle_id: str, district_id: str):
    if not db.query(SericultureCircle).filter(SericultureCircle.id == seri_circle_id, SericultureCircle.district_id == district_id).first():
        raise HTTPException(403, "Sericulture Circle does not belong to this district")


def _validate_fig_in_district(db: Session, fig_id: str, district_id: str):
    if not db.query(Fig).filter(Fig.id == fig_id, Fig.district_id == district_id).first():
        raise HTTPException(403, "FIG does not belong to this district")


def _resolve_months(month: Optional[str], fiscal_year: Optional[str],
                     from_month: Optional[str], to_month: Optional[str]) -> Optional[list[str]]:
    """None means all-time (no filter) — matches the Dashboard tile's `_product_summary_rows`
    semantics exactly. Only falls back to a custom range when neither month nor fiscal_year
    was given; a custom range combined with either of those is rejected as ambiguous."""
    months = period_months(month, fiscal_year)
    if months is not None:
        if from_month or to_month:
            raise HTTPException(400, "Provide either month/fiscal_year or from_month/to_month, not both")
        return months
    if from_month or to_month:
        if not (from_month and to_month):
            raise HTTPException(400, "from_month and to_month must both be provided")
        return month_range(from_month, to_month)
    return None


@router.get("/farmers")
def analytics_farmers(level: str, district_id: Optional[str] = None,
                      user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                      db: Session = Depends(get_session)):
    _require_level(level, _levels_for(user, {"district", "sericulture_circle"}))
    if level == "district":
        return {"level": "district", "rows": farmers_by_district(db)}
    resolved = scope_district(user, district_id)
    if not resolved:
        raise HTTPException(400, "district_id is required at sericulture_circle level")
    return {"level": "sericulture_circle", "rows": farmers_by_circle(db, resolved)}


@router.get("/figs")
def analytics_figs(level: str, district_id: Optional[str] = None, seri_circle_id: Optional[str] = None,
                   user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                   db: Session = Depends(get_session)):
    _require_level(level, _levels_for(user, {"district", "sericulture_circle", "fig"}))
    if level == "district":
        return {"level": "district", "rows": figs_by_district(db)}
    if level == "sericulture_circle":
        resolved = scope_district(user, district_id)
        if not resolved:
            raise HTTPException(400, "district_id is required at sericulture_circle level")
        return {"level": "sericulture_circle", "rows": figs_by_circle(db, resolved)}
    # fig level
    if not seri_circle_id:
        raise HTTPException(400, "seri_circle_id is required at fig level")
    if user.role == "DISTRICT_ADMIN":
        _validate_circle_in_district(db, seri_circle_id, user.district_id)
    return {"level": "fig", "rows": figs_in_circle(db, seri_circle_id)}


@router.get("/lands")
def analytics_lands(level: str, district_id: Optional[str] = None,
                    user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                    db: Session = Depends(get_session)):
    _require_level(level, _levels_for(user, {"district", "sericulture_circle"}))
    if level == "district":
        return {"level": "district", "rows": lands_by_district(db)}
    resolved = scope_district(user, district_id)
    if not resolved:
        raise HTTPException(400, "district_id is required at sericulture_circle level")
    return {"level": "sericulture_circle", "rows": lands_by_circle(db, resolved)}


_YIELD_LEVELS = {
    "STATE_ADMIN": {"district", "sericulture_circle", "fig", "farmer"},
    "DISTRICT_ADMIN": {"sericulture_circle", "fig", "farmer"},
    "FIG_PRESIDENT": {"farmer"},
}


@router.get("/products")
def analytics_products(level: str, product_id: str, month: Optional[str] = None, fiscal_year: Optional[str] = None,
                       from_month: Optional[str] = None, to_month: Optional[str] = None,
                       district_id: Optional[str] = None, seri_circle_id: Optional[str] = None, fig_id: Optional[str] = None,
                       user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    _require_level(level, _YIELD_LEVELS.get(user.role, set()))
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    months = _resolve_months(month, fiscal_year, from_month, to_month)

    if level == "district":
        rows = products_by_district(db, product_id, months)
    elif level == "sericulture_circle":
        resolved_district = scope_district(user, district_id)
        if not resolved_district:
            raise HTTPException(400, "district_id is required at sericulture_circle level")
        rows = products_by_circle(db, product_id, months, resolved_district)
    elif level == "fig":
        if not seri_circle_id:
            raise HTTPException(400, "seri_circle_id is required at fig level")
        if user.role == "DISTRICT_ADMIN":
            _validate_circle_in_district(db, seri_circle_id, user.district_id)
        rows = products_by_fig(db, product_id, months, seri_circle_id)
    else:  # farmer
        resolved_fig = scope_fig(user, fig_id)
        if user.role == "DISTRICT_ADMIN":
            _validate_fig_in_district(db, resolved_fig, user.district_id)
        rows = products_by_farmer(db, product_id, months, resolved_fig)

    return {
        "level": level, "months": months,
        "product": {"id": product.id, "product_name": product.product_name, "unit_of_measure": product.unit_of_measure},
        "rows": rows,
    }


@router.get("/stock")
def analytics_stock(level: str, product_id: str,
                    district_id: Optional[str] = None, seri_circle_id: Optional[str] = None, fig_id: Optional[str] = None,
                    user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """Current stock — a point-in-time balance, never a period. No month/fiscal_year param
    exists on this endpoint at all, unlike every other analytics endpoint."""
    _require_level(level, _YIELD_LEVELS.get(user.role, set()))
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")

    if level == "district":
        rows = stock_by_district(db, product_id)
    elif level == "sericulture_circle":
        resolved_district = scope_district(user, district_id)
        if not resolved_district:
            raise HTTPException(400, "district_id is required at sericulture_circle level")
        rows = stock_by_circle(db, product_id, resolved_district)
    elif level == "fig":
        if not seri_circle_id:
            raise HTTPException(400, "seri_circle_id is required at fig level")
        if user.role == "DISTRICT_ADMIN":
            _validate_circle_in_district(db, seri_circle_id, user.district_id)
        rows = stock_by_fig(db, product_id, seri_circle_id)
    else:  # farmer
        resolved_fig = scope_fig(user, fig_id)
        if user.role == "DISTRICT_ADMIN":
            _validate_fig_in_district(db, resolved_fig, user.district_id)
        rows = stock_by_farmer(db, product_id, resolved_fig)

    return {
        "level": level,
        "product": {"id": product.id, "product_name": product.product_name, "unit_of_measure": product.unit_of_measure},
        "rows": rows,
    }


@router.get("/inputs")
def analytics_inputs(level: str, product_id: str, month: Optional[str] = None, fiscal_year: Optional[str] = None,
                     from_month: Optional[str] = None, to_month: Optional[str] = None,
                     district_id: Optional[str] = None, seri_circle_id: Optional[str] = None, fig_id: Optional[str] = None,
                     user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    _require_level(level, _YIELD_LEVELS.get(user.role, set()))
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    months = _resolve_months(month, fiscal_year, from_month, to_month)

    if level == "district":
        rows = inputs_by_district(db, product_id, months)
    elif level == "sericulture_circle":
        resolved_district = scope_district(user, district_id)
        if not resolved_district:
            raise HTTPException(400, "district_id is required at sericulture_circle level")
        rows = inputs_by_circle(db, product_id, months, resolved_district)
    elif level == "fig":
        if not seri_circle_id:
            raise HTTPException(400, "seri_circle_id is required at fig level")
        if user.role == "DISTRICT_ADMIN":
            _validate_circle_in_district(db, seri_circle_id, user.district_id)
        rows = inputs_by_fig(db, product_id, months, seri_circle_id)
    else:  # farmer
        resolved_fig = scope_fig(user, fig_id)
        if user.role == "DISTRICT_ADMIN":
            _validate_fig_in_district(db, resolved_fig, user.district_id)
        rows = inputs_by_farmer(db, product_id, months, resolved_fig)

    return {
        "level": level, "months": months,
        "product": {"id": product.id, "product_name": product.product_name, "unit_of_measure": product.unit_of_measure},
        "rows": rows,
    }


@router.get("/dfl-efficiency")
def dfl_efficiency(month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                   user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")), db: Session = Depends(get_session)):
    months = period_months(month, fiscal_year)
    resolved_district = scope_district(user, district_id)
    return {"months": months, "district_id": resolved_district, "rows": dfl_efficiency_rows(db, months, resolved_district)}


@router.get("/byproduct-ratio")
def byproduct_ratio(month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                    user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")), db: Session = Depends(get_session)):
    months = period_months(month, fiscal_year)
    resolved_district = scope_district(user, district_id)
    return {"months": months, "rows": byproduct_ratio_by_district(db, months, resolved_district)}


@router.get("/activity-efficiency")
def activity_efficiency(activity_id: str, month: Optional[str] = None, fiscal_year: Optional[str] = None, district_id: Optional[str] = None,
                        user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")), db: Session = Depends(get_session)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(404, "Activity not found")
    months = period_months(month, fiscal_year)
    resolved_district = scope_district(user, district_id)
    return {
        "months": months,
        "activity": {"id": activity.id, "activity_name": activity.activity_name},
        "rows": activity_efficiency_rows(db, activity_id, months, resolved_district),
    }
