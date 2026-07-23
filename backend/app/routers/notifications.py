"""Notifications + inbox."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models import Notification, NotificationRecipient, User
from app.schemas import NotificationIn
from app.services.notifications import create_notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("")
def send(body: NotificationIn, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
         db: Session = Depends(get_session)):
    result = create_notification(db, user, body.title, body.details, body.recipient_type,
                                 recipient_ids=body.recipient_ids, attachment_path=body.attachment_path)
    db.commit()
    return result


@router.get("/inbox")
def inbox(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    rows = db.query(NotificationRecipient).filter(
        NotificationRecipient.recipient_user_id == user.id, NotificationRecipient.is_active).all()
    nids = [r.notification_id for r in rows]
    notifs = {n.id: n for n in db.query(Notification).filter(
        Notification.id.in_(nids or [""]), Notification.is_active).all()}
    out = []
    for r in rows:
        n = notifs.get(r.notification_id)
        if not n:
            continue
        d = n.model_dump()
        d["is_read"] = r.is_read
        d["recipient_id"] = r.id
        out.append(d)
    out.sort(key=lambda x: x.get("sent_at"), reverse=True)
    return out


@router.post("/read/{recipient_id}")
def mark_read(recipient_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_session)):
    r = db.query(NotificationRecipient).filter(
        NotificationRecipient.id == recipient_id,
        NotificationRecipient.recipient_user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(404, "Not found")
    r.is_read = True
    r.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/{notification_id}/retract")
def retract(notification_id: str,
            user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
            db: Session = Depends(get_session)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(404, "Not found")
    if n.sent_by_user_id != user.id and user.role != "STATE_ADMIN":
        raise HTTPException(403, "Cannot retract another user's notification")
    n.is_active = False
    db.query(NotificationRecipient).filter(
        NotificationRecipient.notification_id == notification_id,
    ).update({NotificationRecipient.is_active: False})
    db.commit()
    return {"ok": True}


@router.get("/{notification_id}/recipients")
def notification_recipients(notification_id: str,
                            user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
                            db: Session = Depends(get_session)):
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        raise HTTPException(404, "Not found")
    rows = db.query(NotificationRecipient).filter(
        NotificationRecipient.notification_id == notification_id,
    ).all()
    user_ids = [r.recipient_user_id for r in rows]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids or [""])).all()}
    return [{
        "id": r.id, "recipient_user_id": r.recipient_user_id, "is_read": r.is_read,
        "read_at": r.read_at, "user_name": users.get(r.recipient_user_id).name if users.get(r.recipient_user_id) else None,
        "user_mobile": users.get(r.recipient_user_id).mobile_no if users.get(r.recipient_user_id) else None,
    } for r in rows]


@router.get("/sent")
def sent(user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
         db: Session = Depends(get_session)):
    return db.query(Notification).filter(Notification.sent_by_user_id == user.id).order_by(
        Notification.sent_at.desc()).limit(200).all()
