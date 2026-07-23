"""File upload to local folder-structured storage."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.security import decode_access
from app.models import User, FileRecord, District, SericultureCircle, Fig
from app.services.storage import put_object, get_object, _safe_segment

router = APIRouter(tags=["upload"])
ALLOWED = {"jpg", "jpeg", "png", "webp", "pdf"}


def _build_folder(category: str, db: Session, user: User, district_id: str | None,
                  seri_circle_id: str | None, farmer_identifier: str | None, month: str | None) -> str:
    if category in ("farmer_photo", "farmer_passbook"):
        district = db.query(District).filter(District.id == district_id).first() if district_id else None
        circle = db.query(SericultureCircle).filter(SericultureCircle.id == seri_circle_id).first() if seri_circle_id else None
        district_name = _safe_segment(district.district_name if district else "Unknown District")
        circle_name = _safe_segment(circle.circle_name if circle else "Unknown Circle")
        farmer_seg = _safe_segment(farmer_identifier or "Unknown Farmer")
        return f"File Uploads/Farmer Details/{district_name}/{circle_name}/{farmer_seg}"
    if category == "fig_minutes":
        fig = db.query(Fig).filter(Fig.id == user.fig_id).first() if user.fig_id else None
        if fig:
            district = db.query(District).filter(District.id == fig.district_id).first()
            circle = db.query(SericultureCircle).filter(SericultureCircle.id == fig.seri_circle_id).first()
            district_name = _safe_segment(district.district_name if district else "Unknown District")
            circle_name = _safe_segment(circle.circle_name if circle else "Unknown Circle")
            fig_seg = _safe_segment(f"{fig.fig_name} ({fig.fig_code})")
        else:
            district_name = circle_name = "Unknown"
            fig_seg = "Unknown FIG"
        month_seg = _safe_segment(month or "Unspecified Month")
        return f"File Uploads/FIG Details/{district_name}/{circle_name}/{fig_seg}/Monthly Meetings/{month_seg}"
    if category == "assets":
        district = db.query(District).filter(District.id == district_id).first() if district_id else None
        district_name = _safe_segment(district.district_name if district else "Unknown District")
        owner_seg = _safe_segment(farmer_identifier or "Unknown Owner")
        return f"File Uploads/Asset Records/{district_name}/{owner_seg}"
    if category == "certificate":
        district = db.query(District).filter(District.id == district_id).first() if district_id else None
        district_name = _safe_segment(district.district_name if district else "Unknown District")
        training_seg = _safe_segment(farmer_identifier or "Unknown Training")
        return f"File Uploads/Training Certificates/{district_name}/{training_seg}"
    return "File Uploads/Notifications"


@router.post("/upload")
async def upload(file: UploadFile = File(...), category: str = Form("other"),
                 district_id: str | None = Form(None), seri_circle_id: str | None = Form(None),
                 farmer_identifier: str | None = Form(None), month: str | None = Form(None),
                 user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    if ext not in ALLOWED:
        raise HTTPException(400, "Unsupported file type")
    folder = _build_folder(category, db, user, district_id, seri_circle_id, farmer_identifier, month)
    path = f"{folder}/{uuid.uuid4()}_{_safe_segment(file.filename)}"
    data = await file.read()
    ct = file.content_type or ("application/pdf" if ext == "pdf" else f"image/{ext}")
    try:
        result = put_object(path, data, ct)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    db.add(FileRecord(storage_path=result["path"], original_filename=file.filename,
                      content_type=ct, size=result.get("size", len(data)),
                      uploaded_by=user.id))
    db.commit()
    return {"path": result["path"]}


@router.get("/files/{path:path}")
def download(path: str, request: Request, auth: str | None = Query(None),
             db: Session = Depends(get_session)):
    token = auth or (request.headers.get("Authorization", "")[7:]
                     if request.headers.get("Authorization", "").startswith("Bearer ") else None)
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        decode_access(token)
    except Exception:
        raise HTTPException(401, "Invalid token")
    rec = db.query(FileRecord).filter(FileRecord.storage_path == path,
                                       ~FileRecord.is_deleted).first()
    if not rec:
        raise HTTPException(404, "File not found")
    try:
        data, ct = get_object(path)
    except RuntimeError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type=rec.content_type or ct)
