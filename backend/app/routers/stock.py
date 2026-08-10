"""Current stock snapshot — read-only, role-scoped the same way as GET /yields."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import Stock, User

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("")
def list_stock(fig_id: Optional[str] = None, farmer_id: Optional[str] = None,
              product_id: Optional[str] = None,
              user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    # age computed in SQL (now() - last_entry_at) rather than in Python: both sides are
    # TIMESTAMP WITHOUT TIME ZONE evaluated in the same DB session, so this stays correct
    # regardless of the server's session timezone — a Python-side tzinfo guess would not.
    age_expr = func.extract("epoch", func.now() - Stock.last_entry_at) / 86400.0
    q = db.query(Stock, age_expr.label("age_days"))
    if user.role == "FARMER":
        q = q.filter(Stock.farmer_id == user.farmer_id)
    elif user.role == "FIG_PRESIDENT":
        q = q.filter(Stock.fig_id == user.fig_id)
    elif user.role == "DISTRICT_ADMIN":
        q = q.filter(Stock.district_id == user.district_id)
        if fig_id:
            q = q.filter(Stock.fig_id == fig_id)
    elif fig_id:
        q = q.filter(Stock.fig_id == fig_id)
    if farmer_id:
        q = q.filter(Stock.farmer_id == farmer_id)
    if product_id:
        q = q.filter(Stock.product_id == product_id)
    out = []
    for s, age_days in q.order_by(Stock.updated_at.desc()).limit(2000).all():
        d = s.model_dump()
        d["age_days"] = int(age_days) if age_days is not None else None
        out.append(d)
    return out
