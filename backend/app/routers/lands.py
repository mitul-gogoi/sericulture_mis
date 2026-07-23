"""Land parcels + GPS submission + verification (uses PostGIS for overlap)."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from geoalchemy2.shape import to_shape
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models import Land, Farmer, User, FigMember
from app.schemas import LandIn, GpsSubmitIn, GpsVerifyIn
from app.services.geo import polygon_area_sqm, points_to_wkt, MIN_GPS_POINTS

router = APIRouter(prefix="/lands", tags=["lands"])

BIGHA_SQM = 2400.0
VALID_LAND_TYPES = {"Owned", "Leased", "Community", "Government", "Forest"}


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
               user: User = Depends(get_current_user), db: Session = Depends(get_session)):
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
    lands = q.order_by(Land.created_at.desc()).limit(500).all()
    farmer_ids = list({ld.farmer_id for ld in lands})
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    return [_serialize_land(ld, farmers.get(ld.farmer_id)) for ld in lands]


@router.post("/gps")
def submit_gps(body: GpsSubmitIn, user: User = Depends(require_roles("FIG_PRESIDENT", "DISTRICT_ADMIN", "STATE_ADMIN")),
               db: Session = Depends(get_session)):
    if len(body.points) < MIN_GPS_POINTS:
        raise HTTPException(400, f"Minimum {MIN_GPS_POINTS} GPS points required")
    land = db.query(Land).filter(Land.id == body.farmer_land_id).first()
    if not land:
        raise HTTPException(404, "Land not found")
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
    db.commit()
    return {
        "area_sqm": area_sqm, "area_bigha": land.land_area_bigha,
        "area_hectare": land.land_area_hectare,
        "overlap_detected": land.overlap_detected,
        "overlapping_parcel_ids": overlap_ids,
    }


@router.post("/verify")
def verify_gps(body: GpsVerifyIn, user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
               db: Session = Depends(get_session)):
    land = db.query(Land).filter(Land.id == body.farmer_land_id).first()
    if not land:
        raise HTTPException(404, "Not found")
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
