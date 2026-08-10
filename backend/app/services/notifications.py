"""Notification creation — shared by the manual /notifications send endpoint and
automated senders (e.g. scheme publish) so both go through one fan-out path.

Threading model: a reply always keeps the IDENTICAL notification_code as whatever it's
replying to, forever — the visible "ticket number" never forks, no matter how many different
recipients reply to the same broadcast. Privacy is tracked separately via thread_id (a purely
internal, never-user-facing self-FK): the first time any one recipient of a broadcast replies,
that reply seeds a brand-new private 2-party thread_id; every further message in that same
back-and-forth (from either party) reuses that thread_id. reply_seq is a small integer, drawn
from a counter shared by every message under one notification_code (regardless of which private
thread_id it's in), letting a sender who has several different recipients' private replies to the
same broadcast (all sharing one code) still tell them apart."""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Notification, NotificationRecipient, User, _uuid

_SENDER_ROLE_TO_SELECTED_TAG = {
    "STATE_ADMIN": "SELECTED_SA",
    "DISTRICT_ADMIN": "SELECTED_DA",
    "FIG_PRESIDENT": "SELECTED_FP",
    "FARMER": "SELECTED_FARMER",
}


def _next_notification_seq(db: Session) -> int:
    # Codes are zero-padded to a fixed width (:06d), so lexicographic ordering matches numeric
    # ordering — safe to sort by the string column directly instead of scanning every row.
    last = db.query(Notification.notification_code).order_by(Notification.notification_code.desc()).first()
    if not last:
        return 1
    try:
        return int(last[0].rsplit("-", 1)[-1]) + 1
    except (ValueError, AttributeError):
        return 1


def _next_reply_seq(db: Session, code: str) -> int:
    """Next sequence number for `code`'s shared counter — spans every private thread under
    that code, not just one of them, so replies from different recipients to the same
    broadcast still draw distinct, increasing numbers."""
    max_seq = db.query(func.max(Notification.reply_seq)).filter(Notification.notification_code == code).scalar()
    return (max_seq or 0) + 1


def create_notification(db: Session, sender_user: User, title: str, details: str,
                        recipient_type: str, recipient_ids: Optional[list[str]] = None,
                        attachment_path: Optional[str] = None) -> dict:
    """Create a ROOT Notification (a fresh broadcast, starting a brand-new notification_code
    and its own thread_id) + fan out NotificationRecipient rows. Does not commit — caller
    controls the transaction boundary. Not used for replies — see create_reply() below."""
    new_id = _uuid()
    code = f"SERI-MSG-{_next_notification_seq(db):06d}"
    n = Notification(id=new_id, notification_code=code, title=title, details=details,
                     attachment_path=attachment_path, sent_by_user_id=sender_user.id,
                     sent_by_role=sender_user.role, recipient_type=recipient_type,
                     thread_id=new_id, reply_seq=0)
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
        if recipient_type == "SELECTED_FP" and sender_user.role == "DISTRICT_ADMIN":
            # A DA's picker only ever offers their own district's FPs — enforce that server-side
            # too, rather than trusting a client-supplied recipient_ids list verbatim.
            recip_ids = [u.id for u in db.query(User).filter(
                User.id.in_(recipient_ids or [""]), User.district_id == sender_user.district_id).all()]
        else:
            recip_ids = recipient_ids
    elif recipient_type == "ALL_SA":
        recip_ids = [u.id for u in db.query(User).filter(User.role == "STATE_ADMIN", User.is_active).all()]
    elif recipient_type in ("SELECTED_SA", "SELECTED_FARMER"):
        # SELECTED_FARMER: a District Admin notifying one specific farmer about their own
        # resubmission (accept/reject) — not composable via the broadcast UI (no farmer picker
        # exists there), only ever sent programmatically with exactly the one farmer's user id.
        recip_ids = recipient_ids

    for uid in recip_ids:
        db.add(NotificationRecipient(notification_id=n.id, recipient_user_id=uid))

    return {"id": n.id, "notification_code": n.notification_code, "thread_id": n.thread_id, "sent_to": len(recip_ids)}


