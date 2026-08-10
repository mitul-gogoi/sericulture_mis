"""Silk-type / activity / product (STAP) production taxonomy — read (public)
+ State-Admin-only CRUD."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.db import get_session, commit_or_conflict, delete_or_conflict
from app.core.deps import get_current_user
from app.models import (
    SilkType, Activity, Product, SilkTypeActivityProduct, InputSourceType, StapSourceType,
    InputSourceCategory, User, Yield_, ByproductEntry, YieldInputEntry, Stock, Training, Fig, Farmer,
    ConversionStandard,
)
from ._common import _SA, _q, _get_or_404, ActiveToggleIn

router = APIRouter()


@router.get("/silk-types")
def list_silk_types(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, SilkType, all).order_by(SilkType.silk_type_name).all()


@router.get("/activities")
def list_activities(silk_type_id: Optional[str] = None,
                     all: bool = False, db: Session = Depends(get_session)):
    q = _q(db, Activity, all)
    if silk_type_id:
        q = q.filter(Activity.silk_type_id == silk_type_id)
    rows = q.all()
    silk_types = {s.id: s.silk_type_name for s in db.query(SilkType).all()}

    def _sort_key(a: Activity):
        return (silk_types.get(a.silk_type_id) or "", a.step_no)

    rows.sort(key=_sort_key)
    out = []
    for a in rows:
        out.append({
            "id": a.id, "activity_name": a.activity_name, "silk_type_id": a.silk_type_id,
            "step_no": a.step_no,
            "description": a.description, "is_active": a.is_active,
            "silk_type_name": silk_types.get(a.silk_type_id),
        })
    return out


@router.get("/products")
def list_products(silk_type_id: Optional[str] = None, all: bool = False, db: Session = Depends(get_session)):
    q = _q(db, Product, all)
    if silk_type_id:
        q = q.filter(or_(Product.silk_type_id == silk_type_id, Product.silk_type_id.is_(None)))
    rows = q.order_by(Product.product_name).all()
    silk_types = {s.id: s.silk_type_name for s in db.query(SilkType).all()}
    out = []
    for p in rows:
        d = p.model_dump()
        d["silk_type_name"] = silk_types.get(p.silk_type_id)
        out.append(d)
    return out


@router.get("/silk-type-activity-products")
def list_stap(silk_type_id: Optional[str] = None, activity_id: Optional[str] = None,
              product_id: Optional[str] = None, is_byproduct: Optional[bool] = None,
              role: Optional[str] = None,
              all: bool = False, db: Session = Depends(get_session)):
    q = _q(db, SilkTypeActivityProduct, all)
    if silk_type_id:
        q = q.filter(SilkTypeActivityProduct.silk_type_id == silk_type_id)
    if activity_id:
        q = q.filter(SilkTypeActivityProduct.activity_id == activity_id)
    if product_id:
        q = q.filter(SilkTypeActivityProduct.product_id == product_id)
    if role:
        q = q.filter(SilkTypeActivityProduct.role == role)
    rows = q.all()
    if is_byproduct is not None:
        product_ids = {p.id for p in db.query(Product).filter(Product.is_byproduct == is_byproduct).all()}
        rows = [r for r in rows if r.product_id in product_ids]
    silk_types = {s.id: s.silk_type_name for s in db.query(SilkType).all()}
    activities = {a.id: a for a in db.query(Activity).all()}
    products = {p.id: p for p in db.query(Product).all()}
    source_types = {s.id: s for s in db.query(InputSourceType).all()}
    categories = {c.id: c.category_name for c in db.query(InputSourceCategory).all()}
    stap_source_type_ids: dict[str, list[str]] = {}
    for sst in db.query(StapSourceType).filter(StapSourceType.stap_id.in_([r.id for r in rows] or [""])).all():
        stap_source_type_ids.setdefault(sst.stap_id, []).append(sst.source_type_id)
    out = []
    for r in rows:
        p = products.get(r.product_id)
        a = activities.get(r.activity_id)
        source_type_ids = stap_source_type_ids.get(r.id, [])
        out.append({
            "id": r.id, "silk_type_id": r.silk_type_id, "activity_id": r.activity_id,
            "product_id": r.product_id, "role": r.role, "input_group": r.input_group, "is_active": r.is_active,
            "silk_type_name": silk_types.get(r.silk_type_id),
            "activity_name": a.activity_name if a else None,
            "step_no": a.step_no if a else None,
            "product_name": p.product_name if p else None,
            "unit_of_measure": p.unit_of_measure if p else None,
            "is_perishable": p.is_perishable if p else None,
            "is_byproduct": p.is_byproduct if p else None,
            "source_type_ids": source_type_ids,
            "source_type_names": [source_types[sid].source_name for sid in source_type_ids if sid in source_types],
            "input_source_category_id": r.input_source_category_id,
            "input_source_category_name": categories.get(r.input_source_category_id),
        })
    out.sort(key=lambda r: (r["silk_type_name"] or "", r["step_no"] or 0, r["role"] or "", r["product_name"] or ""))
    return out


@router.get("/silk-type-activity-products/{stap_id}/options")
def stap_options(stap_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    stap = db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id == stap_id).first()
    if not stap:
        raise HTTPException(404, "Mapping not found")
    primary = db.query(Product).filter(Product.id == stap.product_id).first()
    same_activity = db.query(SilkTypeActivityProduct).filter(
        SilkTypeActivityProduct.silk_type_id == stap.silk_type_id,
        SilkTypeActivityProduct.activity_id == stap.activity_id,
        SilkTypeActivityProduct.is_active,
    )
    byproducts = db.query(Product).filter(
        Product.is_byproduct, Product.is_active,
        Product.id.in_(same_activity.filter(SilkTypeActivityProduct.role == "OUTPUT").with_entities(SilkTypeActivityProduct.product_id)),
    ).all()
    input_rows = same_activity.filter(SilkTypeActivityProduct.role == "INPUT").all()
    input_groups = {r.product_id: r.input_group for r in input_rows}
    input_row_by_product = {r.product_id: r for r in input_rows}
    inputs = db.query(Product).filter(
        Product.is_active,
        Product.id.in_([r.product_id for r in input_rows]),
    ).all()
    # A product is "chain-internal" if it's produced as an OUTPUT by some activity in this
    # silk type — meaning an "Own Source" input for it can plausibly draw down real Stock
    # or this cycle's already-entered producing-activity output.
    producing_stap_by_product: dict[str, str] = {}
    for r in db.query(SilkTypeActivityProduct).filter(
        SilkTypeActivityProduct.silk_type_id == stap.silk_type_id,
        SilkTypeActivityProduct.role == "OUTPUT",
        SilkTypeActivityProduct.is_active,
    ).all():
        producing_stap_by_product[r.product_id] = r.id

    all_source_types = db.query(InputSourceType).filter(InputSourceType.is_active).order_by(InputSourceType.source_name).all()
    configured_by_stap: dict[str, list[str]] = {}
    for sst in db.query(StapSourceType).filter(StapSourceType.stap_id.in_([r.id for r in input_rows] or [""])).all():
        configured_by_stap.setdefault(sst.stap_id, []).append(sst.source_type_id)

    def _allowed_source_types(input_row: SilkTypeActivityProduct) -> list[dict]:
        configured_ids = configured_by_stap.get(input_row.id)
        if configured_ids:
            chosen = [s for s in all_source_types if s.id in configured_ids]
        elif input_row.input_source_category_id:
            chosen = [s for s in all_source_types if s.category_id == input_row.input_source_category_id]
        else:
            chosen = all_source_types  # nothing configured at all — fall back to all active types
        return [{"id": s.id, "source_name": s.source_name, "requires_scheme": s.requires_scheme,
                 "is_own_source": s.is_own_source} for s in chosen]

    return {
        "primary": {"product_id": primary.id, "product_name": primary.product_name, "unit_of_measure": primary.unit_of_measure} if primary else None,
        "byproducts": [{"product_id": p.id, "product_name": p.product_name, "unit_of_measure": p.unit_of_measure} for p in byproducts],
        "inputs": [{
            "product_id": p.id, "product_name": p.product_name, "unit_of_measure": p.unit_of_measure,
            "input_group": input_groups.get(p.id),
            "is_chain_internal": p.id in producing_stap_by_product,
            "producing_stap_id": producing_stap_by_product.get(p.id),
            "allowed_source_types": _allowed_source_types(input_row_by_product[p.id]),
        } for p in inputs],
    }


class SilkTypeIn(BaseModel):
    silk_type_name: str = Field(min_length=1, max_length=50)
    is_active: Optional[bool] = None


class ActivityIn(BaseModel):
    activity_name: str = Field(min_length=1, max_length=120)
    silk_type_id: str
    step_no: int
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProductIn(BaseModel):
    product_name: str = Field(min_length=1, max_length=80)
    unit_of_measure: str = Field(min_length=1, max_length=30)
    silk_type_id: Optional[str] = None
    default_source_category_id: Optional[str] = None
    is_perishable: bool = False
    is_byproduct: bool = False
    show_in_dashboard: bool = True
    is_active: Optional[bool] = None


class StapIn(BaseModel):
    silk_type_id: str
    activity_id: str
    product_id: str
    role: str = Field(default="OUTPUT", pattern="^(INPUT|OUTPUT)$")
    input_group: Optional[str] = Field(default=None, max_length=40)
    input_source_category_id: Optional[str] = None
    source_type_ids: list[str] = []


class StapBatchItemIn(BaseModel):
    product_id: str
    role: str = Field(pattern="^(INPUT|OUTPUT)$")
    input_group: Optional[str] = Field(default=None, max_length=40)
    input_source_category_id: Optional[str] = None
    source_type_ids: list[str] = []


class StapBatchIn(BaseModel):
    silk_type_id: str
    activity_id: str
    items: list[StapBatchItemIn]


# ---------- Silk Types ----------
@router.post("/silk-types")
def create_silk_type(body: SilkTypeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = SilkType(silk_type_name=body.silk_type_name.strip(),
                 is_active=True if body.is_active is None else body.is_active)
    db.add(s)
    commit_or_conflict(db, "Silk type name already exists")
    db.refresh(s)
    return s


@router.patch("/silk-types/{silk_type_id}")
def update_silk_type(silk_type_id: str, body: SilkTypeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = _get_or_404(db, SilkType, silk_type_id, "Silk type")
    s.silk_type_name = body.silk_type_name.strip()
    if body.is_active is not None:
        s.is_active = body.is_active
    commit_or_conflict(db, "Silk type name already exists")
    db.refresh(s)
    return s


@router.patch("/silk-types/{silk_type_id}/active")
def toggle_silk_type(silk_type_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = _get_or_404(db, SilkType, silk_type_id, "Silk type")
    s.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": s.is_active}


@router.delete("/silk-types/{silk_type_id}")
def delete_silk_type(silk_type_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = _get_or_404(db, SilkType, silk_type_id, "Silk type")
    if s.is_active:
        raise HTTPException(400, "Deactivate this silk type before deleting it")
    delete_or_conflict(db, s, "Cannot delete — one or more silk-type/activity/product mappings still reference this silk type")
    return {"ok": True}


# ---------- Activities ----------
@router.post("/activities")
def create_activity(body: ActivityIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    a = Activity(activity_name=body.activity_name.strip(), silk_type_id=body.silk_type_id,
                 step_no=body.step_no, description=body.description,
                 is_active=True if body.is_active is None else body.is_active)
    db.add(a)
    commit_or_conflict(db, "This activity name, or this step position, already exists for this silk type")
    db.refresh(a)
    return a


@router.patch("/activities/{activity_id}")
def update_activity(activity_id: str, body: ActivityIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    a = _get_or_404(db, Activity, activity_id, "Activity")
    _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    if body.silk_type_id != a.silk_type_id:
        has_mappings = db.query(SilkTypeActivityProduct).filter(
            SilkTypeActivityProduct.activity_id == activity_id
        ).first() is not None
        if has_mappings:
            raise HTTPException(400,
                "Cannot change this activity's silk type — it already has Map-Activity-to-Product "
                "mapping(s) tied to its current silk type. Deactivate this activity and create a "
                "new one under the correct silk type instead.")
    a.activity_name = body.activity_name.strip()
    a.silk_type_id = body.silk_type_id
    a.step_no = body.step_no
    a.description = body.description
    if body.is_active is not None:
        a.is_active = body.is_active
    commit_or_conflict(db, "This activity name, or this step position, already exists for this silk type")
    db.refresh(a)
    return a


@router.patch("/activities/{activity_id}/active")
def toggle_activity(activity_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    a = _get_or_404(db, Activity, activity_id, "Activity")
    a.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": a.is_active}


@router.get("/activities/{activity_id}/usage")
def activity_usage(activity_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, Activity, activity_id, "Activity")
    stap_rows = db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.activity_id == activity_id).all()
    active_stap = sum(1 for m in stap_rows if m.is_active)
    yields = db.query(Yield_).filter(Yield_.activity_id == activity_id).count()
    trainings = db.query(Training).filter(Training.activity_id == activity_id).count()
    blockers = []
    if active_stap:
        blockers.append(f"{active_stap} active Map-Activity-to-Product mapping(s)")
    if yields:
        blockers.append(f"{yields} yield record(s)")
    if trainings:
        blockers.append(f"{trainings} training(s)")
    return {"blockers": blockers}


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    a = _get_or_404(db, Activity, activity_id, "Activity")
    if a.is_active:
        raise HTTPException(400, "Deactivate this activity before deleting it")
    delete_or_conflict(db, a, "Cannot delete — one or more silk-type/activity/product mappings or yield records still reference this activity")
    return {"ok": True}


# ---------- Products ----------
@router.post("/products")
def create_product(body: ProductIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    if body.silk_type_id:
        _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    if body.default_source_category_id:
        _get_or_404(db, InputSourceCategory, body.default_source_category_id, "Input source category")
    p = Product(product_name=body.product_name.strip(), unit_of_measure=body.unit_of_measure.strip(),
                silk_type_id=body.silk_type_id, default_source_category_id=body.default_source_category_id,
                is_perishable=body.is_perishable, is_byproduct=body.is_byproduct,
                show_in_dashboard=body.show_in_dashboard,
                is_active=True if body.is_active is None else body.is_active)
    db.add(p)
    commit_or_conflict(db, "Product name already exists")
    db.refresh(p)
    return p


@router.patch("/products/{product_id}")
def update_product(product_id: str, body: ProductIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    p = _get_or_404(db, Product, product_id, "Product")
    if body.silk_type_id:
        _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    if body.default_source_category_id:
        _get_or_404(db, InputSourceCategory, body.default_source_category_id, "Input source category")
    p.product_name = body.product_name.strip()
    p.unit_of_measure = body.unit_of_measure.strip()
    p.silk_type_id = body.silk_type_id
    p.default_source_category_id = body.default_source_category_id
    p.is_perishable = body.is_perishable
    p.is_byproduct = body.is_byproduct
    p.show_in_dashboard = body.show_in_dashboard
    if body.is_active is not None:
        p.is_active = body.is_active
    commit_or_conflict(db, "Product name already exists")
    db.refresh(p)
    return p


@router.patch("/products/{product_id}/active")
def toggle_product(product_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    p = _get_or_404(db, Product, product_id, "Product")
    p.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": p.is_active}


def _product_reference_summary(db: Session, product_id: str) -> dict:
    """Every row across the 5 FK'd tables that still references this product, split into
    cascade-safe (inactive STAP config) vs. permanent (active mappings + real transactional
    history) so delete_product can name the specific blocker instead of a generic message."""
    stap_rows = (
        db.query(SilkTypeActivityProduct, Activity)
        .join(Activity, Activity.id == SilkTypeActivityProduct.activity_id)
        .filter(SilkTypeActivityProduct.product_id == product_id)
        .all()
    )
    stap_active = [(m, a) for m, a in stap_rows if m.is_active]
    stap_inactive = [(m, a) for m, a in stap_rows if not m.is_active]
    return {
        "stap_active": [{"id": m.id, "activity_name": a.activity_name, "role": m.role} for m, a in stap_active],
        "stap_inactive": [{"id": m.id, "activity_name": a.activity_name, "role": m.role} for m, a in stap_inactive],
        "yields": db.query(Yield_).filter(Yield_.product_id == product_id).count(),
        "byproduct_entries": db.query(ByproductEntry).filter(ByproductEntry.product_id == product_id).count(),
        "yield_input_entries": db.query(YieldInputEntry).filter(YieldInputEntry.product_id == product_id).count(),
        "stock": db.query(Stock).filter(Stock.product_id == product_id).count(),
    }


@router.get("/products/{product_id}/usage")
def product_usage(product_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, Product, product_id, "Product")
    refs = _product_reference_summary(db, product_id)
    blockers = []
    if refs["stap_active"]:
        blockers.append(f"{len(refs['stap_active'])} active Map-Activity-to-Product mapping(s)")
    if refs["yields"]:
        blockers.append(f"{refs['yields']} yield record(s)")
    if refs["byproduct_entries"]:
        blockers.append(f"{refs['byproduct_entries']} byproduct entr{'y' if refs['byproduct_entries'] == 1 else 'ies'}")
    if refs["yield_input_entries"]:
        blockers.append(f"{refs['yield_input_entries']} yield input entr{'y' if refs['yield_input_entries'] == 1 else 'ies'}")
    if refs["stock"]:
        blockers.append(f"{refs['stock']} stock row(s)")
    return {"blockers": blockers}


@router.delete("/products/{product_id}")
def delete_product(product_id: str, cascade_inactive_mappings: bool = False,
                    user: User = Depends(_SA), db: Session = Depends(get_session)):
    p = _get_or_404(db, Product, product_id, "Product")
    if p.is_active:
        raise HTTPException(400, "Deactivate this product before deleting it")

    refs = _product_reference_summary(db, product_id)

    # Real transactional history and still-active mappings are never auto-cleaned — report only.
    permanent_parts = []
    if refs["yields"]:
        permanent_parts.append(f"{refs['yields']} yield record(s)")
    if refs["byproduct_entries"]:
        permanent_parts.append(f"{refs['byproduct_entries']} byproduct entr{'y' if refs['byproduct_entries'] == 1 else 'ies'}")
    if refs["yield_input_entries"]:
        permanent_parts.append(f"{refs['yield_input_entries']} yield input entr{'y' if refs['yield_input_entries'] == 1 else 'ies'}")
    if refs["stock"]:
        permanent_parts.append(f"{refs['stock']} stock row(s)")
    if refs["stap_active"]:
        names = ", ".join(f"{m['activity_name']} ({m['role']})" for m in refs["stap_active"])
        permanent_parts.append(f"{len(refs['stap_active'])} active mapping(s): {names}")

    if permanent_parts:
        raise HTTPException(400, "Cannot delete — this product is still referenced by: " + "; ".join(permanent_parts) +
                             ". Real production history and active mappings cannot be removed automatically.")

    if refs["stap_inactive"]:
        if not cascade_inactive_mappings:
            names = ", ".join(f"{m['activity_name']} ({m['role']})" for m in refs["stap_inactive"])
            raise HTTPException(400,
                f"This product has {len(refs['stap_inactive'])} inactive mapping(s) still linked to it: {names}. "
                "Retry with cascade_inactive_mappings=true to remove them and delete the product.")
        stap_ids = [m["id"] for m in refs["stap_inactive"]]
        db.query(StapSourceType).filter(StapSourceType.stap_id.in_(stap_ids)).delete(synchronize_session=False)
        db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id.in_(stap_ids)).delete(synchronize_session=False)

    delete_or_conflict(db, p, "Cannot delete — this product is still referenced by other data")
    return {"ok": True}


# ---------- Silk Type × Activity × Product mapping ----------
@router.post("/silk-type-activity-products")
def create_stap(body: StapIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    activity = _get_or_404(db, Activity, body.activity_id, "Activity")
    product = _get_or_404(db, Product, body.product_id, "Product")
    if activity.silk_type_id != body.silk_type_id:
        raise HTTPException(400, "This activity belongs to a different silk type")
    if product.silk_type_id and product.silk_type_id != body.silk_type_id:
        raise HTTPException(400, "This product belongs to a different silk type")
    if body.input_group and body.role != "INPUT":
        raise HTTPException(400, "input_group only applies to INPUT-role mappings")
    if body.input_source_category_id and body.role != "INPUT":
        raise HTTPException(400, "input_source_category_id only applies to INPUT-role mappings")
    if body.source_type_ids and body.role != "INPUT":
        raise HTTPException(400, "source_type_ids only applies to INPUT-role mappings")
    if body.input_source_category_id:
        _get_or_404(db, InputSourceCategory, body.input_source_category_id, "Input source category")
    if body.input_source_category_id and body.source_type_ids:
        mismatched = [s.source_name for s in db.query(InputSourceType).filter(
            InputSourceType.id.in_(body.source_type_ids),
            InputSourceType.category_id != body.input_source_category_id,
        ).all()]
        if mismatched:
            raise HTTPException(400, f"These source types don't belong to the selected category: {', '.join(mismatched)}")
    m = SilkTypeActivityProduct(silk_type_id=body.silk_type_id, activity_id=body.activity_id,
                                product_id=body.product_id, role=body.role, input_group=body.input_group,
                                input_source_category_id=body.input_source_category_id)
    db.add(m)
    commit_or_conflict(db, "This silk type / activity / product / role combination already exists")
    db.refresh(m)
    if body.source_type_ids:
        valid_ids = {s.id for s in db.query(InputSourceType).filter(InputSourceType.id.in_(body.source_type_ids)).all()}
        for sid in body.source_type_ids:
            if sid in valid_ids:
                db.add(StapSourceType(stap_id=m.id, source_type_id=sid))
        db.commit()
    return m


@router.post("/silk-type-activity-products/batch")
def create_stap_batch(body: StapBatchIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    activity = _get_or_404(db, Activity, body.activity_id, "Activity")
    if activity.silk_type_id != body.silk_type_id:
        raise HTTPException(400, "This activity belongs to a different silk type")
    created = []
    updated = []
    for item in body.items:
        item_product = _get_or_404(db, Product, item.product_id, "Product")
        if item_product.silk_type_id and item_product.silk_type_id != body.silk_type_id:
            raise HTTPException(400, f"Product {item_product.product_name} belongs to a different silk type")
        if item.input_group and item.role != "INPUT":
            raise HTTPException(400, "input_group only applies to INPUT-role mappings")
        if item.input_source_category_id and item.role != "INPUT":
            raise HTTPException(400, "input_source_category_id only applies to INPUT-role mappings")
        if item.source_type_ids and item.role != "INPUT":
            raise HTTPException(400, "source_type_ids only applies to INPUT-role mappings")
        if item.input_source_category_id:
            _get_or_404(db, InputSourceCategory, item.input_source_category_id, "Input source category")
        if item.input_source_category_id and item.source_type_ids:
            mismatched = [s.source_name for s in db.query(InputSourceType).filter(
                InputSourceType.id.in_(item.source_type_ids),
                InputSourceType.category_id != item.input_source_category_id,
            ).all()]
            if mismatched:
                raise HTTPException(400, f"These source types don't belong to the selected category: {', '.join(mismatched)}")
        exists = db.query(SilkTypeActivityProduct).filter(
            SilkTypeActivityProduct.silk_type_id == body.silk_type_id,
            SilkTypeActivityProduct.activity_id == body.activity_id,
            SilkTypeActivityProduct.product_id == item.product_id,
            SilkTypeActivityProduct.role == item.role,
        ).first()
        if exists:
            # Being present in the batch payload means "this should be active" — reactivate a
            # previously-deactivated row even if nothing else about it changed.
            changed = not exists.is_active
            exists.is_active = True
            # Only INPUT rows carry editable fields (group/category/source types) — re-saving
            # an already-mapped OUTPUT has nothing else to update.
            if item.role == "INPUT":
                exists.input_group = item.input_group
                exists.input_source_category_id = item.input_source_category_id
                db.query(StapSourceType).filter(StapSourceType.stap_id == exists.id).delete()
                if item.source_type_ids:
                    valid_ids = {s.id for s in db.query(InputSourceType).filter(InputSourceType.id.in_(item.source_type_ids)).all()}
                    for sid in item.source_type_ids:
                        if sid in valid_ids:
                            db.add(StapSourceType(stap_id=exists.id, source_type_id=sid))
                changed = True
            if changed:
                updated.append(exists)
            continue
        m = SilkTypeActivityProduct(silk_type_id=body.silk_type_id, activity_id=body.activity_id,
                                    product_id=item.product_id, role=item.role, input_group=item.input_group,
                                    input_source_category_id=item.input_source_category_id)
        db.add(m)
        db.flush()
        if item.source_type_ids:
            valid_ids = {s.id for s in db.query(InputSourceType).filter(InputSourceType.id.in_(item.source_type_ids)).all()}
            for sid in item.source_type_ids:
                if sid in valid_ids:
                    db.add(StapSourceType(stap_id=m.id, source_type_id=sid))
        created.append(m)
    db.commit()
    for m in created + updated:
        db.refresh(m)
    return {"created": len(created), "updated": len(updated)}


@router.patch("/silk-type-activity-products/{stap_id}/active")
def toggle_stap(stap_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    m = _get_or_404(db, SilkTypeActivityProduct, stap_id, "Mapping")
    m.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": m.is_active}


def _stap_reference_summary(db: Session, stap_id: str) -> dict:
    """Everything still pointing at this STAP row: real transactional history (Yield_) plus the
    two soft (JSON/plain-string) references — Fig.stap_id and Farmer.stap_ids/primary_stap_id —
    that the DB's own FKs can't see, so delete_stap can name them instead of a generic 400.
    Farmer.stap_ids is a plain JSON column (not JSONB), so containment is checked in Python
    rather than a Postgres @> operator — fine at this app's farmer-table scale."""
    figs = db.query(Fig).filter(Fig.stap_id == stap_id).all()
    farmers = [
        f for f in db.query(Farmer).all()
        if f.primary_stap_id == stap_id or stap_id in (f.stap_ids or [])
    ]
    return {
        "yields": db.query(Yield_).filter(Yield_.stap_id == stap_id).count(),
        "figs": [{"id": f.id, "fig_name": f.fig_name} for f in figs],
        "farmers": [{"id": f.id, "name": f"{f.first_name} {f.last_name}"} for f in farmers],
    }


