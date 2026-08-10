"""Analytics: drill-down reports for Farmers, FIGs, Lands, Yields/Stock."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import require_roles
from app.services.fiscal import period_months, month_range
from app.services.analytics import (
    scope_district, scope_fig,
    farmers_by_district, farmers_by_circle,
    figs_by_district, figs_by_circle, figs_in_circle,
)
from app.services import yield_matrix
from app.models import User, SericultureCircle, Fig

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


_MATRIX_LEVELS = {
    "STATE_ADMIN": {"state", "district", "sericulture_circle", "fig", "farmer", "meeting"},
    "DISTRICT_ADMIN": {"district", "sericulture_circle", "fig", "farmer", "meeting"},  # "district" allowed for DA here too — trivially 1 row; "state" is State-Admin-only
}
_MATRIX_PAGE_SIZES = (25, 50, 100)


@router.get("/yield-matrix")
def yield_matrix_endpoint(
    level: str, month: Optional[str] = None, from_month: Optional[str] = None, to_month: Optional[str] = None,
    product_ids: Optional[str] = None, page: int = 1, page_size: int = 25,
    user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
    db: Session = Depends(get_session),
):
    """Multi-granularity, multi-product Yield View matrix — the read-only District/State Admin
    page. Unlike /products, /stock, /inputs above, levels here are flat and self-contained
    (no parent scope id required for circle/fig/farmer) — State Admin sees every entity
    statewide at the chosen granularity, District Admin sees every entity in their own
    district, both paginated. See services/yield_matrix.py for the aggregation logic."""
    _require_level(level, _MATRIX_LEVELS.get(user.role, set()))
    if page_size not in _MATRIX_PAGE_SIZES:
        raise HTTPException(400, f"page_size must be one of {', '.join(str(n) for n in _MATRIX_PAGE_SIZES)}")
    months = _resolve_months(month, None, from_month, to_month)
    if months is None:
        months = [datetime.now(timezone.utc).strftime("%Y-%m")]
    district_scope = scope_district(user, None)  # DA -> own district always; SA -> unscoped (statewide)
    requested = [p for p in product_ids.split(",") if p] if product_ids else None

    entities, total = yield_matrix.entities_page(db, level, district_scope, page, page_size)
    avail = yield_matrix.available_products(db, level, district_scope, months)
    input_ids, output_ids, stock_ids = yield_matrix.resolve_column_ids(avail, requested)
    input_sources = yield_matrix.available_input_sources(db, level, district_scope, months, input_ids)
    matrix = yield_matrix.build_matrix(db, level, entities, months, input_ids, output_ids, stock_ids, input_sources)

    return {**matrix, "page": page, "page_size": page_size, "total": total, "available_products": avail}