def create_reply(db: Session, sender_user: User, thread_root: Notification, details: str,
                 attachment_path: Optional[str] = None) -> dict:
    """Reply within the private conversation seeded at `thread_root` (the row where
    id == thread_id — always exists, always satisfies thread_root.thread_id == thread_root.id).

    Fork-or-continue is decided by how many active recipients `thread_root` has:
      - exactly 1: CONTINUE — this is already an established private 2-party thread (either an
        earlier reply, or a broadcast that happened to target exactly one person). The reply
        reuses thread_root's own thread_id and title verbatim (no re-prefixing).
      - more than 1: FORK — thread_root is still an un-forked, multi-recipient broadcast. Only
        one of its active recipients may fork it into a new private thread; the fork's title is
        the one and only place "Re: " gets prefixed for this branch, ever.

    Either way, notification_code is ALWAYS inherited unconditionally from thread_root — this is
    the one line that keeps a whole broadcast + every reply to it under one shared, permanent
    code, regardless of fork-vs-continue. reply_seq draws from that code's shared counter."""
    active_recipients = db.query(NotificationRecipient).filter(
        NotificationRecipient.notification_id == thread_root.id,
        NotificationRecipient.is_active,
    ).all()
    recipient_ids_on_root = {r.recipient_user_id for r in active_recipients}

    if len(recipient_ids_on_root) == 1:
        the_recipient = next(iter(recipient_ids_on_root))
        if sender_user.id == thread_root.sent_by_user_id:
            other_party_id = the_recipient
        elif sender_user.id == the_recipient:
            other_party_id = thread_root.sent_by_user_id
        else:
            raise HTTPException(403, "Not authorized to reply in this thread")
        new_id = _uuid()
        thread_id = thread_root.thread_id
        title = thread_root.title
    else:
        if sender_user.id not in recipient_ids_on_root:
            raise HTTPException(403, "You can only reply to a notification you received")
        other_party_id = thread_root.sent_by_user_id
        new_id = _uuid()
        thread_id = new_id
        title = f"Re: {thread_root.title}"

    other_party_role = db.query(User.role).filter(User.id == other_party_id).scalar()
    tag = _SENDER_ROLE_TO_SELECTED_TAG.get(other_party_role)
    if not tag:
        raise HTTPException(400, "Cannot reply to this notification")

    code = thread_root.notification_code
    seq = _next_reply_seq(db, code)

    n = Notification(id=new_id, notification_code=code, title=title, details=details,
                     attachment_path=attachment_path, sent_by_user_id=sender_user.id,
                     sent_by_role=sender_user.role, recipient_type=tag,
                     in_reply_to_id=thread_root.id, thread_id=thread_id, reply_seq=seq)
    db.add(n)
    db.flush()
    db.add(NotificationRecipient(notification_id=n.id, recipient_user_id=other_party_id))

    return {"id": n.id, "notification_code": n.notification_code, "thread_id": n.thread_id,
            "reply_seq": n.reply_seq, "sent_to": 1}


_PAGE_SIZES = {10, 20, 50, 100}


def list_threads(db: Session, user: User, box: str, page: int, page_size: int) -> dict:
    """One row per thread_id the user is a party to (inbox: active recipient on >=1 message in
    that thread; sent: sent >=1 message in that thread — a thread may appear in both), sorted by
    latest-activity-in-that-thread descending. Multiple rows can legitimately share the identical
    notification_code (e.g. a sender's own separate private replies from different recipients to
    the same broadcast) — each row carries reply_seq + the other party's name so the frontend can
    tell them apart."""
    if box == "inbox":
        thread_ids = {t for (t,) in db.query(Notification.thread_id)
                     .join(NotificationRecipient, NotificationRecipient.notification_id == Notification.id)
                     .filter(NotificationRecipient.recipient_user_id == user.id,
                             NotificationRecipient.is_active, Notification.is_active).all()}
    elif box == "sent":
        thread_ids = {t for (t,) in db.query(Notification.thread_id)
                     .filter(Notification.sent_by_user_id == user.id, Notification.is_active).all()}
    else:
        raise HTTPException(400, "box must be 'inbox' or 'sent'")

    total = len(thread_ids)
    if not thread_ids:
        return {"items": [], "total": 0}

    all_msgs = (db.query(Notification).filter(Notification.thread_id.in_(thread_ids), Notification.is_active)
               .order_by(Notification.sent_at.desc()).all())
    latest_by_thread: dict[str, Notification] = {}
    for m in all_msgs:
        latest_by_thread.setdefault(m.thread_id, m)

    ordered = sorted(latest_by_thread.values(), key=lambda m: m.sent_at, reverse=True)
    page_rows = ordered[(page - 1) * page_size: (page - 1) * page_size + page_size]

    # Root title (fixed "subject") per thread.
    root_ids = {m.thread_id for m in page_rows}
    roots = {r.id: r for r in db.query(Notification).filter(Notification.id.in_(root_ids or [""])).all()}

    # My own recipient rows across EVERY message in these threads (not just the latest one per
    # thread) — needed because when the latest message in a thread is one I sent myself, "is this
    # thread unread for me" has to look at the most recent message that was actually addressed to
    # me, not the one I just sent.
    all_msg_ids = [m.id for m in all_msgs]
    my_recip_by_msg: dict[str, NotificationRecipient] = {}
    if all_msg_ids:
        for r in db.query(NotificationRecipient).filter(
                NotificationRecipient.notification_id.in_(all_msg_ids),
                NotificationRecipient.recipient_user_id == user.id).all():
            my_recip_by_msg[r.notification_id] = r
    msgs_by_thread: dict[str, list[Notification]] = {}
    for m in all_msgs:
        msgs_by_thread.setdefault(m.thread_id, []).append(m)  # already sent_at-descending

    other_party_ids = set()
    for m in page_rows:
        other_party_ids.add(m.sent_by_user_id)
    recipient_rows_by_msg: dict[str, list[NotificationRecipient]] = {}
    if page_rows:
        for r in db.query(NotificationRecipient).filter(
                NotificationRecipient.notification_id.in_([m.id for m in page_rows])).all():
            recipient_rows_by_msg.setdefault(r.notification_id, []).append(r)
            other_party_ids.add(r.recipient_user_id)
    other_party_ids.discard(user.id)
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(other_party_ids or [""])).all()}

    items = []
    for m in page_rows:
        root = roots.get(m.thread_id, m)
        other_id = m.sent_by_user_id if m.sent_by_user_id != user.id else None
        if other_id is None:
            recips = recipient_rows_by_msg.get(m.id, [])
            other_id = recips[0].recipient_user_id if recips else None
        is_read = True
        if box == "inbox":
            last_to_me = next((x for x in msgs_by_thread.get(m.thread_id, []) if x.id in my_recip_by_msg), None)
            if last_to_me is not None:
                is_read = my_recip_by_msg[last_to_me.id].is_read
        items.append({
            "thread_id": m.thread_id, "notification_code": m.notification_code, "title": root.title,
            "other_party_name": names.get(other_id), "latest_details_snippet": m.details[:200],
            "latest_sent_at": m.sent_at, "latest_sent_by_role": m.sent_by_role,
            "latest_reply_seq": m.reply_seq, "is_read": is_read,
        })

    return {"items": items, "total": total}


