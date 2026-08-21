"""Training requests, approvals, completions, roster/attendance, and certificate
generation/tracking.

A Training request may optionally link to a Training-support-type Scheme (scheme_id).
Once that scheme's beneficiaries have been State-Admin-approved, this module resolves
them as the training's expected attendee roster, lets the District Admin mark who
actually attended, and (once the training is Completed) generates a tracked, numbered
certificate PDF for each attendee marked present.
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models import (
    Training, User, Scheme, Beneficiary, Farmer, Fig, TrainingAttendance, TrainingCertificate, FileRecord,
)
from app.schemas import (
    TrainingRequestIn, TrainingApprovalIn, TrainingCompletionIn,
    TrainingAttendanceMarkIn, CertificateRevokeIn,
)
from app.services.scheme_targeting import scheme_targets_district
from app.services.certificates import next_certificate_number, render_certificate_pdf
from app.services.storage import put_object
from app.core.scope import active_district, assigned_district_ids

router = APIRouter(prefix="/trainings", tags=["trainings"])


def _training_or_404(db: Session, training_id: str) -> Training:
    t = db.query(Training).filter(Training.id == training_id).first()
    if not t:
        raise HTTPException(404, "Training not found")
    return t


def _beneficiary_display_name(b: Beneficiary, farmers: dict, figs: dict) -> tuple[str, str]:
    if b.farmer_id and farmers.get(b.farmer_id):
        f = farmers[b.farmer_id]
        return f"{f.first_name} {f.last_name}".strip(), f.farmer_code
    if b.fig_id and figs.get(b.fig_id):
        g = figs[b.fig_id]
        return g.fig_name, g.fig_code
    return "Unknown", ""


@router.post("/requests")
def create(body: TrainingRequestIn, user: User = Depends(require_roles("DISTRICT_ADMIN")),
           db: Session = Depends(get_session)):
    if body.scheme_id:
        scheme = db.query(Scheme).filter(Scheme.id == body.scheme_id).first()
        if not scheme:
            raise HTTPException(404, "Scheme not found")
        if scheme.support_type != "Training":
            raise HTTPException(400, "This scheme is not a Training-support-type scheme")
        if not scheme_targets_district(scheme, active_district(user)):
            raise HTTPException(400, "This scheme does not target your district")

    # An admin holding additional charge must be able to file against either district, so
    # the form sends one explicitly; fall back to whichever they are currently acting as.
    target_district = body.district_id or active_district(user)
    if not target_district:
        raise HTTPException(400, "A district is required")
    if target_district not in assigned_district_ids(db, user):
        raise HTTPException(403, "You are not assigned to that district")

    t = Training(
        topic=body.topic, description=body.description, activity_id=body.activity_id,
        scheme_id=body.scheme_id,
        proposed_from_date=body.proposed_from_date, proposed_to_date=body.proposed_to_date,
        proposed_venue=body.proposed_venue, estimated_participants=body.estimated_participants,
        participant_names=body.participant_names,
        requesting_da_id=user.id, district_id=target_district,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id}


@router.get("/requests")
def list_requests(status: Optional[str] = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    q = db.query(Training)
    if user.role == "DISTRICT_ADMIN":
        q = q.filter(Training.district_id == active_district(user))
    if status:
        q = q.filter(Training.status == status)
    return q.order_by(Training.created_at.desc()).all()


@router.post("/approve")
def approve(body: TrainingApprovalIn, user: User = Depends(require_roles("STATE_ADMIN")),
            db: Session = Depends(get_session)):
    t = db.query(Training).filter(Training.id == body.request_id).first()
    if not t:
        raise HTTPException(404, "Not found")
    if body.decision == "approved":
        t.status = "Approved"
        t.approval_from_date = body.approval_from_date
        t.approval_to_date = body.approval_to_date
        t.approved_venue = body.approved_venue
        t.approval_remarks = body.approval_remarks
    else:
        t.status = "Rejected"
        t.rejection_reason = body.rejection_reason
    t.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/complete")
def complete(body: TrainingCompletionIn, user: User = Depends(require_roles("DISTRICT_ADMIN")),
             db: Session = Depends(get_session)):
    t = db.query(Training).filter(Training.id == body.request_id, Training.status == "Approved").first()
    if not t:
        raise HTTPException(404, "Not approved/found")
    t.actual_from_date = body.actual_from_date
    t.actual_to_date = body.actual_to_date
    t.actual_venue = body.actual_venue
    t.actual_participants = body.actual_participants
    t.completion_report = body.completion_report
    t.status = "Completed"
    t.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ---------- Roster + attendance ----------
@router.get("/{training_id}/roster")
def roster(training_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    t = _training_or_404(db, training_id)
    if user.role == "DISTRICT_ADMIN" and t.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    if not t.scheme_id:
        return []

    beneficiaries = db.query(Beneficiary).filter(
        Beneficiary.scheme_id == t.scheme_id, Beneficiary.district_id == t.district_id,
        Beneficiary.status == "APPROVED",
    ).all()
    farmer_ids = [b.farmer_id for b in beneficiaries if b.farmer_id]
    fig_ids = [b.fig_id for b in beneficiaries if b.fig_id]
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    figs = {g.id: g for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}
    attendance = {
        a.beneficiary_id: a for a in db.query(TrainingAttendance).filter(
            TrainingAttendance.training_id == training_id).all()
    }

    out = []
    for b in beneficiaries:
        name, code = _beneficiary_display_name(b, farmers, figs)
        a = attendance.get(b.id)
        out.append({
            "beneficiary_id": b.id, "name": name, "code": code,
            "beneficiary_type": b.beneficiary_type,
            "is_present": a.is_present if a else False,
        })
    return out


@router.post("/{training_id}/attendance")
def mark_attendance(training_id: str, body: TrainingAttendanceMarkIn,
                    user: User = Depends(require_roles("DISTRICT_ADMIN")),
                    db: Session = Depends(get_session)):
    t = _training_or_404(db, training_id)
    if t.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    if t.status not in ("Approved", "Completed"):
        raise HTTPException(400, "Attendance can only be marked once the training is Approved or Completed")

    valid_beneficiary_ids = {
        b.id for b in db.query(Beneficiary).filter(
            Beneficiary.scheme_id == t.scheme_id, Beneficiary.district_id == t.district_id,
            Beneficiary.status == "APPROVED").all()
    } if t.scheme_id else set()

    for item in body.items:
        if item.beneficiary_id not in valid_beneficiary_ids:
            raise HTTPException(400, f"{item.beneficiary_id} is not an approved beneficiary of this training's scheme")
        row = db.query(TrainingAttendance).filter(
            TrainingAttendance.training_id == training_id,
            TrainingAttendance.beneficiary_id == item.beneficiary_id).first()
        if row:
            row.is_present = item.is_present
            row.marked_by_user_id = user.id
            row.marked_at = datetime.now(timezone.utc)
        else:
            db.add(TrainingAttendance(
                training_id=training_id, beneficiary_id=item.beneficiary_id,
                is_present=item.is_present, marked_by_user_id=user.id,
            ))
    db.commit()
    return {"ok": True}


# ---------- Certificates ----------
@router.post("/{training_id}/certificates/generate")
def generate_certificates(training_id: str, user: User = Depends(require_roles("DISTRICT_ADMIN")),
                          db: Session = Depends(get_session)):
    t = _training_or_404(db, training_id)
    if t.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    if t.status != "Completed":
        raise HTTPException(400, "Certificates can only be generated once the training is Completed")

    present = db.query(TrainingAttendance).filter(
        TrainingAttendance.training_id == training_id, TrainingAttendance.is_present == True,  # noqa: E712
    ).all()
    existing_beneficiary_ids = {
        c.beneficiary_id for c in db.query(TrainingCertificate).filter(
            TrainingCertificate.training_id == training_id, TrainingCertificate.revoked == False,  # noqa: E712
        ).all()
    }
    to_issue = [a for a in present if a.beneficiary_id not in existing_beneficiary_ids]
    if not to_issue:
        return {"created": [], "already_issued": len(existing_beneficiary_ids)}

    beneficiaries = {
        b.id: b for b in db.query(Beneficiary).filter(
            Beneficiary.id.in_([a.beneficiary_id for a in to_issue])).all()
    }
    farmer_ids = [b.farmer_id for b in beneficiaries.values() if b.farmer_id]
    fig_ids = [b.fig_id for b in beneficiaries.values() if b.fig_id]
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    figs = {g.id: g for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}

    training_dates = f"{t.actual_from_date or t.proposed_from_date} to {t.actual_to_date or t.proposed_to_date}"
    venue = t.actual_venue or t.proposed_venue
    issued_at_str = datetime.now(timezone.utc).strftime("%d %b %Y")

    created = []
    for a in to_issue:
        b = beneficiaries.get(a.beneficiary_id)
        if not b:
            continue
        name, _code = _beneficiary_display_name(b, farmers, figs)
        cert_number = next_certificate_number(db)
        pdf_bytes = render_certificate_pdf(cert_number, name, t.topic, training_dates, venue, issued_at_str)
        district_seg = t.district_id
        path = f"File Uploads/Training Certificates/{district_seg}/{training_id}/{cert_number}.pdf"
        put_object(path, pdf_bytes, "application/pdf")
        db.add(FileRecord(storage_path=path, original_filename=f"{cert_number}.pdf",
                          content_type="application/pdf", size=len(pdf_bytes), uploaded_by=user.id))
        cert = TrainingCertificate(
            training_id=training_id, beneficiary_id=b.id, certificate_number=cert_number,
            issued_by_user_id=user.id, pdf_path=path,
        )
        db.add(cert)
        db.flush()
        created.append({"id": cert.id, "certificate_number": cert_number, "beneficiary_id": b.id, "name": name})
    db.commit()
    return {"created": created, "already_issued": len(existing_beneficiary_ids)}


@router.get("/{training_id}/certificates")
def list_certificates(training_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    t = _training_or_404(db, training_id)
    if user.role == "DISTRICT_ADMIN" and t.district_id != active_district(user):
        raise HTTPException(403, "District scope mismatch")
    certs = db.query(TrainingCertificate).filter(
        TrainingCertificate.training_id == training_id).order_by(TrainingCertificate.issued_at.desc()).all()
    beneficiaries = {
        b.id: b for b in db.query(Beneficiary).filter(
            Beneficiary.id.in_([c.beneficiary_id for c in certs] or [""])).all()
    }
    farmer_ids = [b.farmer_id for b in beneficiaries.values() if b.farmer_id]
    fig_ids = [b.fig_id for b in beneficiaries.values() if b.fig_id]
    farmers = {f.id: f for f in db.query(Farmer).filter(Farmer.id.in_(farmer_ids or [""])).all()}
    figs = {g.id: g for g in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}

    out = []
    for c in certs:
        b = beneficiaries.get(c.beneficiary_id)
        name = _beneficiary_display_name(b, farmers, figs)[0] if b else "Unknown"
        out.append({
            "id": c.id, "certificate_number": c.certificate_number, "beneficiary_name": name,
            "issued_at": c.issued_at, "pdf_path": c.pdf_path,
            "revoked": c.revoked, "revoked_at": c.revoked_at, "revoked_reason": c.revoked_reason,
        })
    return out


@router.post("/certificates/{certificate_id}/revoke")
def revoke_certificate(certificate_id: str, body: CertificateRevokeIn,
                       user: User = Depends(require_roles("DISTRICT_ADMIN", "STATE_ADMIN")),
                       db: Session = Depends(get_session)):
    c = db.query(TrainingCertificate).filter(TrainingCertificate.id == certificate_id).first()
    if not c:
        raise HTTPException(404, "Certificate not found")
    if user.role == "DISTRICT_ADMIN":
        t = _training_or_404(db, c.training_id)
        if t.district_id != active_district(user):
            raise HTTPException(403, "District scope mismatch")
    c.revoked = True
    c.revoked_at = datetime.now(timezone.utc)
    c.revoked_reason = body.reason
    db.commit()
    return {"ok": True}
