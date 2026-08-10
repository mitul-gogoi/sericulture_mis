"""Asset helpers — useful-life cooldown + owner resolution.

`asset_instances` is the single source of truth for "what durable assets does this
farmer/FIG already hold". The cooldown check deliberately ignores acquisition_mode:
a scheme-funded, self-procured or self-declared asset all count equally, otherwise
pre-digital history would be invisible to eligibility screening.
"""
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    AssetInstance, AssetType, FigMember, Farmer, Fig, District, SericultureCircle, Scheme, User,
)


def add_years(d: date, years: int) -> date:
    """Year arithmetic that survives Feb 29 (no external dateutil dependency)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def asset_code(seq: int) -> str:
    return f"SERI-AST-{seq:05d}"


def next_asset_seq(db: Session) -> int:
    """Shared by routers/assets.py (create_asset) and routers/figs.py (create_fig's
    atomic asset capture) — no floor/skip-zero rule, unlike Farmer/FIG codes."""
    max_num = 0
    for (code,) in db.query(AssetInstance.asset_code).all():
        try:
            num = int(code.rsplit("-", 1)[-1])
        except (ValueError, AttributeError):
            continue
        max_num = max(max_num, num)
    return max_num + 1


def check_asset_cooldown(db: Session, owner_type: str, owner_id: str, asset_type_id: str) -> dict:
    """Is this owner eligible to receive `asset_type_id` again today?

    Returns {eligible, last_acquired, cooldown_until, reason, asset_type_name}.
    An ineligible result is a FLAG for the District Office, not a hard block — the
    caller decides whether to require an override justification.
    """
    at = db.query(AssetType).filter(AssetType.id == asset_type_id).first()
    if not at:
        return {"eligible": True, "last_acquired": None, "cooldown_until": None,
                "reason": None, "asset_type_name": None}

    last_acquired = db.query(func.max(AssetInstance.acquisition_date)).filter(
        AssetInstance.owner_type == owner_type,
        AssetInstance.owner_id == owner_id,
        AssetInstance.asset_type_id == asset_type_id,
        AssetInstance.status != "DECOMMISSIONED",
    ).scalar()

    if not last_acquired or not at.useful_life_years:
        return {"eligible": True, "last_acquired": last_acquired, "cooldown_until": None,
                "reason": None, "asset_type_name": at.name}

    cooldown_until = add_years(last_acquired, at.useful_life_years)
    if date.today() < cooldown_until:
        return {
            "eligible": False,
            "last_acquired": last_acquired,
            "cooldown_until": cooldown_until,
            "reason": (f"{at.name} already acquired on {last_acquired.isoformat()}; "
                       f"useful life of {at.useful_life_years} years runs until {cooldown_until.isoformat()}"),
            "asset_type_name": at.name,
        }
    return {"eligible": True, "last_acquired": last_acquired, "cooldown_until": None,
            "reason": None, "asset_type_name": at.name}


def resolve_owner_for_asset(db: Session, asset_type: AssetType, beneficiary_type: str,
                            farmer_id: Optional[str], fig_id: Optional[str]) -> tuple[str, str]:
    """Decide who owns a scheme-granted asset, from the asset type's ownership level.

    INDIVIDUAL -> the farmer. FIG -> the FIG (for a farmer beneficiary, their active FIG).
    EITHER     -> whoever the beneficiary actually is.
    Raises ValueError with a user-facing message when it cannot be resolved.
    """
    level = asset_type.ownership_level

    if level == "EITHER":
        level = "FIG" if beneficiary_type == "FIG" else "INDIVIDUAL"

    if level == "INDIVIDUAL":
        if not farmer_id:
            raise ValueError(f"'{asset_type.name}' is an individually-owned asset, so it needs a farmer beneficiary")
        return "FARMER", farmer_id

    # FIG-owned
    if fig_id:
        return "FIG", fig_id
    if not farmer_id:
        raise ValueError(f"'{asset_type.name}' is a FIG-owned asset, so it needs a FIG beneficiary")
    membership = db.query(FigMember).filter(
        FigMember.farmer_id == farmer_id, FigMember.is_active).first()
    if not membership:
        raise ValueError(f"'{asset_type.name}' is a FIG-owned asset, but this farmer is not in an active FIG")
    return "FIG", membership.fig_id


def asset_report_rows(rows: list[AssetInstance], db: Session) -> list[dict]:
    """Flat, export-and-table-shaped rows for the Asset Management table + export — shared
    by routers/assets.py (list_assets) and routers/reports.py (export dispatcher's "assets"
    branch). `rows` must already be materialized in the desired order (and already
    paginated, if applicable) — this only shapes rows, it never queries/orders/limits
    `AssetInstance` itself."""
    types = {t.id: t for t in db.query(AssetType).all()}
    farmer_ids = [r.owner_id for r in rows if r.owner_type == "FARMER"]
    fig_ids = [r.owner_id for r in rows if r.owner_type == "FIG"]
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    figs = {g.id: g for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}
    district_names = {d.id: d.district_name for d in db.query(District).all()}
    circle_names = {c.id: c.circle_name for c in db.query(SericultureCircle).all()}
    scheme_ids = [r.scheme_id for r in rows if r.scheme_id]
    scheme_names = {s.id: s.scheme_name for s in db.query(Scheme).filter(Scheme.id.in_(scheme_ids or [""])).all()}
    verifier_ids = list({r.last_verified_by for r in rows if r.last_verified_by})
    verifiers = {u.id: (u.name or u.mobile_no)
                 for u in db.query(User).filter(User.id.in_(verifier_ids or [""])).all()}

    out = []
    for r in rows:
        at = types.get(r.asset_type_id)
        if r.owner_type == "FARMER":
            owner = farmers.get(r.owner_id)
            owner_code = owner.farmer_code if owner else None
            owner_name = f"{owner.first_name} {owner.last_name}".strip() if owner else None
            district_id = owner.district_id if owner else None
            circle_id = owner.seri_circle_id if owner else None
        else:
            owner = figs.get(r.owner_id)
            owner_code = owner.fig_code if owner else None
            owner_name = owner.fig_name if owner else None
            district_id = owner.district_id if owner else None
            circle_id = owner.seri_circle_id if owner else None

        age_left_days = None
        if at and at.useful_life_years and r.acquisition_date:
            cooldown_until = add_years(r.acquisition_date, at.useful_life_years)
            age_left_days = (cooldown_until - date.today()).days

        out.append({
            "id": r.id,
            "asset_code": r.asset_code,
            "asset_type_name": at.name if at else None,
            "quantity": r.quantity,
            "owner_type": r.owner_type,
            "owner_code": owner_code,
            "owner_name": owner_name,
            "acquisition_date": r.acquisition_date,
            "age_left_days": age_left_days,
            "acquisition_mode": r.acquisition_mode,
            "scheme_name": scheme_names.get(r.scheme_id),
            "confidence": r.confidence,
            "district_name": district_names.get(district_id),
            "circle_name": circle_names.get(circle_id),
            "gps_status": r.gps_status,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "gps_failure_reason": r.gps_failure_reason,
            "verification_status": r.verification_status,
            "last_verified_by_name": verifiers.get(r.last_verified_by) if r.last_verified_by else None,
            "photo_path": r.photo_path,
            "status": r.status,
            "remarks": r.remarks,
        })
    return out