def get_thread_messages(db: Session, user: User, thread_id: str) -> dict:
    msgs = (db.query(Notification).filter(Notification.thread_id == thread_id, Notification.is_active)
           .order_by(Notification.sent_at.asc()).all())
    if not msgs:
        raise HTTPException(404, "Thread not found")

    msg_ids = [m.id for m in msgs]
    recip_rows = db.query(NotificationRecipient).filter(
        NotificationRecipient.notification_id.in_(msg_ids), NotificationRecipient.is_active).all()
    recip_ids_by_msg: dict[str, list[str]] = {}
    for r in recip_rows:
        recip_ids_by_msg.setdefault(r.notification_id, []).append(r.recipient_user_id)
    recip_user_ids = {r.recipient_user_id for r in recip_rows}
    sender_ids = {m.sent_by_user_id for m in msgs}
    if user.id not in recip_user_ids and user.id not in sender_ids:
        raise HTTPException(403, "Not authorized to view this thread")

    # Ancestor (if any) may have many more recipients than fit in msg_ids' set — resolved below,
    # once we know whether an ancestor exists.
    root = msgs[0]
    parent = None
    if root.in_reply_to_id:
        candidate = db.query(Notification).filter(Notification.id == root.in_reply_to_id).first()
        if candidate and candidate.thread_id != thread_id:
            parent = candidate

    ancestor_recip_ids: list[str] = []
    all_user_ids = sender_ids | recip_user_ids
    if parent:
        ancestor_recip_ids = [r.recipient_user_id for r in db.query(NotificationRecipient).filter(
            NotificationRecipient.notification_id == parent.id, NotificationRecipient.is_active).all()]
        all_user_ids = all_user_ids | {parent.sent_by_user_id} | set(ancestor_recip_ids)
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(all_user_ids or [""])).all()}

    def _serialize(m: Notification) -> dict:
        return {"id": m.id, "notification_code": m.notification_code, "reply_seq": m.reply_seq,
                "title": m.title, "details": m.details, "sent_at": m.sent_at,
                "sent_by_user_id": m.sent_by_user_id, "sent_by_name": names.get(m.sent_by_user_id),
                "sent_by_role": m.sent_by_role, "attachment_path": m.attachment_path,
                "in_reply_to_id": m.in_reply_to_id,
                "recipient_names": [names.get(uid) or "—" for uid in recip_ids_by_msg.get(m.id, [])]}

    ancestor = None
    if parent:
        ancestor = {"id": parent.id, "notification_code": parent.notification_code,
                   "reply_seq": parent.reply_seq, "title": parent.title, "details": parent.details,
                   "sent_at": parent.sent_at, "sent_by_user_id": parent.sent_by_user_id,
                   "sent_by_name": names.get(parent.sent_by_user_id),
                   "sent_by_role": parent.sent_by_role, "attachment_path": parent.attachment_path,
                   "in_reply_to_id": parent.in_reply_to_id,
                   "recipient_names": [names.get(uid) or "—" for uid in ancestor_recip_ids]}

    return {"ancestor": ancestor, "messages": [_serialize(m) for m in msgs]}


def mark_thread_read(db: Session, user: User, thread_id: str) -> None:
    msg_ids = [m.id for m in db.query(Notification.id).filter(Notification.thread_id == thread_id).all()]
    db.query(NotificationRecipient).filter(
        NotificationRecipient.notification_id.in_(msg_ids or [""]),
        NotificationRecipient.recipient_user_id == user.id,
        NotificationRecipient.is_active,
        NotificationRecipient.is_read == False,  # noqa: E712
    ).update({NotificationRecipient.is_read: True, NotificationRecipient.read_at: func.now()},
             synchronize_session=False)
