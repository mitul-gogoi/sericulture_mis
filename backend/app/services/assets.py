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

from app.models import AssetInstance, AssetType, FigMember


def add_years(d: date, years: int) -> date:
    """Year arithmetic that survives Feb 29 (no external dateutil dependency)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


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
