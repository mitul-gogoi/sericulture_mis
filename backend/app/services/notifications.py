"""Notification creation — shared by the manual /notifications send endpoint and
automated senders (e.g. scheme publish) so both go through one fan-out path."""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Notification, NotificationRecipient, User


def create_notification(db: Session, sender_user: User, title: str, details: str,
                        recipient_type: str, recipient_ids: Optional[list[str]] = None,
                        attachment_path: Optional[str] = None) -> dict:
    """Create a Notification + fan out NotificationRecipient rows. Does not commit —
    caller controls the transaction boundary."""
    n = Notification(title=title, details=details, attachment_path=attachment_path,
                     sent_by_user_id=sender_user.id, sent_by_role=sender_user.role,
                     recipient_type=recipient_type)
    db.add(n)
    db.flush()

    recipient_ids = recipient_ids or []
    recip_ids: list[str] = []
    if recipient_type == "ALL_DA":
        if sender_user.role == "DISTRICT_ADMIN":
            raise HTTPException(403, "DAs cannot broadcast to all DAs")
        recip_ids = [u.id for u in db.query(User).filter(User.role == "DISTRICT_ADMIN", User.is_active).all()]
    elif recipient_type == "ALL_FP":
        q = db.query(User).filter(User.role == "FIG_PRESIDENT", User.is_active)
        if sender_user.role == "DISTRICT_ADMIN":
            q = q.filter(User.district_id == sender_user.district_id)
        recip_ids = [u.id for u in q.all()]
    elif recipient_type == "ALL_DA_AND_FP":
        recip_ids = [u.id for u in db.query(User).filter(
            User.role.in_(["DISTRICT_ADMIN", "FIG_PRESIDENT"]), User.is_active).all()]
    elif recipient_type in ("SELECTED_DA", "SELECTED_FP", "SELECTED_DA_AND_FP"):
        recip_ids = recipient_ids
    elif recipient_type == "ALL_SA":
        recip_ids = [u.id for u in db.query(User).filter(User.role == "STATE_ADMIN", User.is_active).all()]
    elif recipient_type == "SELECTED_SA":
        recip_ids = recipient_ids

    for uid in recip_ids:
        db.add(NotificationRecipient(notification_id=n.id, recipient_user_id=uid))

    return {"id": n.id, "sent_to": len(recip_ids)}
