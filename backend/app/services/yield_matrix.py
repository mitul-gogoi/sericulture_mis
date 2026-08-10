"""Multi-granularity, multi-product Yield-View matrix aggregation, for the redesigned
District/State Admin "Yield View" (see routers/analytics.py's /yield-matrix endpoint and
routers/reports.py's export dispatcher).

Deliberately NOT built on the existing per-product products_by_x/stock_by_x/inputs_by_x
functions in this same package's analytics.py — those require a parent scope id at
circle/fig/farmer level (e.g. products_by_circle needs a district_id). This module's levels
are flat and self-contained by design: State Admin sees every circle/FIG/farmer statewide
(paginated), District Admin sees every circle/FIG/farmer within their own district (also
paginated) — no drill-down/pre-selection step.

Every transactional table (Yield_, ByproductEntry, YieldInputEntry, Stock) already has its
own fig_id column directly, and Fig itself carries both district_id and seri_circle_id
directly — so district/circle-level grouping needs at most one join (through Fig), and
fig/farmer-level grouping needs none at all.
"""
from typing import Optional
from sqlalchemy import func, literal, literal_column
from sqlalchemy.orm import Session
from app.models import (
    Farmer, Fig, FigMember, District, SericultureCircle, Yield_, ByproductEntry,
    YieldInputEntry, Stock, Product, ConversionStandard, InputSourceType, LossReason,
    Meeting, Attendance,
)

LEVELS = ("state", "district", "sericulture_circle", "fig", "farmer", "meeting")

# Delimiter used to build the "meeting" level's composite (meeting_id, farmer_id) entity id —
# both parts are UUIDs, so this can never collide with either half.
_MEETING_KEY_SEP = "::"


