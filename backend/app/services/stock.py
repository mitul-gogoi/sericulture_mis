"""Stock snapshot upserts — keep `Stock.closing_balance` correct after every production write.

One row per (farmer_id, product_id); each write applies a delta (produced − sold) via a single
`INSERT ... ON CONFLICT DO UPDATE`, never a full recompute over history.

This relies on `Yield_`/`ByproductEntry` rows being immutable after submission (no edit/delete
endpoint exists for either today) — if that ever changes, a compensating-adjustment step must
be added here rather than silently letting balances drift.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from app.models import Stock, Product, Yield_, ByproductEntry, _now


def _upsert(db: Session, *, farmer_id: str, fig_id: str, product_id: str,
            delta: float, yield_month: str, is_perishable: bool,
            source_yield_id: str | None = None, source_byproduct_id: str | None = None) -> None:
    now = _now()
    stmt = pg_insert(Stock).values(
        farmer_id=farmer_id, fig_id=fig_id, product_id=product_id,
        opening_balance=0, closing_balance=delta, is_perishable=is_perishable,
        last_produced_month=yield_month, last_entry_at=now,
        last_source_yield_id=source_yield_id, last_source_byproduct_id=source_byproduct_id,
        updated_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["farmer_id", "product_id"],
        set_={
            "fig_id": fig_id,
            "closing_balance": Stock.closing_balance + delta,
            "is_perishable": is_perishable,
            "last_produced_month": yield_month,
            "last_entry_at": now,
            "last_source_yield_id": source_yield_id,
            "last_source_byproduct_id": source_byproduct_id,
            "updated_at": now,
        },
    )
    db.execute(stmt)


def upsert_stock_for_yield(db: Session, yield_row: Yield_) -> None:
    if not yield_row.product_id:
        return  # legacy stage with no mapping yet — nothing to snapshot
    product = db.query(Product).filter(Product.id == yield_row.product_id).first()
    _upsert(
        db, farmer_id=yield_row.farmer_id, fig_id=yield_row.fig_id, product_id=yield_row.product_id,
        delta=float(yield_row.actual_yield or 0) - float(yield_row.sold_quantity or 0),
        yield_month=yield_row.yield_month,
        is_perishable=bool(product.is_perishable) if product else False,
        source_yield_id=yield_row.id,
    )


def upsert_stock_for_byproduct(db: Session, bp_row: ByproductEntry) -> None:
    product = db.query(Product).filter(Product.id == bp_row.product_id).first()
    _upsert(
        db, farmer_id=bp_row.farmer_id, fig_id=bp_row.fig_id, product_id=bp_row.product_id,
        delta=float(bp_row.quantity or 0) - float(bp_row.sold_quantity or 0),
        yield_month=bp_row.yield_month,
        is_perishable=bool(product.is_perishable) if product else False,
        source_byproduct_id=bp_row.id,
    )
