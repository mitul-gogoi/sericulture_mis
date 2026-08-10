"""Notifications: broadcast/compose + threaded conversation view."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models import Notification, NotificationRecipient, User, District, Fig
from app.schemas import NotificationIn, NotificationReplyIn
from app.services.notifications import create_notification, create_reply, list_threads, get_thread_messages, mark_thread_read

router = APIRouter(prefix="/notifications", tags=["notifications"])

_PAGE_SIZES = {10, 20, 50, 100}


@router.post("")
def send(body: NotificationIn, user: User = Depends(require_roles("STATE_ADMIN", "DISTRICT_ADMIN")),
         db: Session = Depends(get_session)):
    result = create_notification(db, user, body.title, body.details, body.recipient_type,
                                 recipient_ids=body.recipient_ids, attachment_path=body.attachment_path)
    db.commit()
    return result


@router.get("/candidates")
def candidates(recipient_type: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_session)):
    if recipient_type == "SELECTED_DA":
        if user.role != "STATE_ADMIN":
            raise HTTPException(403, "Only State Admin can browse District Admins")
        rows = db.query(User).filter(User.role == "DISTRICT_ADMIN", User.is_active).all()
    elif recipient_type == "SELECTED_FP":
        q = db.query(User).filter(User.role == "FIG_PRESIDENT", User.is_active)
        if user.role == "DISTRICT_ADMIN":
            q = q.filter(User.district_id == user.district_id)
        rows = q.all()
    elif recipient_type == "SELECTED_SA":
        rows = db.query(User).filter(User.role == "STATE_ADMIN", User.is_active).all()
    else:
        raise HTTPException(400, "Unsupported recipient_type for candidates")

    district_ids = {u.district_id for u in rows if u.district_id}
    districts = {d.id: d.district_name for d in db.query(District).filter(District.id.in_(district_ids or [""])).all()}
    fig_ids = {u.fig_id for u in rows if u.fig_id}
    figs = {f.id: f.fig_name for f in db.query(Fig).filter(Fig.id.in_(fig_ids or [""])).all()}

    return [{
        "id": u.id, "name": u.name, "mobile_no": u.mobile_no,
        "district_id": u.district_id, "district_name": districts.get(u.district_id),
        "fig_id": u.fig_id, "fig_name": figs.get(u.fig_id),
    } for u in rows]


@router.get("/threads")
def list_threads_route(box: str, page: int = 1, page_size: int = 20,
                       user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    if page_size not in _PAGE_SIZES:
        raise HTTPException(400, "page_size must be one of 10, 20, 50, 100")
    if box not in ("inbox", "sent"):
        raise HTTPException(400, "box must be 'inbox' or 'sent'")
    return list_threads(db, user, box, page, page_size)


@router.get("/threads/{thread_id}")
def thread_detail(thread_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    return get_thread_messages(db, user, thread_id)


@router.post("/threads/{thread_id}/reply")
def reply_to_thread(thread_id: str, body: NotificationReplyIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_session)):
    root = db.query(Notification).filter(
        Notification.id == thread_id, Notification.thread_id == thread_id, Notification.is_active).first()
    if not root:
        raise HTTPException(404, "Thread not found")
    result = create_reply(db, user, root, body.details, attachment_path=body.attachment_path)
    db.commit()
    return result


@router.post("/threads/{thread_id}/read")
def mark_thread_read_route(thread_id: str, user: User = Depends(get_current_user),
                           db: Session = Depends(get_session)):
    mark_thread_read(db, user, thread_id)
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