@router.get("/silk-type-activity-products/{stap_id}/usage")
def stap_usage(stap_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, SilkTypeActivityProduct, stap_id, "Mapping")
    refs = _stap_reference_summary(db, stap_id)
    blockers = []
    if refs["yields"]:
        blockers.append(f"{refs['yields']} yield record(s)")
    if refs["figs"]:
        blockers.append(f"{len(refs['figs'])} FIG(s) using this as their primary production")
    if refs["farmers"]:
        blockers.append(f"{len(refs['farmers'])} farmer(s) assigned this activity")
    return {"blockers": blockers}


@router.delete("/silk-type-activity-products/{stap_id}")
def delete_stap(stap_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    m = _get_or_404(db, SilkTypeActivityProduct, stap_id, "Mapping")
    if m.is_active:
        raise HTTPException(400, "Deactivate this mapping before deleting it")
    refs = _stap_reference_summary(db, stap_id)
    parts = []
    if refs["yields"]:
        parts.append(f"{refs['yields']} yield record(s)")
    if refs["figs"]:
        names = ", ".join(f["fig_name"] for f in refs["figs"])
        parts.append(f"{len(refs['figs'])} FIG(s) still set to this as their primary production: {names}")
    if refs["farmers"]:
        names = ", ".join(f["name"] for f in refs["farmers"][:5])
        more = f" and {len(refs['farmers']) - 5} more" if len(refs["farmers"]) > 5 else ""
        parts.append(f"{len(refs['farmers'])} farmer(s) still assigned this activity: {names}{more}")
    if parts:
        raise HTTPException(400, "Cannot delete — this mapping is still referenced by: " + "; ".join(parts) +
                             ". Reassign these to a different mapping first.")
    db.query(StapSourceType).filter(StapSourceType.stap_id == stap_id).delete()
    delete_or_conflict(db, m, "Cannot delete — this mapping is still referenced elsewhere")
    return {"ok": True}


# ---------- Conversion Standards ----------
# Expected input->output conversion range, independent of any specific Activity/STAP mapping
# (State Admin can map straight from an early-stage input to a late-stage output, e.g. Eri
# Eggs (DFL) -> Eri Silk Yarn). Consumed by the Yield View's "Expected" column — see
# services/yield_matrix.py.
class ConversionStandardIn(BaseModel):
    silk_type_id: str
    input_product_id: str
    output_product_id: str
    standard_input_qty: float = Field(gt=0)
    output_min_qty: float = Field(ge=0)
    output_max_qty: float = Field(ge=0)
    is_active: Optional[bool] = None


@router.get("/conversion-standards")
def list_conversion_standards(silk_type_id: Optional[str] = None, all: bool = False, db: Session = Depends(get_session)):
    q = _q(db, ConversionStandard, all)
    if silk_type_id:
        q = q.filter(ConversionStandard.silk_type_id == silk_type_id)
    rows = q.all()
    silk_types = {s.id: s.silk_type_name for s in db.query(SilkType).all()}
    products = {p.id: p for p in db.query(Product).all()}
    out = []
    for r in rows:
        ip, op_ = products.get(r.input_product_id), products.get(r.output_product_id)
        out.append({
            "id": r.id, "silk_type_id": r.silk_type_id, "silk_type_name": silk_types.get(r.silk_type_id),
            "input_product_id": r.input_product_id, "input_product_name": ip.product_name if ip else None,
            "input_unit_of_measure": ip.unit_of_measure if ip else None,
            "output_product_id": r.output_product_id, "output_product_name": op_.product_name if op_ else None,
            "output_unit_of_measure": op_.unit_of_measure if op_ else None,
            "standard_input_qty": r.standard_input_qty, "output_min_qty": r.output_min_qty,
            "output_max_qty": r.output_max_qty,
            "min_pct": r.min_pct, "max_pct": r.max_pct, "is_active": r.is_active,
        })
    out.sort(key=lambda r: (r["silk_type_name"] or "", r["input_product_name"] or "", r["output_product_name"] or ""))
    return out


def _validate_conversion_standard(db: Session, body: "ConversionStandardIn"):
    _get_or_404(db, SilkType, body.silk_type_id, "Silk type")
    _get_or_404(db, Product, body.input_product_id, "Input product")
    _get_or_404(db, Product, body.output_product_id, "Output product")
    if body.input_product_id == body.output_product_id:
        raise HTTPException(400, "Input and output product must be different")
    if body.output_max_qty < body.output_min_qty:
        raise HTTPException(400, "Output Max Quantity must be greater than or equal to Output Min Quantity")


def _derived_pcts(body: "ConversionStandardIn") -> tuple[float, float]:
    """The system computes the Expected % range from the admin's entered quantities — this is
    the one place that derivation happens; min_pct/max_pct then flow through to the Yield View's
    existing Expected-range calculation (services/yield_matrix.py) completely unchanged."""
    return (
        round(body.output_min_qty / body.standard_input_qty * 100, 4),
        round(body.output_max_qty / body.standard_input_qty * 100, 4),
    )


@router.post("/conversion-standards")
def create_conversion_standard(body: ConversionStandardIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _validate_conversion_standard(db, body)
    min_pct, max_pct = _derived_pcts(body)
    c = ConversionStandard(silk_type_id=body.silk_type_id, input_product_id=body.input_product_id,
                            output_product_id=body.output_product_id,
                            standard_input_qty=body.standard_input_qty, output_min_qty=body.output_min_qty,
                            output_max_qty=body.output_max_qty, min_pct=min_pct, max_pct=max_pct,
                            is_active=True if body.is_active is None else body.is_active)
    db.add(c)
    commit_or_conflict(db, "This Silk Type / Input Product / Output Product combination already exists — edit or reactivate it instead")
    db.refresh(c)
    return c


@router.patch("/conversion-standards/{cs_id}")
def update_conversion_standard(cs_id: str, body: ConversionStandardIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, ConversionStandard, cs_id, "Conversion standard")
    _validate_conversion_standard(db, body)
    min_pct, max_pct = _derived_pcts(body)
    c.silk_type_id, c.input_product_id, c.output_product_id = body.silk_type_id, body.input_product_id, body.output_product_id
    c.standard_input_qty, c.output_min_qty, c.output_max_qty = body.standard_input_qty, body.output_min_qty, body.output_max_qty
    c.min_pct, c.max_pct = min_pct, max_pct
    if body.is_active is not None:
        c.is_active = body.is_active
    commit_or_conflict(db, "This Silk Type / Input Product / Output Product combination already exists")
    db.refresh(c)
    return c


@router.patch("/conversion-standards/{cs_id}/active")
def toggle_conversion_standard(cs_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, ConversionStandard, cs_id, "Conversion standard")
    c.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": c.is_active}


@router.delete("/conversion-standards/{cs_id}")
def delete_conversion_standard(cs_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, ConversionStandard, cs_id, "Conversion standard")
    if c.is_active:
        raise HTTPException(400, "Deactivate this conversion standard before deleting it")
    delete_or_conflict(db, c, "Cannot delete — this conversion standard is still referenced elsewhere")
    return {"ok": True}
    return {"ok": True}
