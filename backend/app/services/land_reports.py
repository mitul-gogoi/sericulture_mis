"""Row-shaping helper for Land & GIS / GPS Verification's paginated table and Excel/PDF
export — shared by routers/lands.py (list_lands) and routers/reports.py (export
dispatcher's "lands" branch)."""
from sqlalchemy.orm import Session
from app.models import Land, Farmer, District, SericultureCircle


def land_report_rows(rows: list[Land], db: Session) -> list[dict]:
    """Flat, export-and-table-shaped rows covering every field the Land & GIS table and
    export need: dag/patta, farmer identity, area in both units, and the farmer's
    village/panchayat/block/district/circle. `rows` must already be materialized in the
    desired order (and already paginated, if applicable) — this only shapes rows, it
    never queries/orders/limits `Land` itself, so it's equally correct for a paginated
    on-screen slice and a full unpaginated export dump."""
    farmer_ids = list({r.farmer_id for r in rows})
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    district_names = {d.id: d.district_name for d in db.query(District).all()}
    circle_names = {c.id: c.circle_name for c in db.query(SericultureCircle).all()}

    out = []
    for r in rows:
        f = farmers.get(r.farmer_id)
        out.append({
            "id": r.id,
            "farmer_id": r.farmer_id,
            "dag_no": r.dag_no,
            "patta_no": r.patta_no,
            "farmer_code": f.farmer_code if f else None,
            "farmer_name": " ".join(filter(None, [f.first_name, f.last_name])) if f else None,
            "land_area_bigha": r.land_area_bigha,
            "land_area_hectare": r.land_area_hectare,
            "village_name": f.village_name if f else None,
            "gaon_panchayat": f.gaon_panchayat if f else None,
            "development_block": f.development_block if f else None,
            "district_name": district_names.get(f.district_id) if f else None,
            "circle_name": circle_names.get(f.seri_circle_id) if f else None,
            "gps_verified": r.gps_verified,
            "gps_points": r.gps_points,
            "overlap_detected": r.overlap_detected,
            "overlapping_parcel_ids": r.overlapping_parcel_ids,
            "failure_reason": r.failure_reason,
            "verified_at": r.verified_at,
            "created_at": r.created_at,
        })
    return out
