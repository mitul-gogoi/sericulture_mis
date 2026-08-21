"""District, sub-division/CDC, sericulture-circle, directorate-office, and FIG-settings
master data — read (public) + State-Admin-only CRUD."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.core.db import get_session, commit_or_conflict, delete_or_conflict
from app.core.deps import get_current_user
from app.models import District, SericultureCircle, SubdivisionCdc, DirectorateOffice, FigSettings, User, Designation
from ._common import _SA, _q, _get_or_404, ActiveToggleIn

router = APIRouter()


# ---------- Read endpoints (public to any authenticated user through downstream deps) ----------
@router.get("/districts")
def list_districts(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, District, all).order_by(District.district_name).all()


@router.get("/sericulture-circles")
def list_circles(district_id: Optional[str] = None, all: bool = False, db: Session = Depends(get_session)):
    q = _q(db, SericultureCircle, all)
    if district_id:
        q = q.filter(SericultureCircle.district_id == district_id)
    return q.order_by(SericultureCircle.circle_name).all()


@router.get("/subdivision-cdc")
def list_subdivision_cdc(district_id: Optional[str] = None, all: bool = False, db: Session = Depends(get_session)):
    q = _q(db, SubdivisionCdc, all)
    if district_id:
        q = q.filter(SubdivisionCdc.district_id == district_id)
    return q.order_by(SubdivisionCdc.office_name).all()


@router.get("/directorate-office")
def get_directorate_office(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    row = db.query(DirectorateOffice).first()
    if not row:
        raise HTTPException(404, "Directorate office not configured")
    return row


@router.get("/fig-settings")
def get_fig_settings(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    row = db.query(FigSettings).first()
    if not row:
        raise HTTPException(404, "FIG settings not configured")
    return row


# =====================================================================================
# SA-only CRUD (create / update / activate-deactivate)
# =====================================================================================
class DistrictIn(BaseModel):
    district_name: str = Field(min_length=1, max_length=80)
    state_name: str = "Assam"
    is_active: Optional[bool] = None
    office_name: Optional[str] = None
    office_address: Optional[str] = None
    office_contact_no: Optional[str] = None
    officer_in_charge_name: Optional[str] = None


class CircleIn(BaseModel):
    circle_name: str = Field(min_length=1, max_length=80)
    district_id: str
    subdivision_cdc_id: Optional[str] = None
    is_active: Optional[bool] = None
    office_name: Optional[str] = None
    office_address: Optional[str] = None
    office_contact_no: Optional[str] = None
    officer_in_charge_name: Optional[str] = None


class SubdivisionCdcIn(BaseModel):
    office_type: str = Field(pattern="^(Sub-division Office|CDC)$")
    office_name: str = Field(min_length=1, max_length=160)
    district_id: str
    is_active: Optional[bool] = None
    office_address: Optional[str] = None
    office_contact_no: Optional[str] = None
    officer_in_charge_name: Optional[str] = None


class DirectorateOfficeIn(BaseModel):
    office_name: str = Field(min_length=1, max_length=160)
    office_address: Optional[str] = None
    office_contact_no: Optional[str] = None
    officer_in_charge_name: Optional[str] = None


class FigSettingsIn(BaseModel):
    min_members: int = Field(ge=1)


# ---------- Districts ----------
@router.post("/districts")
def create_district(body: DistrictIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    d = District(district_name=body.district_name.strip(),
                 state_name=body.state_name.strip() or "Assam",
                 is_active=True if body.is_active is None else body.is_active,
                 office_name=body.office_name, office_address=body.office_address,
                 office_contact_no=body.office_contact_no, officer_in_charge_name=body.officer_in_charge_name)
    db.add(d)
    commit_or_conflict(db, "District name already exists")
    db.refresh(d)
    return d


@router.patch("/districts/{district_id}")
def update_district(district_id: str, body: DistrictIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    d = _get_or_404(db, District, district_id, "District")
    d.district_name = body.district_name.strip()
    d.state_name = body.state_name.strip() or "Assam"
    d.office_name = body.office_name
    d.office_address = body.office_address
    d.office_contact_no = body.office_contact_no
    d.officer_in_charge_name = body.officer_in_charge_name
    if body.is_active is not None:
        d.is_active = body.is_active
    commit_or_conflict(db, "District name already exists")
    db.refresh(d)
    return d


@router.patch("/districts/{district_id}/active")
def toggle_district(district_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    d = _get_or_404(db, District, district_id, "District")
    d.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": d.is_active}


@router.delete("/districts/{district_id}")
def delete_district(district_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    d = _get_or_404(db, District, district_id, "District")
    if d.is_active:
        raise HTTPException(400, "Deactivate this district before deleting it")
    delete_or_conflict(db, d, "Cannot delete — one or more sericulture circles, farmers, FIGs, users, scheme allocations, beneficiaries, or training requests still reference this district")
    return {"ok": True}


# ---------- Sub-division/CDC ----------
@router.post("/subdivision-cdc")
def create_subdivision_cdc(body: SubdivisionCdcIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, District, body.district_id, "District")
    s = SubdivisionCdc(office_type=body.office_type, office_name=body.office_name.strip(),
                       district_id=body.district_id,
                       is_active=True if body.is_active is None else body.is_active,
                       office_address=body.office_address, office_contact_no=body.office_contact_no,
                       officer_in_charge_name=body.officer_in_charge_name)
    db.add(s)
    commit_or_conflict(db, "Sub-division/CDC office already exists in this district")
    db.refresh(s)
    return s


@router.patch("/subdivision-cdc/{subdivision_cdc_id}")
def update_subdivision_cdc(subdivision_cdc_id: str, body: SubdivisionCdcIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = _get_or_404(db, SubdivisionCdc, subdivision_cdc_id, "Sub-division/CDC office")
    _get_or_404(db, District, body.district_id, "District")
    s.office_type = body.office_type
    s.office_name = body.office_name.strip()
    s.district_id = body.district_id
    s.office_address = body.office_address
    s.office_contact_no = body.office_contact_no
    s.officer_in_charge_name = body.officer_in_charge_name
    if body.is_active is not None:
        s.is_active = body.is_active
    commit_or_conflict(db, "Sub-division/CDC office already exists in this district")
    db.refresh(s)
    return s


@router.patch("/subdivision-cdc/{subdivision_cdc_id}/active")
def toggle_subdivision_cdc(subdivision_cdc_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = _get_or_404(db, SubdivisionCdc, subdivision_cdc_id, "Sub-division/CDC office")
    s.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": s.is_active}


@router.delete("/subdivision-cdc/{subdivision_cdc_id}")
def delete_subdivision_cdc(subdivision_cdc_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    s = _get_or_404(db, SubdivisionCdc, subdivision_cdc_id, "Sub-division/CDC office")
    if s.is_active:
        raise HTTPException(400, "Deactivate this Sub-division/CDC office before deleting it")
    delete_or_conflict(db, s, "Cannot delete — one or more sericulture circles still reference this Sub-division/CDC office")
    return {"ok": True}


# ---------- Sericulture Circles ----------
@router.post("/sericulture-circles")
def create_circle(body: CircleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    _get_or_404(db, District, body.district_id, "District")
    if body.subdivision_cdc_id:
        sc = _get_or_404(db, SubdivisionCdc, body.subdivision_cdc_id, "Sub-division/CDC office")
        if sc.district_id != body.district_id:
            raise HTTPException(400, "Selected Sub-division/CDC office does not belong to this district")
    c = SericultureCircle(circle_name=body.circle_name.strip(), district_id=body.district_id,
                          subdivision_cdc_id=body.subdivision_cdc_id,
                          is_active=True if body.is_active is None else body.is_active,
                          office_name=body.office_name, office_address=body.office_address,
                          office_contact_no=body.office_contact_no, officer_in_charge_name=body.officer_in_charge_name)
    db.add(c)
    commit_or_conflict(db, "Sericulture Circle already exists in this district")
    db.refresh(c)
    return c


@router.patch("/sericulture-circles/{circle_id}")
def update_circle(circle_id: str, body: CircleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, SericultureCircle, circle_id, "Sericulture Circle")
    _get_or_404(db, District, body.district_id, "District")
    if body.subdivision_cdc_id:
        sc = _get_or_404(db, SubdivisionCdc, body.subdivision_cdc_id, "Sub-division/CDC office")
        if sc.district_id != body.district_id:
            raise HTTPException(400, "Selected Sub-division/CDC office does not belong to this district")
    c.circle_name = body.circle_name.strip()
    c.district_id = body.district_id
    c.subdivision_cdc_id = body.subdivision_cdc_id
    c.office_name = body.office_name
    c.office_address = body.office_address
    c.office_contact_no = body.office_contact_no
    c.officer_in_charge_name = body.officer_in_charge_name
    if body.is_active is not None:
        c.is_active = body.is_active
    commit_or_conflict(db, "Sericulture Circle already exists in this district")
    db.refresh(c)
    return c


@router.patch("/sericulture-circles/{circle_id}/active")
def toggle_circle(circle_id: str, body: ActiveToggleIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, SericultureCircle, circle_id, "Sericulture Circle")
    c.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": c.is_active}


@router.delete("/sericulture-circles/{circle_id}")
def delete_circle(circle_id: str, user: User = Depends(_SA), db: Session = Depends(get_session)):
    c = _get_or_404(db, SericultureCircle, circle_id, "Sericulture Circle")
    if c.is_active:
        raise HTTPException(400, "Deactivate this sericulture circle before deleting it")
    delete_or_conflict(db, c, "Cannot delete — one or more farmers or FIGs still reference this sericulture circle")
    return {"ok": True}


# ---------- Directorate Office (state-level singleton) ----------
@router.patch("/directorate-office")
def update_directorate_office(body: DirectorateOfficeIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    row = db.query(DirectorateOffice).first()
    if not row:
        row = DirectorateOffice(office_name=body.office_name)
        db.add(row)
    row.office_name = body.office_name.strip()
    row.office_address = body.office_address
    row.office_contact_no = body.office_contact_no
    row.officer_in_charge_name = body.officer_in_charge_name
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


# ---------- FIG Settings (state-level singleton) ----------
@router.patch("/fig-settings")
def update_fig_settings(body: FigSettingsIn, user: User = Depends(_SA), db: Session = Depends(get_session)):
    row = db.query(FigSettings).first()
    if not row:
        row = FigSettings(min_members=body.min_members)
        db.add(row)
    else:
        row.min_members = body.min_members
        row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


# ---------- Designations ----------
# Departmental posts held by officer accounts (State / District Admin). Ordered by
# display_order so the hierarchy reads correctly; alphabetical would list "Assistant
# Director" above "Director".
class DesignationIn(BaseModel):
    designation_name: str = Field(min_length=1, max_length=120)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/designations")
def list_designations(all: bool = False, db: Session = Depends(get_session)):
    return _q(db, Designation, all).order_by(
        Designation.display_order, Designation.designation_name).all()


@router.post("/designations")
def create_designation(body: DesignationIn, user: User = Depends(_SA),
                       db: Session = Depends(get_session)):
    d = Designation(designation_name=body.designation_name.strip(),
                    display_order=body.display_order or 0,
                    is_active=True if body.is_active is None else body.is_active)
    db.add(d)
    commit_or_conflict(db, "Designation already exists")
    db.refresh(d)
    return d


@router.patch("/designations/{designation_id}")
def update_designation(designation_id: str, body: DesignationIn, user: User = Depends(_SA),
                       db: Session = Depends(get_session)):
    d = _get_or_404(db, Designation, designation_id, "Designation")
    d.designation_name = body.designation_name.strip()
    if body.display_order is not None:
        d.display_order = body.display_order
    if body.is_active is not None:
        d.is_active = body.is_active
    commit_or_conflict(db, "Designation already exists")
    db.refresh(d)
    return d


@router.patch("/designations/{designation_id}/active")
def toggle_designation(designation_id: str, body: ActiveToggleIn, user: User = Depends(_SA),
                       db: Session = Depends(get_session)):
    d = _get_or_404(db, Designation, designation_id, "Designation")
    d.is_active = body.is_active
    db.commit()
    return {"ok": True, "is_active": d.is_active}


@router.delete("/designations/{designation_id}")
def delete_designation(designation_id: str, user: User = Depends(_SA),
                       db: Session = Depends(get_session)):
    d = _get_or_404(db, Designation, designation_id, "Designation")
    if d.is_active:
        raise HTTPException(400, "Deactivate this designation before deleting it")
    delete_or_conflict(db, d, "Cannot delete — one or more users still hold this designation")
    return {"ok": True}
