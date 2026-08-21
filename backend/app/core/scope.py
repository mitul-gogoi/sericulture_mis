"""District scoping for admins who hold additional charge of several districts.

A District Admin may be responsible for more than one district (models.UserDistrict). They
act as ONE district at a time, chosen in the UI and sent on each request as the
`X-District-Id` header.

The header is a *request*, never a grant: `resolve_active_district` validates it against the
assignments in the database on every call, so a forged or stale id is rejected, not honoured.

Two deliberate design choices, both about avoiding a worse failure mode:

1. `User.district_id` is never mutated. The User object is live in the request's SQLAlchemy
   session and `auth.change_password` does `user.password_hash = ...; db.commit()` -- a
   mutated district_id would be flushed by that commit and permanently corrupt the officer's
   primary district. The active district is kept in a separate, non-mapped attribute.

2. `active_district(user)` falls back to `user.district_id` (the primary) whenever nothing
   was set -- outside a request, in scripts, or at a call site not yet converted.
   So the failure mode of missing a call site is "this page only shows the primary district",
   a visible and reportable gap, never a cross-district data leak.
"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User, UserDistrict

DISTRICT_HEADER = "X-District-Id"

# Stashed on the User instance itself, as a plain attribute that is NOT a mapped column.
#
# A ContextVar was the obvious choice and does not work: FastAPI runs `def` dependencies
# and `def` endpoints in separate threadpool contexts, so a value set inside
# get_current_user is discarded before the route handler runs. Verified, not assumed.
#
# A non-mapped attribute rides along on the object every call site already has, and
# SQLAlchemy does not flush it -- also verified: setting it and committing leaves
# users.district_id untouched.
_ATTR = "_active_district"


def set_active_district(user: User, district_id: Optional[str]) -> None:
    setattr(user, _ATTR, district_id)


def active_district(user: User) -> Optional[str]:
    """The district this request is acting as.

    Use this instead of `user.district_id` anywhere a District Admin's scope is applied.
    Falls back to the primary district when nothing was set for this request -- so a call
    site that is never converted keeps today's behaviour rather than leaking a district.
    """
    if user.role != "DISTRICT_ADMIN":
        return user.district_id
    return getattr(user, _ATTR, None) or user.district_id


def assigned_district_ids(db: Session, user: User) -> List[str]:
    """Every district this user may act as, primary first.

    Falls back to the primary alone when no join rows exist, so an account created before
    user_districts existed still behaves correctly.
    """
    if user.role != "DISTRICT_ADMIN":
        return [user.district_id] if user.district_id else []
    ids = [d.district_id for d in
           db.query(UserDistrict).filter(UserDistrict.user_id == user.id).all()]
    if user.district_id:
        if user.district_id in ids:
            ids.remove(user.district_id)
        ids.insert(0, user.district_id)
    return ids


def set_assigned_districts(db: Session, user: User, district_ids: List[str]) -> None:
    """Replace a District Admin's assignments.

    The first entry becomes User.district_id (the primary), so the column and the join
    table can never drift apart.
    """
    seen: List[str] = []
    for d in district_ids:
        if d and d not in seen:
            seen.append(d)
    db.query(UserDistrict).filter(UserDistrict.user_id == user.id).delete(
        synchronize_session=False)
    for d in seen:
        db.add(UserDistrict(user_id=user.id, district_id=d))
    user.district_id = seen[0] if seen else None


def resolve_active_district(db: Session, user: User,
                            requested: Optional[str]) -> Optional[str]:
    """Validate a requested district against what the user actually holds."""
    if user.role != "DISTRICT_ADMIN":
        return None
    allowed = assigned_district_ids(db, user)
    if not requested:
        return allowed[0] if allowed else None
    if requested not in allowed:
        raise HTTPException(403, "You are not assigned to that district")
    return requested
