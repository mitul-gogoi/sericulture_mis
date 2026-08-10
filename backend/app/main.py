"""FastAPI app factory."""
import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.limiter import limiter
from app.core.db import engine, SessionLocal
from app.models import (  # noqa — ensure metadata loaded
    District, SericultureCircle, DirectorateOffice, FigSettings, Caste, Religion, EducationLevel, User, Farmer, Fig,
    FigMember, Meeting, Attendance, Yield_, Land, Scheme, Allocation,
    Beneficiary, Training, Notification, NotificationRecipient, FileRecord,
    SilkType, Activity, Product, SilkTypeActivityProduct, ByproductEntry, Stock,
    AssetType, AssetInstance, AssetVerificationLog,
)
from app.seed import seed_all
from app.routers import (
    auth, master, farmers, figs, meetings, lands, schemes, trainings,
    notifications, reports, users, upload, analytics, stock, assets, farmer_submissions,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sericulture")

app = FastAPI(title="Sericulture MIS API", version="2.0")

# Rate limit handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers — all mounted under /api
for r in [auth.router, master.router, farmers.router, figs.router, meetings.router,
          lands.router, schemes.router, trainings.router, notifications.router,
          reports.router, users.router, upload.router, analytics.router, stock.router,
          assets.router, farmer_submissions.router]:
    app.include_router(r, prefix="/api")


@app.get("/api")
def root():
    return {"app": "Sericulture MIS API", "status": "ok", "version": "2.0"}


@app.on_event("startup")
def startup():
    # Run Alembic migrations to head (single source of truth for schema).
    # Retried a few times as defensive robustness against a slow/flaky first
    # connection to a remote DB — connect_timeout (set in alembic/env.py)
    # turns a stuck connection into a fast failure instead of hanging forever.
    from alembic.config import Config
    from alembic import command
    import os
    import time
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

    attempts = 5
    for attempt in range(1, attempts + 1):
        try:
            command.upgrade(cfg, "head")
            break
        except Exception as exc:
            if attempt == attempts:
                raise
            logger.warning(f"Alembic upgrade attempt {attempt}/{attempts} failed: {exc}. Retrying in 3s...")
            time.sleep(3)

    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    logger.info("Startup complete — Alembic upgraded and DB seeded.")


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
