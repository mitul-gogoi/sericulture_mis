"""Land parcels + GPS submission + verification (uses PostGIS for overlap)."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from geoalchemy2.shape import to_shape
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models import Land, Farmer, User, FigMember, LandGpsDraft
from app.schemas import LandIn, GpsSubmitIn, GpsVerifyIn, LandGpsDraftIn
from app.services.geo import polygon_area_sqm, points_to_wkt, MIN_GPS_POINTS
from app.services.land_reports import land_report_rows

router = APIRouter(prefix="/lands", tags=["lands"])

BIGHA_SQM = 2400.0
VALID_LAND_TYPES = {"Owned", "Leased", "Community", "Government", "Forest"}
_PAGE_SIZES = {10, 20, 50, 100}


def _serialize_land(land: Land, farmer: Optional[Farmer] = None) -> dict:
    d = {
        "id": land.id, "farmer_id": land.farmer_id, "dag_no": land.dag_no, "patta_no": land.patta_no,
        "land_type": land.land_type, "land_area_sqm": land.land_area_sqm,
        "land_area_bigha": land.land_area_bigha, "land_area_hectare": land.land_area_hectare,
        "gps_verified": land.gps_verified, "gps_points": land.gps_points,
        "overlap_detected": land.overlap_detected, "overlapping_parcel_ids": land.overlapping_parcel_ids,
        "failure_reason": land.failure_reason, "verified_at": land.verified_at,
        "created_at": land.created_at,
    }
    if farmer:
        d["farmer"] = {"id": farmer.id, "first_name": farmer.first_name,
                       "last_name": farmer.last_name, "farmer_code": farmer.farmer_code,
                       "mobile_no": farmer.mobile_no}
    return d


def _active_fig_member(db: Session, farmer_id: str) -> Optional[FigMember]:
    return db.query(FigMember).filter(
        FigMember.farmer_id == farmer_id, FigMember.is_active).first()


def _assert_land_gps_submit_scope(db: Session, user: User, land: Land) -> None:
    """Closes a pre-existing gap: submit_gps used to accept any land_id from any
    FIG_PRESIDENT/DISTRICT_ADMIN/STATE_ADMIN with no ownership check at all. Also adds the
    new FARMER case (solo only — FIG members must use the draft endpoint instead)."""
    if user.role == "STATE_ADMIN":
        return
    if user.role == "FARMER":
        if land.farmer_id != user.farmer_id:
            raise HTTPException(403, "Out of scope")
        if _active_fig_member(db, user.farmer_id):
            raise HTTPException(400, "You have an active FIG — save this as a draft for your FIG President instead of submitting directly")
        return
    if user.role == "FIG_PRESIDENT":
        member = db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.farmer_id == land.farmer_id, FigMember.is_active).first()
        if not member:
            raise HTTPException(403, "Out of scope")
        return
    if user.role == "DISTRICT_ADMIN":
        farmer = db.query(Farmer).filter(Farmer.id == land.farmer_id).first()
        if not farmer or farmer.district_id != user.district_id:
            raise HTTPException(403, "District scope mismatch")
        return
    raise HTTPException(403, "Not permitted")


def _consume_land_gps_draft(db: Session, land_id: str) -> None:
    draft = db.query(LandGpsDraft).filter(LandGpsDraft.land_id == land_id).first()
    if draft:
        db.delete(draft)


@router.post("")
def create_land(body: LandIn, user: User = Depends(require_roles("DISTRICT_ADMIN")),
                db: Session = Depends(get_session)):
    farmer = db.query(Farmer).filter(Farmer.id == body.farmer_id).first()
    if not farmer:
        raise HTTPException(404, "Farmer not found")
    if farmer.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if body.land_type not in VALID_LAND_TYPES:
        raise HTTPException(400, f"Invalid land_type: {body.land_type}")
    land = Land(**body.model_dump())
    db.add(land)
    db.commit()
    db.refresh(land)
    return {"id": land.id}


@router.delete("/{land_id}")
def delete_land(land_id: str, user: User = Depends(require_roles("DISTRICT_ADMIN")),
                db: Session = Depends(get_session)):
    land = db.query(Land).filter(Land.id == land_id).first()
    if not land:
        raise HTTPException(404, "Not found")
    farmer = db.query(Farmer).filter(Farmer.id == land.farmer_id).first()
    if not farmer or farmer.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if land.gps_verified != "Not Submitted":
        raise HTTPException(400, "Cannot delete a land parcel with GPS data already submitted")
    db.delete(land)
    db.commit()
    return {"ok": True}


@router.get("")
def list_lands(farmer_id: Optional[str] = None, status: Optional[str] = None,
               page: Optional[int] = Query(None, ge=1), page_size: Optional[int] = None,
               user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if user.role == "FARMER":
        farmer_id = user.farmer_id
    q = db.query(Land)
    if farmer_id:
        q = q.filter(Land.farmer_id == farmer_id)
    if status:
        q = q.filter(Land.gps_verified == status)
    if user.role == "DISTRICT_ADMIN":
        farmer_ids = [f.id for f in db.query(Farmer).filter(Farmer.district_id == user.district_id).all()]
        q = q.filter(Land.farmer_id.in_(farmer_ids or [""]))
    elif user.role == "FIG_PRESIDENT":
        member_ids = [m.farmer_id for m in db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.is_active).all()]
        q = q.filter(Land.farmer_id.in_(member_ids or [""]))
    q = q.order_by(Land.created_at.desc())

    # Only opt-in via `page` triggers the new paginated {items,total} shape; omitting it
    # preserves the exact legacy flat-array contract, matching farmers.py's own convention.
    show_drafts = user.role in ("FIG_PRESIDENT", "DISTRICT_ADMIN", "STATE_ADMIN")
    if page is None:
        lands = q.limit(500).all()
        farmer_ids2 = list({ld.farmer_id for ld in lands})
        farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids2 or [""])).all()}
        draft_land_ids = set()
        if show_drafts:
            draft_land_ids = {r[0] for r in db.query(LandGpsDraft.land_id).filter(
                LandGpsDraft.land_id.in_([ld.id for ld in lands] or [""])).all()}
        out = []
        for ld in lands:
            row = _serialize_land(ld, farmers.get(ld.farmer_id))
            if show_drafts:
                row["has_gps_draft"] = ld.id in draft_land_ids
            out.append(row)
        return out
    size = page_size or 20
    if size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    total = q.count()
    # Counted against the full role-scoped query (before offset/limit) so these stay
    # state/district-wide, not silently page-scoped once pagination trims `items`.
    pending_count = q.filter(Land.gps_verified == "Pending").count()
    overlap_count = q.filter(Land.overlap_detected).count()
    page_lands = q.offset((page - 1) * size).limit(size).all()
    rows = land_report_rows(page_lands, db)
    if show_drafts:
        draft_land_ids = {r[0] for r in db.query(LandGpsDraft.land_id).filter(
            LandGpsDraft.land_id.in_([ld.id for ld in page_lands] or [""])).all()}
        for row in rows:
            row["has_gps_draft"] = row["id"] in draft_land_ids
    return {"items": rows, "total": total, "pending_count": pending_count, "overlap_count": overlap_count}


@router.post("/{land_id}/gps/draft")
def save_land_gps_draft(land_id: str, body: LandGpsDraftIn, user: User = Depends(require_roles("FARMER")),
                        db: Session = Depends(get_session)):
    land = db.query(Land).filter(Land.id == land_id).first()
    if not land:
        raise HTTPException(404, "Not found")
    if land.farmer_id != user.farmer_id:
        raise HTTPException(403, "Out of scope")
    member = _active_fig_member(db, user.farmer_id)
    if not member:
        raise HTTPException(400, "You have no active FIG — submit directly via POST /lands/gps instead")
    draft = db.query(LandGpsDraft).filter(LandGpsDraft.land_id == land_id).first()
    if draft:
        draft.points = body.points
        draft.updated_at = datetime.now(timezone.utc)
    else:
        db.add(LandGpsDraft(farmer_id=user.farmer_id, land_id=land_id, fig_id=member.fig_id, points=body.points))
    db.commit()
    return {"ok": True}


@router.get("/{land_id}/gps/draft")
def get_land_gps_draft(land_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    land = db.query(Land).filter(Land.id == land_id).first()
    if not land:
        raise HTTPException(404, "Not found")
    if user.role == "FARMER":
        if land.farmer_id != user.farmer_id:
            raise HTTPException(403, "Out of scope")
    elif user.role == "FIG_PRESIDENT":
        member = db.query(FigMember).filter(
            FigMember.fig_id == user.fig_id, FigMember.farmer_id == land.farmer_id, FigMember.is_active).first()
        if not member:
            raise HTTPException(403, "Out of scope")
    else:
        raise HTTPException(403, "Not permitted")
    draft = db.query(LandGpsDraft).filter(LandGpsDraft.land_id == land_id).first()
    if not draft:
        return None
    return {"points": draft.points, "updated_at": draft.updated_at, "farmer_id": draft.farmer_id}


@router.post("/gps")
def submit_gps(body: GpsSubmitIn, user: User = Depends(require_roles("FARMER", "FIG_PRESIDENT", "DISTRICT_ADMIN", "STATE_ADMIN")),
               db: Session = Depends(get_session)):
    if len(body.points) < MIN_GPS_POINTS:
        raise HTTPException(400, f"Minimum {MIN_GPS_POINTS} GPS points required")
    land = db.query(Land).filter(Land.id == body.farmer_land_id).first()
    if not land:
        raise HTTPException(404, "Land not found")
    _assert_land_gps_submit_scope(db, user, land)
    area_sqm = polygon_area_sqm(body.points)
    wkt = points_to_wkt(body.points)
    # PostGIS overlap check
    overlap_ids: list[str] = []
    if land.id:
        rows = db.execute(text("""
            SELECT id FROM lands
            WHERE id != :lid
              AND boundary IS NOT NULL
              AND ST_Intersects(boundary, ST_GeomFromEWKT(:wkt))
        """), {"lid": land.id, "wkt": wkt}).fetchall()
        overlap_ids = [r[0] for r in rows]
    land.land_area_sqm = area_sqm
    land.land_area_bigha = area_sqm / BIGHA_SQM
    land.land_area_hectare = area_sqm / 10000.0
    land.gps_verified = "Pending"
    land.gps_points = body.points
    land.boundary = wkt
    land.overlap_detected = len(overlap_ids) > 0
    land.overlapping_parcel_ids = overlap_ids
    land.updated_at = datetime.now(timezone.utc)
    _consume_land_gps_draft(db, land.id)
    db.commit()
    return {
        "area_sqm": area_sqm, "area_bigha": land.land_area_bigha,
        "area_hectare": land.land_area_hectare,
        "overlap_detected": land.overlap_detected,
        "overlapping_parcel_ids": overlap_ids,
    }


@router.post("/verify")
def verify_gps(body: GpsVerifyIn, user: User = Depends(require_roles("DISTRICT_ADMIN")),
               db: Session = Depends(get_session)):
    land = db.query(Land).filter(Land.id == body.farmer_land_id).first()
    if not land:
        raise HTTPException(404, "Not found")
    farmer = db.query(Farmer).filter(Farmer.id == land.farmer_id).first()
    if not farmer or farmer.district_id != user.district_id:
        raise HTTPException(403, "District scope mismatch")
    if land.overlap_detected and not body.override_overlap and body.decision == "verified":
        raise HTTPException(400, "Overlap detected — pass override_overlap=true to verify regardless")
    if body.decision == "verified":
        land.gps_verified = "Verified"
        land.failure_reason = None
    else:
        land.gps_verified = "Failed"
        land.failure_reason = body.reason
    land.verified_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
