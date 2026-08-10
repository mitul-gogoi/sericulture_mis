"""FIGs and members."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.security import hash_password, DEFAULT_FARMER_PASSWORD
from app.core.deps import get_current_user, require_roles
from datetime import date
from app.models import Fig, FigMember, Farmer, User, SilkTypeActivityProduct, FigSettings, AssetType, AssetInstance
from app.schemas import FigIn, FigMemberIn, PresidentSetIn, FigUpdateIn
from app.services.fig_reports import apply_fig_filters, member_names_by_fig
from app.services.assets import next_asset_seq, asset_code

_PAGE_SIZES = {10, 20, 50, 100}

router = APIRouter(prefix="/figs", tags=["figs"])


class ActiveToggleIn(BaseModel):
    is_active: bool


def _gcode(seq: int) -> str:
    return f"SERI-FIG-{seq:05d}"


def _next_fig_seq(db: Session) -> int:
    # Codes must be >= 10001 and never end in 0.
    max_num = 10000
    for (code,) in db.query(Fig.fig_code).all():
        try:
            num = int(code.rsplit("-", 1)[-1])
        except (ValueError, AttributeError):
            continue
        max_num = max(max_num, num)
    candidate = max_num + 1
    while candidate % 10 == 0:
        candidate += 1
    return candidate


def _require_output_stap(db: Session, stap_id: str) -> None:
    stap = db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id == stap_id).first()
    if not stap or stap.role != "OUTPUT":
        raise HTTPException(400, "A FIG's production stage must be an output stage, not an input")


@router.post("")
def create_fig(body: FigIn, user: User = Depends(require_roles("DISTRICT_ADMIN")),
               db: Session = Depends(get_session)):
    if user.role == "DISTRICT_ADMIN" and body.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    _require_output_stap(db, body.stap_id)
    settings = db.query(FigSettings).first()
    min_members = settings.min_members if settings else 1
    if len(body.member_ids) < min_members:
        raise HTTPException(400, f"At least {min_members} member(s) required to register a FIG")
    dupes = db.query(FigMember).filter(FigMember.farmer_id.in_(body.member_ids), FigMember.is_active).all()
    if dupes:
        raise HTTPException(400, "One or more selected farmers are already in an active FIG")
    # Self-declared assets are an eligibility-screening snapshot, so they must reference a real
    # catalog entry — but an individually-owned asset type can never be declared for a FIG.
    asset_types = {}
    if body.assets:
        asset_types = {t.id: t for t in db.query(AssetType).filter(
            AssetType.id.in_([a.asset_type_id for a in body.assets])).all()}
        for asset in body.assets:
            at = asset_types.get(asset.asset_type_id)
            if not at:
                raise HTTPException(400, f"Unknown asset type: {asset.asset_type_id}")
            if at.ownership_level == "INDIVIDUAL":
                raise HTTPException(400, f"'{at.name}' is an individually-owned asset — it cannot be declared for a FIG")

    seq = _next_fig_seq(db)
    data = body.model_dump()
    data.pop("member_ids")
    asset_rows = data.pop("assets")
    fig = Fig(fig_code=_gcode(seq), **data)
    db.add(fig)
    db.flush()  # assign fig.id before creating members/assets, same transaction
    for farmer_id in body.member_ids:
        db.add(FigMember(fig_id=fig.id, farmer_id=farmer_id))
    for asset in asset_rows:
        year = asset.get("acquisition_year")
        db.add(AssetInstance(
            asset_code=asset_code(next_asset_seq(db)),
            asset_type_id=asset["asset_type_id"], owner_type="FIG", owner_id=fig.id,
            quantity=asset.get("quantity") or 1,
            acquisition_date=date(year, 1, 1) if year else None,
            acquisition_mode="SELF_DECLARED_AT_REGISTRATION",
            confidence="FARMER_SELF_DECLARED", created_by_user_id=user.id,
        ))
    db.commit()
    db.refresh(fig)
    return {"id": fig.id, "fig_code": fig.fig_code}


@router.get("")
def list_figs(
    q: Optional[str] = None,
    district_id: Optional[str] = None,
    seri_circle_id: Optional[str] = None,
    stap_id: Optional[str] = None,
    formation_date_from: Optional[str] = None,
    formation_date_to: Optional[str] = None,
    is_active: Optional[bool] = None,
    all: bool = False,
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_session),
):
    query = db.query(Fig)
    if not all:
        query = query.filter(Fig.is_active)
    if user.role == "DISTRICT_ADMIN":
        query = query.filter(Fig.district_id == user.district_id)
    elif user.role == "FIG_PRESIDENT":
        query = query.filter(Fig.id == user.fig_id)
    elif district_id:
        query = query.filter(Fig.district_id == district_id)
    if seri_circle_id:
        query = query.filter(Fig.seri_circle_id == seri_circle_id)
    if q:
        like = f"%{q}%"
        member_match = db.query(FigMember.fig_id).join(Farmer, Farmer.id == FigMember.farmer_id).filter(
            FigMember.is_active,
            or_(Farmer.farmer_code.ilike(like), Farmer.mobile_no.like(like),
                Farmer.first_name.ilike(like), Farmer.last_name.ilike(like)),
        ).scalar_subquery()
        query = query.filter(or_(Fig.fig_code.ilike(like), Fig.fig_name.ilike(like), Fig.id.in_(member_match)))
    query = apply_fig_filters(query, stap_id=stap_id, formation_date_from=formation_date_from,
                              formation_date_to=formation_date_to, is_active=is_active)
    query = query.order_by(Fig.created_at.desc())

    def _rows_with_members(figs: list[Fig]) -> list[dict]:
        fig_ids = [f.id for f in figs]
        counts = dict(db.query(FigMember.fig_id, func.count(FigMember.id)).filter(
            FigMember.fig_id.in_(fig_ids or [""]), FigMember.is_active).group_by(FigMember.fig_id).all())
        names = member_names_by_fig(fig_ids, db)
        out = []
        for f in figs:
            d = f.model_dump()
            d["total_members"] = counts.get(f.id, 0)
            d["member_names"] = names.get(f.id, [])
            out.append(d)
        return out

    # Only opt-in via `page` triggers the new paginated {items,total} shape; omitting it
    # preserves the exact legacy flat-array contract relied on by meetings/page.tsx and
    # users/fig-presidents/page.tsx, neither of which ever pass `page`.
    if page is None:
        return _rows_with_members(query.all())
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    return {"items": _rows_with_members(rows), "total": total}


@router.get("/{fig_id}")
def get_fig(fig_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    f = db.query(Fig).filter(Fig.id == fig_id).first()
    if not f:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and f.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if user.role == "FIG_PRESIDENT" and f.id != user.fig_id:
        raise HTTPException(403, "FIG scope mismatch")
    members = db.query(FigMember).filter(FigMember.fig_id == fig_id, FigMember.is_active).all()
    farmer_ids = [m.farmer_id for m in members]
    farmers = {fr.id: fr for fr in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    data = f.model_dump()
    data["total_members"] = len(members)
    data["members"] = [{
        "id": m.id, "fig_id": m.fig_id, "farmer_id": m.farmer_id, "role": m.role,
        "is_active": m.is_active, "farmer": (farmers.get(m.farmer_id).model_dump() if farmers.get(m.farmer_id) else None),
    } for m in members]
    return data


@router.patch("/{fig_id}")
def update_fig(fig_id: str, body: FigUpdateIn,
               user: User = Depends(require_roles("DISTRICT_ADMIN")),
               db: Session = Depends(get_session)):
    fig = db.query(Fig).filter(Fig.id == fig_id).first()
    if not fig:
        raise HTTPException(404, "Not found")
    if fig.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if body.stap_id is not None:
        _require_output_stap(db, body.stap_id)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(fig, k, v)
    fig.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(fig)
    return fig


@router.patch("/{fig_id}/active")
def toggle_fig(fig_id: str, body: ActiveToggleIn,
               user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
               db: Session = Depends(get_session)):
    fig = db.query(Fig).filter(Fig.id == fig_id).first()
    if not fig:
        raise HTTPException(404, "Not found")
    if user.role == "DISTRICT_ADMIN" and fig.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    fig.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": fig.is_active}


@router.post("/members")
def add_member(body: FigMemberIn, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
               db: Session = Depends(get_session)):
    fig = db.query(Fig).filter(Fig.id == body.fig_id).first()
    if not fig:
        raise HTTPException(404, "FIG not found")
    if user.role == "DISTRICT_ADMIN" and fig.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if db.query(FigMember).filter(FigMember.farmer_id == body.farmer_id, FigMember.is_active).first():
        raise HTTPException(400, "Farmer already in an active FIG")
    db.add(FigMember(fig_id=body.fig_id, farmer_id=body.farmer_id, role=body.role))
    db.commit()
    return {"ok": True}


@router.delete("/members/{member_id}")
def remove_member(member_id: str, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    m = db.query(FigMember).filter(FigMember.id == member_id).first()
    if not m:
        raise HTTPException(404, "Not found")
    m.is_active = False
    m.exit_date = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/president")
def set_president(body: PresidentSetIn, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                  db: Session = Depends(get_session)):
    fig = db.query(Fig).filter(Fig.id == body.fig_id).first()
    if not fig:
        raise HTTPException(404, "FIG not found")
    if user.role == "DISTRICT_ADMIN" and fig.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    # Demote existing presidents — both the FigMember role flag and, since a FIG President's
    # login is just their own farmer account promoted in place (not a separate account), the
    # linked User row too, so an outgoing president loses elevated access but keeps their own
    # login (mobile/password untouched).
    for m in db.query(FigMember).filter(FigMember.fig_id == body.fig_id, FigMember.role == "President", FigMember.is_active).all():
        m.role = "Member"
        outgoing_login = db.query(User).filter(
            User.role == "FIG_PRESIDENT", User.fig_id == body.fig_id, User.farmer_id == m.farmer_id).first()
        if outgoing_login:
            outgoing_login.role = "FARMER"
            outgoing_login.fig_id = None
    # Promote selected member
    member = db.query(FigMember).filter(FigMember.fig_id == body.fig_id, FigMember.farmer_id == body.farmer_id, FigMember.is_active).first()
    if not member:
        raise HTTPException(400, "Farmer is not an active member of this FIG")
    member.role = "President"
    # Promote the farmer's own existing login in place — never a separate account/password.
    farmer = db.query(Farmer).filter(Farmer.id == body.farmer_id).first()
    president_name = f"{farmer.first_name} {farmer.last_name}".strip() if farmer else None
    login = db.query(User).filter(User.farmer_id == body.farmer_id).first()
    if login:
        login.role = "FIG_PRESIDENT"
        login.fig_id = body.fig_id
        login.district_id = fig.district_id
        login.name = president_name
    else:
        # Defensive fallback only — every farmer should already have a login (auto-provisioned
        # at registration, or via the one-off backfill script), but don't hard-fail if one
        # somehow doesn't exist yet.
        db.add(User(mobile_no=farmer.mobile_no, password_hash=hash_password(DEFAULT_FARMER_PASSWORD),
                    role="FIG_PRESIDENT", farmer_id=body.farmer_id, fig_id=body.fig_id,
                    district_id=fig.district_id, name=president_name))
    db.commit()
    return {"ok": True}
