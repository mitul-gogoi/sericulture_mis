"""Master data — read + State-Admin-only CRUD (create / edit / activate-deactivate).

Split into domain submodules (offices, demographics, yield_lookups, production, assets) —
each declares a bare APIRouter with no prefix of its own; this file combines them all under
the single shared `/master` prefix so every endpoint path and behavior is unchanged from the
previous single-file `master.py`, and `main.py`'s `from app.routers import master` /
`master.router` usage keeps working with zero changes."""
from fastapi import APIRouter
from . import offices, demographics, yield_lookups, production, assets

router = APIRouter(prefix="/master", tags=["master"])
for _sub in (offices.router, demographics.router, yield_lookups.router, production.router, assets.router):
    router.include_router(_sub)