def _district_name_map(db: Session, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {d.id: d.district_name for d in db.query(District).filter(District.id.in_(ids)).all()}


def _circle_name_map(db: Session, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {c.id: c.circle_name for c in db.query(SericultureCircle).filter(SericultureCircle.id.in_(ids)).all()}


def _fig_by_farmer(db: Session, farmer_ids: list[str]) -> dict[str, Fig]:
    """A farmer's *current* FIG, resolved the same way every other query in this codebase
    resolves "current membership" — FigMember.is_active alone (exit_date is set alongside it
    on removal but is never itself queried anywhere). A farmer with no active membership is
    simply absent from the returned dict."""
    if not farmer_ids:
        return {}
    rows = (
        db.query(FigMember.farmer_id, Fig)
        .join(Fig, Fig.id == FigMember.fig_id)
        .filter(FigMember.farmer_id.in_(farmer_ids), FigMember.is_active)
        .all()
    )
    return {farmer_id: fig for farmer_id, fig in rows}


def entities_page(db: Session, level: str, district_id_scope: Optional[str],
                   page: int, page_size: int) -> tuple[list[dict], int]:
    """Row universe resolved directly from the master tables (not from who-has-submitted),
    so every entity in scope appears even with zero submissions — a District Admin should be
    able to spot who *didn't* submit, not just see who did.

    For sericulture_circle/fig/farmer levels, each returned dict also carries breadcrumb
    context fields (district_name, seri_circle_name, and — farmer level only — fig_name) so
    the Yield View can show where each row sits in the hierarchy above it. These are resolved
    only for the current page's entities, matching this module's existing efficiency pattern
    of never querying more than the page actually needs."""
    if level == "state":
        rows = [{"id": "state", "name": "Assam"}]
        page_rows = rows[(page - 1) * page_size: (page - 1) * page_size + page_size]
        return page_rows, len(rows)
    if level == "district":
        q = db.query(District).filter(District.is_active)
        if district_id_scope:
            q = q.filter(District.id == district_id_scope)
        q = q.order_by(District.district_name)
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return [{"id": r.id, "name": r.district_name} for r in rows], total
    if level == "sericulture_circle":
        q = db.query(SericultureCircle).filter(SericultureCircle.is_active)
        if district_id_scope:
            q = q.filter(SericultureCircle.district_id == district_id_scope)
        q = q.order_by(SericultureCircle.circle_name)
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        districts = _district_name_map(db, {r.district_id for r in rows})
        return [{"id": r.id, "name": r.circle_name,
                 "district_name": districts.get(r.district_id)} for r in rows], total
    if level == "fig":
        q = db.query(Fig).filter(Fig.is_active)
        if district_id_scope:
            q = q.filter(Fig.district_id == district_id_scope)
        q = q.order_by(Fig.fig_name)
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        districts = _district_name_map(db, {r.district_id for r in rows})
        circles = _circle_name_map(db, {r.seri_circle_id for r in rows})
        return [{"id": r.id, "name": r.fig_name, "fig_code": r.fig_code,
                 "district_name": districts.get(r.district_id),
                 "seri_circle_name": circles.get(r.seri_circle_id)} for r in rows], total
    if level == "meeting":
        # Row universe = every attendee (present or not) of every meeting in scope, sourced from
        # Attendance rather than Farmer/Fig — a "meeting" only exists once a FIG has actually
        # submitted, so unlike every other level there's no master-data roster to fall back to.
        # Present-or-not is kept (not filtered to is_present) so an admin can also see who was
        # absent, matching this module's "show the whole roster, zero-fill missing data" idea.
        q = (
            db.query(Attendance, Meeting, Fig, Farmer)
            .join(Meeting, Meeting.id == Attendance.meeting_id)
            .join(Fig, Fig.id == Attendance.fig_id)
            .join(Farmer, Farmer.id == Attendance.farmer_id)
        )
        if district_id_scope:
            q = q.filter(Fig.district_id == district_id_scope)
        q = q.order_by(Meeting.meeting_month.desc(), Fig.fig_name, Farmer.first_name, Farmer.last_name)
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        districts = _district_name_map(db, {fig.district_id for _, _, fig, _ in rows})
        circles = _circle_name_map(db, {fig.seri_circle_id for _, _, fig, _ in rows})
        out = []
        for att, meeting, fig, farmer in rows:
            out.append({
                "id": f"{meeting.id}{_MEETING_KEY_SEP}{farmer.id}",
                "name": f"{farmer.first_name} {farmer.last_name}", "farmer_code": farmer.farmer_code,
                "meeting_id": meeting.id, "meeting_month": meeting.meeting_month,
                "district_name": districts.get(fig.district_id), "seri_circle_name": circles.get(fig.seri_circle_id),
                "fig_name": fig.fig_name, "fig_code": fig.fig_code,
                # Excel-only "raw record" extras — no equivalent at any aggregate level.
                "meeting_title": meeting.meeting_title,
                "meeting_date": meeting.meeting_date.isoformat() if meeting.meeting_date else None,
                "meeting_venue": meeting.meeting_venue, "farmer_mobile": farmer.mobile_no,
                "is_present": att.is_present,
            })
        return out, total
    # farmer
    q = db.query(Farmer).filter(Farmer.is_active)
    if district_id_scope:
        q = q.filter(Farmer.district_id == district_id_scope)
    q = q.order_by(Farmer.first_name, Farmer.last_name)
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    districts = _district_name_map(db, {r.district_id for r in rows})
    circles = _circle_name_map(db, {r.seri_circle_id for r in rows})
    figs_by_farmer = _fig_by_farmer(db, [r.id for r in rows])
    return [{"id": r.id, "name": f"{r.first_name} {r.last_name}", "farmer_code": r.farmer_code,
             "district_name": districts.get(r.district_id),
             "seri_circle_name": circles.get(r.seri_circle_id),
             "fig_name": figs_by_farmer.get(r.id).fig_name if r.id in figs_by_farmer else None,
             "fig_code": figs_by_farmer.get(r.id).fig_code if r.id in figs_by_farmer else None} for r in rows], total


def entities_all_ids(db: Session, level: str, district_id_scope: Optional[str]) -> list[str]:
    """Unpaginated id list — used by the export path and by available_products()."""
    rows, _ = entities_page(db, level, district_id_scope, page=1, page_size=1_000_000)
    return [r["id"] for r in rows]


def _group_and_join(level: str, table):
    """Returns (group_by_column, join_tuple_or_None). fig/farmer levels group on the table's
    own column with no join (every transactional table already has fig_id/farmer_id).
    district/sericulture_circle levels group on the table's own denormalized district_id/
    seri_circle_id column (also no join needed) — these are copied from the owning farmer at
    write time (see routers/meetings.py's _apply_yield_entries), specifically so a solo
    (non-FIG) farmer's rows — which always have fig_id=None — still aggregate correctly at
    district/circle/state level instead of silently vanishing behind a Fig join. "state"
    collapses every row into one group via a constant expression —
    literal("state").in_(entity_ids) is always-true and GROUP BY literal("state") naturally
    folds everything into a single row, so none of the calling functions below need any
    special-casing for this level.

    "meeting" groups on a composite (meeting_id, farmer_id) key, built the same way for every
    table via func.concat so callers keep treating group_col as an opaque column — but unlike
    every other level, the join target differs *per table*: Yield_ already has meeting_id
    directly (no join); ByproductEntry/YieldInputEntry only have parent_yield_id, so they join
    to Yield_ first to reach it. Stock has no path to meeting_id at all (it's a running balance,
    not a submission-scoped record) — callers must never call this for Stock at this level;
    matrix_stock() bypasses it entirely for `level == "meeting"` instead."""
    if level == "state":
        return literal("state"), None
    if level == "meeting":
        if table is Yield_:
            return func.concat(Yield_.meeting_id, literal_column("'::'"), Yield_.farmer_id), None
        if table is Stock:
            raise ValueError("Stock has no meeting-level grouping — see matrix_stock's bypass")
        return func.concat(Yield_.meeting_id, literal_column("'::'"), Yield_.farmer_id), \
            (Yield_, Yield_.id == table.parent_yield_id)
    if level == "farmer":
        return table.farmer_id, None
    if level == "fig":
        return table.fig_id, None
    if level == "sericulture_circle":
        return table.seri_circle_id, None
    return table.district_id, None  # district


def matrix_input(db: Session, level: str, entity_ids: list[str], months: Optional[list[str]],
                  product_ids: Optional[list[str]]) -> dict[str, dict[str, dict]]:
    """Shape: {entity_id: {product_id: {"total": float, "by_source": {source_name: float}}}}.
    Still a single SQL GROUP BY (source_name just joins in as one more grouping column,
    alongside the existing group_col/product_id) — mirrors analytics.py's _group_input_rows
    aggregation shape, just keyed one level deeper (per product, not just per entity)."""
    group_col, join = _group_and_join(level, YieldInputEntry)
    q = db.query(group_col, YieldInputEntry.product_id, InputSourceType.source_name,
                 func.sum(YieldInputEntry.quantity).label("qty")) \
        .select_from(YieldInputEntry) \
        .join(InputSourceType, InputSourceType.id == YieldInputEntry.source_type_id)
    if join:
        q = q.join(*join)
    q = q.filter(group_col.in_(entity_ids or [""]))
    if months:
        q = q.filter(YieldInputEntry.yield_month.in_(months))
    if product_ids:
        q = q.filter(YieldInputEntry.product_id.in_(product_ids))
    out: dict[str, dict[str, dict]] = {}
    for entity_id, product_id, source_name, qty in q.group_by(
            group_col, YieldInputEntry.product_id, InputSourceType.source_name).all():
        cell = out.setdefault(entity_id, {}).setdefault(product_id, {"total": 0.0, "by_source": {}})
        qty = float(qty or 0)
        cell["total"] += qty
        cell["by_source"][source_name] = cell["by_source"].get(source_name, 0.0) + qty
    return out


def _new_output_cell() -> dict:
    return {"planned": 0.0, "actual": 0.0, "next_month_plan": 0.0, "sold_quantity": 0.0,
            "earning": 0.0, "loss_reason_ids": set(), "stock_balance": 0.0}


def matrix_output(db: Session, level: str, entity_ids: list[str], months: Optional[list[str]],
                   product_ids: Optional[list[str]]) -> dict[str, dict[str, dict]]:
    """Yield_ (primary output) + ByproductEntry merged per product — matches services/stock.py's
    own convention of treating both as one combined "produced" concept per product.
    Shape: {entity_id: {product_id: {"planned", "actual", "next_month_plan", "sold_quantity",
    "earning", "loss_reason_ids": set(), "stock_balance"}}}.

    Unlike matrix_input/matrix_stock, this fetches raw per-record rows and accumulates in
    Python rather than a SQL GROUP BY — the only way to track a running sum *and* the distinct
    set of loss_reason_ids seen per (entity_id, product_id) at the same time (Loss Reason is
    categorical, not additive). At this app's data scale this is a non-issue performance-wise —
    a deliberate, scoped exception to "aggregate in SQL," not a new general pattern.

    `stock_balance` is captured (assigned, never summed) from each record's own historical
    Yield_/ByproductEntry.stock_balance column — meaningless at every aggregate level (hence
    never read back out there; matrix_stock()'s live Stock-table query is used instead) but the
    *correct* value at the "meeting" level, where each (entity, product) cell is guaranteed to
    come from at most one record (see the UniqueConstraints on both tables) — see build_matrix()."""
    out: dict[str, dict[str, dict]] = {}

    gy, jy = _group_and_join(level, Yield_)
    qy = db.query(gy, Yield_.product_id, Yield_.planned_yield, Yield_.actual_yield,
                  Yield_.next_month_plan, Yield_.sold_quantity, Yield_.earning,
                  Yield_.loss_reason_id, Yield_.stock_balance).select_from(Yield_)
    if jy:
        qy = qy.join(*jy)
    qy = qy.filter(gy.in_(entity_ids or [""]), Yield_.product_id.isnot(None))
    if months:
        qy = qy.filter(Yield_.yield_month.in_(months))
    if product_ids:
        qy = qy.filter(Yield_.product_id.in_(product_ids))
    for entity_id, product_id, planned, actual, next_plan, sold_qty, earning, loss_reason_id, stock_balance in qy.all():
        cell = out.setdefault(entity_id, {}).setdefault(product_id, _new_output_cell())
        cell["planned"] += float(planned or 0)
        cell["actual"] += float(actual or 0)
        cell["next_month_plan"] += float(next_plan or 0)
        cell["sold_quantity"] += float(sold_qty or 0)
        cell["earning"] += float(earning or 0)
        cell["stock_balance"] = float(stock_balance or 0)
        if loss_reason_id:
            cell["loss_reason_ids"].add(loss_reason_id)

    gb, jb = _group_and_join(level, ByproductEntry)
    qb = db.query(gb, ByproductEntry.product_id, ByproductEntry.planned_quantity, ByproductEntry.quantity,
                  ByproductEntry.next_month_plan, ByproductEntry.sold_quantity, ByproductEntry.earning,
                  ByproductEntry.loss_reason_id, ByproductEntry.stock_balance).select_from(ByproductEntry)
    if jb:
        qb = qb.join(*jb)
    qb = qb.filter(gb.in_(entity_ids or [""]))
    if months:
        qb = qb.filter(ByproductEntry.yield_month.in_(months))
    if product_ids:
        qb = qb.filter(ByproductEntry.product_id.in_(product_ids))
    for entity_id, product_id, planned, actual, next_plan, sold_qty, earning, loss_reason_id, stock_balance in qb.all():
        cell = out.setdefault(entity_id, {}).setdefault(product_id, _new_output_cell())
        cell["planned"] += float(planned or 0)
        cell["actual"] += float(actual or 0)
        cell["next_month_plan"] += float(next_plan or 0)
        cell["sold_quantity"] += float(sold_qty or 0)
        cell["earning"] += float(earning or 0)
        cell["stock_balance"] = float(stock_balance or 0)
        if loss_reason_id:
            cell["loss_reason_ids"].add(loss_reason_id)
    return out


def matrix_stock(db: Session, level: str, entity_ids: list[str],
                  product_ids: Optional[list[str]]) -> dict[str, dict[str, float]]:
    """Current snapshot only — no months filter, ever (Stock is a point-in-time balance,
    never additive across a period — see CLAUDE.md's Production-vs-Stock rule).

    Bypassed entirely for `level == "meeting"`: Stock has no meeting_id/parent_yield_id at all
    (it's a running balance, not a submission-scoped record) — that level instead sources its
    "Stock (at submission)" column from matrix_output()'s per-record stock_balance, see
    build_matrix()."""
    if level == "meeting":
        return {}
    group_col, join = _group_and_join(level, Stock)
    q = db.query(group_col, Stock.product_id, func.sum(Stock.closing_balance).label("qty")).select_from(Stock)
    if join:
        q = q.join(*join)
    q = q.filter(group_col.in_(entity_ids or [""]))
    if product_ids:
        q = q.filter(Stock.product_id.in_(product_ids))
    out: dict[str, dict[str, float]] = {}
    for entity_id, product_id, qty in q.group_by(group_col, Stock.product_id).all():
        out.setdefault(entity_id, {})[product_id] = float(qty or 0)
    return out


def available_products(db: Session, level: str, district_id_scope: Optional[str],
                        months: Optional[list[str]]) -> dict[str, list[str]]:
    """Distinct product ids with any data, over the FULL (unpaginated) scope — used to default
    the frontend's Products-shown multi-select independent of on-screen pagination."""
    all_ids = entities_all_ids(db, level, district_id_scope)
    if not all_ids:
        return {"input": [], "output": [], "stock": []}

    gi, ji = _group_and_join(level, YieldInputEntry)
    qi = db.query(YieldInputEntry.product_id).select_from(YieldInputEntry)
    if ji:
        qi = qi.join(*ji)
    qi = qi.filter(gi.in_(all_ids))
    if months:
        qi = qi.filter(YieldInputEntry.yield_month.in_(months))
    input_ids = [r[0] for r in qi.distinct().all()]

    gy, jy = _group_and_join(level, Yield_)
    qy = db.query(Yield_.product_id).select_from(Yield_)
    if jy:
        qy = qy.join(*jy)
    qy = qy.filter(gy.in_(all_ids), Yield_.product_id.isnot(None))
    if months:
        qy = qy.filter(Yield_.yield_month.in_(months))
    gb, jb = _group_and_join(level, ByproductEntry)
    qb = db.query(ByproductEntry.product_id).select_from(ByproductEntry)
    if jb:
        qb = qb.join(*jb)
    qb = qb.filter(gb.in_(all_ids))
    if months:
        qb = qb.filter(ByproductEntry.yield_month.in_(months))
    output_ids = list({*[r[0] for r in qy.distinct().all()], *[r[0] for r in qb.distinct().all()]})

    if level == "meeting":
        # "Stock (at submission)" is the historical stock_balance already carried on each
        # output record itself — see matrix_output/build_matrix — so its column set is just
        # whichever output products exist, not an independent query against Stock (which has
        # no meeting-level concept at all).
        stock_ids = list(output_ids)
    else:
        gs, js = _group_and_join(level, Stock)
        qs = db.query(Stock.product_id).select_from(Stock)
        if js:
            qs = qs.join(*js)
        qs = qs.filter(gs.in_(all_ids))
        stock_ids = [r[0] for r in qs.distinct().all()]

    return {"input": input_ids, "output": output_ids, "stock": stock_ids}


def available_input_sources(db: Session, level: str, district_id_scope: Optional[str],
                             months: Optional[list[str]], product_ids: Optional[list[str]]) -> dict[str, list[str]]:
    """Distinct source-type names per input product, over the FULL (unpaginated) scope —
    mirrors available_products()'s rationale exactly, so an input product's set of source
    sub-columns stays stable as the admin pages through results rather than shifting based on
    whichever page happens to be on screen."""
    all_ids = entities_all_ids(db, level, district_id_scope)
    if not all_ids:
        return {}
    gi, ji = _group_and_join(level, YieldInputEntry)
    q = db.query(YieldInputEntry.product_id, InputSourceType.source_name) \
        .select_from(YieldInputEntry) \
        .join(InputSourceType, InputSourceType.id == YieldInputEntry.source_type_id)
    if ji:
        q = q.join(*ji)
    q = q.filter(gi.in_(all_ids))
    if months:
        q = q.filter(YieldInputEntry.yield_month.in_(months))
    if product_ids:
        q = q.filter(YieldInputEntry.product_id.in_(product_ids))
    out: dict[str, list[str]] = {}
    for product_id, source_name in q.distinct().all():
        out.setdefault(product_id, [])
        if source_name not in out[product_id]:
            out[product_id].append(source_name)
    for pid in out:
        out[pid].sort()
    return out


def applicable_conversion_standards(db: Session, output_product_ids: list[str]) -> list[ConversionStandard]:
    if not output_product_ids:
        return []
    return db.query(ConversionStandard).filter(
        ConversionStandard.is_active, ConversionStandard.output_product_id.in_(output_product_ids)
    ).all()


def resolve_column_ids(avail: dict[str, list[str]], requested: Optional[list[str]]) -> tuple[list[str], list[str], list[str]]:
    """Intersects each group's available-with-data ids against the admin's "Products shown"
    selection (None = no filter applied, i.e. show everything with data). Keeping this
    per-group (rather than one shared list) means a product only ever gets a column in a
    group it's actually relevant to — e.g. checking an input-only product never creates a
    spurious empty OUTPUT/STOCK column for it."""
    def _pick(ids: list[str]) -> list[str]:
        return ids if requested is None else [p for p in ids if p in requested]
    return _pick(avail["input"]), _pick(avail["output"]), _pick(avail["stock"])


def build_matrix(db: Session, level: str, entities: list[dict], months: Optional[list[str]],
                  input_ids: list[str], output_ids: list[str], stock_ids: list[str],
                  input_sources: Optional[dict[str, list[str]]] = None) -> dict:
    """Shared assembly: called by both the paginated JSON endpoint (with the current page's
    entities) and the export dispatcher (with the full unpaginated entity list) — this is what
    guarantees export == exactly what's on screen, just not paginated. The three column-id
    lists are resolved by the caller (see resolve_column_ids) against the FULL scope's
    available_products(), not derived from this call's own (possibly page-limited) data, so
    the column set never shifts as the admin pages through results. `input_sources` is the
    (also full-scope-resolved) available_input_sources() result, used only to populate each
    input product's "sources" column list — never to filter data."""
    input_sources = input_sources or {}
    entity_ids = [e["id"] for e in entities]

    inputs = matrix_input(db, level, entity_ids, months, input_ids)
    outputs = matrix_output(db, level, entity_ids, months, output_ids)
    stocks = matrix_stock(db, level, entity_ids, stock_ids)

    standards = applicable_conversion_standards(db, list(output_ids))
    standards_by_output: dict[str, list[ConversionStandard]] = {}
    for s in standards:
        standards_by_output.setdefault(s.output_product_id, []).append(s)

    # A conversion standard's input_product_id must resolve to a real name even when that
    # product has zero actual INPUT/OUTPUT/STOCK data in the current filtered window (e.g. a
    # single month at the "meeting" level) — otherwise "Expected (via ...)" silently degrades
    # to a raw product id instead of falling back cleanly.
    all_product_ids = set(input_ids) | set(output_ids) | set(stock_ids) | {s.input_product_id for s in standards}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(all_product_ids or [""])).all()}

    all_loss_reason_ids = {rid for cells in outputs.values() for cell in cells.values() for rid in cell["loss_reason_ids"]}
    loss_reason_names = {lr.id: lr.reason_name for lr in
                          db.query(LossReason).filter(LossReason.id.in_(all_loss_reason_ids or [""])).all()}

    def _prod(pid: str) -> dict:
        p = products.get(pid)
        return {"id": pid, "product_name": p.product_name if p else pid, "unit_of_measure": p.unit_of_measure if p else ""}

    def _name_key(pid: str) -> str:
        p = products.get(pid)
        return p.product_name if p else pid

    def _input_prod(pid: str) -> dict:
        entry = _prod(pid)
        entry["sources"] = input_sources.get(pid, [])
        return entry

    def _loss_reason_name(reason_ids: set) -> Optional[str]:
        if not reason_ids:
            return None
        if len(reason_ids) > 1:
            return "Multiple"
        return loss_reason_names.get(next(iter(reason_ids)), "Multiple")

    output_products = []
    for pid in sorted(output_ids, key=_name_key):
        entry = _prod(pid)
        entry["expected_ranges"] = [{
            "standard_id": s.id, "input_product_id": s.input_product_id,
            "input_product_name": products.get(s.input_product_id).product_name if products.get(s.input_product_id) else s.input_product_id,
            "min_pct": s.min_pct, "max_pct": s.max_pct,
        } for s in standards_by_output.get(pid, [])]
        output_products.append(entry)

    items = []
    for e in entities:
        eid = e["id"]
        out_cell = {}
        for pid in output_ids:
            cell = outputs.get(eid, {}).get(pid, _new_output_cell())
            expected: dict[str, Optional[dict]] = {}
            for s in standards_by_output.get(pid, []):
                in_qty = inputs.get(eid, {}).get(s.input_product_id, {}).get("total", 0.0)
                expected[s.id] = {
                    "min": round(in_qty * s.min_pct / 100, 3), "max": round(in_qty * s.max_pct / 100, 3),
                    "input_qty": in_qty,
                } if in_qty else None
            sold_qty = cell["sold_quantity"]
            out_cell[pid] = {
                "planned": cell["planned"], "actual": cell["actual"], "expected_ranges": expected,
                "next_month_plan": cell["next_month_plan"], "sold_quantity": sold_qty,
                "earning": cell["earning"],
                "sold_rate": round(cell["earning"] / sold_qty, 2) if sold_qty else None,
                "loss_reason_name": _loss_reason_name(cell["loss_reason_ids"]),
            }
        # "meeting" has no live Stock-table concept (see matrix_stock's bypass) — its Stock
        # column instead reads the historical stock_balance already captured per output record.
        if level == "meeting":
            stock_cell = {pid: outputs.get(eid, {}).get(pid, _new_output_cell())["stock_balance"] for pid in stock_ids}
        else:
            stock_cell = {pid: stocks.get(eid, {}).get(pid, 0.0) for pid in stock_ids}
        items.append({
            "id": eid, "name": e["name"],
            "district_name": e.get("district_name"), "seri_circle_name": e.get("seri_circle_name"),
            "fig_name": e.get("fig_name"), "fig_code": e.get("fig_code"), "farmer_code": e.get("farmer_code"),
            "meeting_id": e.get("meeting_id"), "meeting_month": e.get("meeting_month"),
            "meeting_title": e.get("meeting_title"), "meeting_date": e.get("meeting_date"),
            "meeting_venue": e.get("meeting_venue"), "farmer_mobile": e.get("farmer_mobile"),
            "input": {pid: inputs.get(eid, {}).get(pid, {"total": 0.0, "by_source": {}}) for pid in input_ids},
            "output": out_cell,
            "stock": stock_cell,
        })

    return {
        "level": level, "months": months,
        "input_products": [_input_prod(p) for p in sorted(input_ids, key=_name_key)],
        "output_products": output_products,
        "stock_products": [_prod(p) for p in sorted(stock_ids, key=_name_key)],
        "items": items,
    }
