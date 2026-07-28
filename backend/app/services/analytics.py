"""Query-building and role-scoping helpers for the Analytics drill-down module.

Every function here returns a single SQL GROUP BY query's rows — no per-row
Python loops over full tables (that anti-pattern was the reason this module
exists as a separate, carefully-built layer; see reports.py's district-comparison
history for what NOT to do at this data volume).
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.models import Farmer, Fig, FigMember, Land, Yield_, District, SericultureCircle, User, Product, Stock, ByproductEntry, SilkType, SilkTypeActivityProduct, YieldInputEntry, Activity, InputSourceType


def scope_district(user: User, district_id: Optional[str]) -> Optional[str]:
    """DISTRICT_ADMIN is pinned to their own district; STATE_ADMIN may pass any (or none, for state level)."""
    if user.role == "DISTRICT_ADMIN":
        if district_id and district_id != user.district_id:
            raise HTTPException(403, "Cannot access another district's analytics")
        return user.district_id
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


# ---- Lands ----
def _land_aggregates():
    return (
        func.count(Land.id).label("parcels"),
        func.coalesce(func.sum(Land.land_area_bigha), 0).label("bigha"),
        func.coalesce(func.sum(Land.land_area_hectare), 0).label("hectare"),
        func.sum(case((Land.gps_verified == "Verified", 1), else_=0)).label("verified"),
        func.sum(case((Land.gps_verified == "Pending", 1), else_=0)).label("pending"),
    )


def _land_row(r) -> dict:
    return {
        "id": r[0], "name": r[1], "parcels": int(r.parcels),
        "bigha": float(r.bigha or 0), "hectare": float(r.hectare or 0),
        "verified": int(r.verified or 0), "pending": int(r.pending or 0),
    }


def lands_by_district(db: Session) -> list[dict]:
    rows = db.query(Farmer.district_id, District.district_name, *_land_aggregates()) \
        .select_from(Land) \
        .join(Farmer, Farmer.id == Land.farmer_id) \
        .join(District, District.id == Farmer.district_id) \
        .group_by(Farmer.district_id, District.district_name) \
        .order_by(District.district_name).all()
    return [_land_row(r) for r in rows]


def lands_by_circle(db: Session, district_id: str) -> list[dict]:
    rows = db.query(Farmer.seri_circle_id, SericultureCircle.circle_name, *_land_aggregates()) \
        .select_from(Land) \
        .join(Farmer, Farmer.id == Land.farmer_id) \
        .join(SericultureCircle, SericultureCircle.id == Farmer.seri_circle_id) \
        .filter(Farmer.district_id == district_id) \
        .group_by(Farmer.seri_circle_id, SericultureCircle.circle_name) \
        .order_by(SericultureCircle.circle_name).all()
    return [_land_row(r) for r in rows]


# ---- Yields (production — time-bound, additive across months) ----
# Stock is a point-in-time balance and is NEVER aggregated here — see the separate
# "Stock" section below, which has no month/fiscal_year concept at all.
def _yield_aggregates():
    return (
        func.sum(Yield_.planned_yield).label("planned"),
        func.sum(Yield_.actual_yield).label("actual"),
        func.sum(Yield_.earning).label("earning"),
    )


def _yield_row(r) -> dict:
    return {
        "id": r[0], "name": r[1],
        "planned": float(r.planned or 0), "actual": float(r.actual or 0),
        "earning": float(r.earning or 0),
    }


# ---- Products (production, product-dimensioned — same shape as Yields, filtered by product_id) ----
# months=None means all-time (no filter) — the caller (analytics.py router) resolves "no
# month/fiscal_year/custom-range given" to None, matching the Dashboard tile's semantics.
def products_by_district(db: Session, product_id: str, months: Optional[list[str]]) -> list[dict]:
    q = db.query(Farmer.district_id, District.district_name, *_yield_aggregates()) \
        .select_from(Yield_) \
        .join(Farmer, Farmer.id == Yield_.farmer_id) \
        .join(District, District.id == Farmer.district_id) \
        .filter(Yield_.product_id == product_id)
    if months:
        q = q.filter(Yield_.yield_month.in_(months))
    rows = q.group_by(Farmer.district_id, District.district_name).order_by(District.district_name).all()
    return [_yield_row(r) for r in rows]


def products_by_circle(db: Session, product_id: str, months: Optional[list[str]], district_id: str) -> list[dict]:
    q = db.query(Farmer.seri_circle_id, SericultureCircle.circle_name, *_yield_aggregates()) \
        .select_from(Yield_) \
        .join(Farmer, Farmer.id == Yield_.farmer_id) \
        .join(SericultureCircle, SericultureCircle.id == Farmer.seri_circle_id) \
        .filter(Yield_.product_id == product_id, Farmer.district_id == district_id)
    if months:
        q = q.filter(Yield_.yield_month.in_(months))
    rows = q.group_by(Farmer.seri_circle_id, SericultureCircle.circle_name).order_by(SericultureCircle.circle_name).all()
    return [_yield_row(r) for r in rows]


def products_by_fig(db: Session, product_id: str, months: Optional[list[str]], seri_circle_id: str) -> list[dict]:
    q = db.query(Yield_.fig_id, Fig.fig_name, func.count(func.distinct(Yield_.farmer_id)).label("farmer_count"), *_yield_aggregates()) \
        .join(Fig, Fig.id == Yield_.fig_id) \
        .join(Farmer, Farmer.id == Yield_.farmer_id) \
        .filter(Yield_.product_id == product_id, Farmer.seri_circle_id == seri_circle_id)
    if months:
        q = q.filter(Yield_.yield_month.in_(months))
    rows = q.group_by(Yield_.fig_id, Fig.fig_name).order_by(Fig.fig_name).all()
    return [{**_yield_row(r), "farmer_count": int(r.farmer_count)} for r in rows]


def products_by_farmer(db: Session, product_id: str, months: Optional[list[str]], fig_id: str) -> list[dict]:
    q = db.query(Yield_.farmer_id, Farmer.first_name, Farmer.last_name, *_yield_aggregates()) \
        .join(Farmer, Farmer.id == Yield_.farmer_id) \
        .filter(Yield_.product_id == product_id, Yield_.fig_id == fig_id)
    if months:
        q = q.filter(Yield_.yield_month.in_(months))
    rows = q.group_by(Yield_.farmer_id, Farmer.first_name, Farmer.last_name).order_by(Farmer.first_name).all()
    return [{
        "id": r.farmer_id, "name": f"{r.first_name} {r.last_name}",
        "planned": float(r.planned or 0), "actual": float(r.actual or 0),
        "earning": float(r.earning or 0),
    } for r in rows]


# ---- Stock (point-in-time balance — no month/fiscal_year concept, ever) ----
def stock_by_district(db: Session, product_id: str) -> list[dict]:
    rows = db.query(Farmer.district_id, District.district_name,
                     func.sum(Stock.closing_balance).label("stock")) \
        .select_from(Stock) \
        .join(Farmer, Farmer.id == Stock.farmer_id) \
        .join(District, District.id == Farmer.district_id) \
        .filter(Stock.product_id == product_id) \
        .group_by(Farmer.district_id, District.district_name) \
        .order_by(District.district_name).all()
    return [{"id": r.district_id, "name": r.district_name, "stock": float(r.stock or 0)} for r in rows]


def stock_by_circle(db: Session, product_id: str, district_id: str) -> list[dict]:
    rows = db.query(Farmer.seri_circle_id, SericultureCircle.circle_name,
                     func.sum(Stock.closing_balance).label("stock")) \
        .select_from(Stock) \
        .join(Farmer, Farmer.id == Stock.farmer_id) \
        .join(SericultureCircle, SericultureCircle.id == Farmer.seri_circle_id) \
        .filter(Stock.product_id == product_id, Farmer.district_id == district_id) \
        .group_by(Farmer.seri_circle_id, SericultureCircle.circle_name) \
        .order_by(SericultureCircle.circle_name).all()
    return [{"id": r.seri_circle_id, "name": r.circle_name, "stock": float(r.stock or 0)} for r in rows]


def stock_by_fig(db: Session, product_id: str, seri_circle_id: str) -> list[dict]:
    rows = db.query(Stock.fig_id, Fig.fig_name, func.count(func.distinct(Stock.farmer_id)).label("farmer_count"),
                     func.sum(Stock.closing_balance).label("stock")) \
        .select_from(Stock) \
        .join(Fig, Fig.id == Stock.fig_id) \
        .join(Farmer, Farmer.id == Stock.farmer_id) \
        .filter(Stock.product_id == product_id, Farmer.seri_circle_id == seri_circle_id) \
        .group_by(Stock.fig_id, Fig.fig_name) \
        .order_by(Fig.fig_name).all()
    return [{"id": r.fig_id, "name": r.fig_name, "farmer_count": int(r.farmer_count), "stock": float(r.stock or 0)} for r in rows]


def stock_by_farmer(db: Session, product_id: str, fig_id: str) -> list[dict]:
    rows = db.query(Stock.farmer_id, Farmer.first_name, Farmer.last_name, Stock.closing_balance) \
        .select_from(Stock) \
        .join(Farmer, Farmer.id == Stock.farmer_id) \
        .filter(Stock.product_id == product_id, Stock.fig_id == fig_id) \
        .order_by(Farmer.first_name).all()
    return [{
        "id": r.farmer_id, "name": f"{r.first_name} {r.last_name}",
        "stock": float(r.closing_balance or 0),
    } for r in rows]


# ---- DFL yield-efficiency ----
def dfl_efficiency_pairs(db: Session) -> list[dict]:
    """(silk_type_id, silk_type_name, cocoon Product, dfl Product) pairs derived from Product
    naming convention "<SilkType> Cocoon" / "<SilkType> DFL" (excludes "Cut Cocoon").
    FRAGILE to Product renames via the Master CRUD — flagged as a follow-up to add a
    nullable self-referencing Product.dfl_pair_product_id FK once this proves out."""
    silk_types = db.query(SilkType).filter(SilkType.is_active).all()
    by_name = {p.product_name: p for p in db.query(Product).filter(Product.is_active).all()}
    pairs = []
    for st in silk_types:
        cocoon = by_name.get(f"{st.silk_type_name} Cocoon")
        dfl = by_name.get(f"{st.silk_type_name} DFL")
        if cocoon and dfl:
            pairs.append({"silk_type_id": st.id, "silk_type_name": st.silk_type_name, "cocoon": cocoon, "dfl": dfl})
    return pairs


def dfl_efficiency_rows(db: Session, months: Optional[list[str]], district_id: Optional[str]) -> list[dict]:
    pairs = dfl_efficiency_pairs(db)
    out = []
    for pair in pairs:
        ids = [pair["cocoon"].id, pair["dfl"].id]
        q = db.query(Yield_.product_id, func.sum(Yield_.actual_yield).label("total")).filter(Yield_.product_id.in_(ids))
        if months:
            q = q.filter(Yield_.yield_month.in_(months))
        if district_id:
            fig_ids = [f.id for f in db.query(Fig.id).filter(Fig.district_id == district_id).all()]
            q = q.filter(Yield_.fig_id.in_(fig_ids or [""]))
        totals = {r.product_id: float(r.total or 0) for r in q.group_by(Yield_.product_id).all()}
        cocoon_total, dfl_total = totals.get(pair["cocoon"].id, 0.0), totals.get(pair["dfl"].id, 0.0)
        out.append({
            "silk_type_id": pair["silk_type_id"], "silk_type_name": pair["silk_type_name"],
            "cocoon_product_id": pair["cocoon"].id, "dfl_product_id": pair["dfl"].id,
            "cocoon_actual": cocoon_total, "dfl_actual": dfl_total,
            "kg_per_dfl": round(cocoon_total / dfl_total, 3) if dfl_total else None,
        })
    return out


# ---- Byproduct-yield-ratio ----
def byproduct_ratio_by_district(db: Session, months: list[str], district_id: Optional[str]) -> list[dict]:
    q = db.query(
        Farmer.district_id, District.district_name,
        ByproductEntry.product_id, Product.product_name, Product.unit_of_measure,
        func.sum(ByproductEntry.quantity).label("byproduct_qty"),
        func.sum(Yield_.actual_yield).label("parent_actual"),
        func.count(func.distinct(ByproductEntry.parent_yield_id)).label("parent_count"),
    ).select_from(ByproductEntry) \
     .join(Yield_, Yield_.id == ByproductEntry.parent_yield_id) \
     .join(Farmer, Farmer.id == ByproductEntry.farmer_id) \
     .join(District, District.id == Farmer.district_id) \
     .join(Product, Product.id == ByproductEntry.product_id)
    if months:
        q = q.filter(ByproductEntry.yield_month.in_(months))
    if district_id:
        q = q.filter(Farmer.district_id == district_id)
    rows = q.group_by(Farmer.district_id, District.district_name, ByproductEntry.product_id,
                       Product.product_name, Product.unit_of_measure).all()
    return [{
        "district_id": r.district_id, "district_name": r.district_name,
        "product_id": r.product_id, "product_name": r.product_name, "unit_of_measure": r.unit_of_measure,
        "byproduct_qty": float(r.byproduct_qty or 0), "parent_actual_yield": float(r.parent_actual or 0),
        "parent_count": int(r.parent_count),
        "ratio_pct": round((r.byproduct_qty / r.parent_actual) * 100, 2) if r.parent_actual else None,
    } for r in rows]


# ---- Inputs (consumption — time-bound/additive across months, same shape as Products) ----
# Source types are State-Admin-managed (InputSourceType), not a fixed enum, so the breakdown
# is built dynamically from whatever source names actually appear in the data.
def _group_input_rows(rows) -> list[dict]:
    """rows: iterable of (dim_id, dim_name, source_name, qty) — aggregates into one entry
    per dim_id with a dynamic by_source breakdown."""
    out: dict[str, dict] = {}
    for dim_id, dim_name, source_name, qty in rows:
        entry = out.setdefault(dim_id, {"id": dim_id, "name": dim_name, "total_qty": 0.0, "by_source": {}})
        q = float(qty or 0)
        entry["total_qty"] += q
        entry["by_source"][source_name] = entry["by_source"].get(source_name, 0.0) + q
    result = list(out.values())
    result.sort(key=lambda r: r["name"] or "")
    return result


def inputs_by_district(db: Session, product_id: str, months: Optional[list[str]]) -> list[dict]:
    q = db.query(Farmer.district_id, District.district_name, InputSourceType.source_name,
                 func.sum(YieldInputEntry.quantity).label("qty")) \
        .select_from(YieldInputEntry) \
        .join(Farmer, Farmer.id == YieldInputEntry.farmer_id) \
        .join(District, District.id == Farmer.district_id) \
        .join(InputSourceType, InputSourceType.id == YieldInputEntry.source_type_id) \
        .filter(YieldInputEntry.product_id == product_id)
    if months:
        q = q.filter(YieldInputEntry.yield_month.in_(months))
    rows = q.group_by(Farmer.district_id, District.district_name, InputSourceType.source_name).all()
    return _group_input_rows(rows)


def inputs_by_circle(db: Session, product_id: str, months: Optional[list[str]], district_id: str) -> list[dict]:
    q = db.query(Farmer.seri_circle_id, SericultureCircle.circle_name, InputSourceType.source_name,
                 func.sum(YieldInputEntry.quantity).label("qty")) \
        .select_from(YieldInputEntry) \
        .join(Farmer, Farmer.id == YieldInputEntry.farmer_id) \
        .join(SericultureCircle, SericultureCircle.id == Farmer.seri_circle_id) \
        .join(InputSourceType, InputSourceType.id == YieldInputEntry.source_type_id) \
        .filter(YieldInputEntry.product_id == product_id, Farmer.district_id == district_id)
    if months:
        q = q.filter(YieldInputEntry.yield_month.in_(months))
    rows = q.group_by(Farmer.seri_circle_id, SericultureCircle.circle_name, InputSourceType.source_name).all()
    return _group_input_rows(rows)


def inputs_by_fig(db: Session, product_id: str, months: Optional[list[str]], seri_circle_id: str) -> list[dict]:
    base_filter = [YieldInputEntry.product_id == product_id, Farmer.seri_circle_id == seri_circle_id]
    if months:
        base_filter.append(YieldInputEntry.yield_month.in_(months))
    farmer_counts = dict(db.query(YieldInputEntry.fig_id, func.count(func.distinct(YieldInputEntry.farmer_id)))
        .join(Farmer, Farmer.id == YieldInputEntry.farmer_id)
        .filter(*base_filter).group_by(YieldInputEntry.fig_id).all())
    rows = db.query(YieldInputEntry.fig_id, Fig.fig_name, InputSourceType.source_name,
                     func.sum(YieldInputEntry.quantity).label("qty")) \
        .join(Fig, Fig.id == YieldInputEntry.fig_id) \
        .join(Farmer, Farmer.id == YieldInputEntry.farmer_id) \
        .join(InputSourceType, InputSourceType.id == YieldInputEntry.source_type_id) \
        .filter(*base_filter) \
        .group_by(YieldInputEntry.fig_id, Fig.fig_name, InputSourceType.source_name).all()
    out = _group_input_rows(rows)
    for entry in out:
        entry["farmer_count"] = int(farmer_counts.get(entry["id"], 0))
    return out


def inputs_by_farmer(db: Session, product_id: str, months: Optional[list[str]], fig_id: str) -> list[dict]:
    q = db.query(YieldInputEntry.farmer_id, Farmer.first_name, Farmer.last_name, InputSourceType.source_name,
                 func.sum(YieldInputEntry.quantity).label("qty")) \
        .join(Farmer, Farmer.id == YieldInputEntry.farmer_id) \
        .join(InputSourceType, InputSourceType.id == YieldInputEntry.source_type_id) \
        .filter(YieldInputEntry.product_id == product_id, YieldInputEntry.fig_id == fig_id)
    if months:
        q = q.filter(YieldInputEntry.yield_month.in_(months))
    rows = q.group_by(YieldInputEntry.farmer_id, Farmer.first_name, Farmer.last_name, InputSourceType.source_name).all()
    # _group_input_rows expects (dim_id, dim_name, source_name, qty) — combine first+last here.
    combined = [(farmer_id, f"{first} {last}", source_name, qty) for farmer_id, first, last, source_name, qty in rows]
    return _group_input_rows(combined)


# ---- Activity efficiency (generalized input/output ratio for any activity, per district) ----
def activity_efficiency_rows(db: Session, activity_id: str, months: Optional[list[str]], district_id: Optional[str] = None) -> list[dict]:
    """output_qty / input_qty per district for a given Activity — generalizes the
    dfl_efficiency_rows pattern to any activity carrying both INPUT- and OUTPUT-role
    STAP rows, not just the hardcoded Muga Cocoon -> DFL pair."""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(404, "Activity not found")

    output_q = db.query(Farmer.district_id, District.district_name, func.sum(Yield_.actual_yield).label("qty")) \
        .select_from(Yield_) \
        .join(Farmer, Farmer.id == Yield_.farmer_id) \
        .join(District, District.id == Farmer.district_id) \
        .filter(Yield_.activity_id == activity_id)
    input_q = db.query(Farmer.district_id, func.sum(YieldInputEntry.quantity).label("qty")) \
        .select_from(YieldInputEntry) \
        .join(Yield_, Yield_.id == YieldInputEntry.parent_yield_id) \
        .join(Farmer, Farmer.id == YieldInputEntry.farmer_id) \
        .filter(Yield_.activity_id == activity_id)
    if months:
        output_q = output_q.filter(Yield_.yield_month.in_(months))
        input_q = input_q.filter(YieldInputEntry.yield_month.in_(months))
    if district_id:
        output_q = output_q.filter(Farmer.district_id == district_id)
        input_q = input_q.filter(Farmer.district_id == district_id)

    outputs = {r.district_id: (r.district_name, float(r.qty or 0))
               for r in output_q.group_by(Farmer.district_id, District.district_name).all()}
    inputs = {r.district_id: float(r.qty or 0) for r in input_q.group_by(Farmer.district_id).all()}

    out = []
    for d_id in set(outputs) | set(inputs):
        name = outputs[d_id][0] if d_id in outputs else db.query(District.district_name).filter(District.id == d_id).scalar()
        output_qty = outputs.get(d_id, (None, 0.0))[1]
        input_qty = inputs.get(d_id, 0.0)
        out.append({
            "district_id": d_id, "district_name": name,
            "output_qty": round(output_qty, 3), "input_qty": round(input_qty, 3),
            "efficiency_ratio": round(output_qty / input_qty, 3) if input_qty else None,
        })
    out.sort(key=lambda r: r["district_name"] or "")
    return out
