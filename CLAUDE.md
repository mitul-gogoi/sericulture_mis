# Sericulture MIS

Web app for the Directorate of Sericulture, Government of Assam. Monorepo, API-first, decoupled frontend/backend. Full build history and backlog live in [memory/PRD.md](memory/PRD.md) — read that for the detailed changelog; business use cases (what each role can do, in user-story + step-by-step form) live in [memory/BUSINESS_USE_CASES.md](memory/BUSINESS_USE_CASES.md); this file is for orientation and day-to-day dev.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11), SQLModel + SQLAlchemy 2, Alembic migrations |
| Database | PostgreSQL 17 + PostGIS (local db: `sericulture_mis`, user/pass `postgres`/`postgres`) |
| Frontend | Next.js 15 App Router, TypeScript 5.7, TanStack Query v5, Tailwind |
| Auth | JWT bearer + refresh tokens, slowapi rate limiting, per-user lockout |
| E2E tests | Playwright (`frontend/e2e/auth.spec.ts`) |

## Running locally (Windows)

```
# Backend (from backend/, with .venv activated)
uvicorn app.main:app --reload --port 8001

# Frontend (from frontend/)
yarn dev        # next dev on :3000
```

**Dev mode vs. actually using the app**: `next dev` (`yarn dev`) JIT-compiles each route in the browser on first visit — expect a multi-second stall the first time you open the dashboard or any sidebar page after a server (re)start. This is normal for active development (you get hot-reload) but is *not* how the app should run when you're just using it day-to-day. For that, build once and run the production server instead:

```
# Frontend (from frontend/) — build once, then serve the compiled build
yarn build
yarn start      # next start on :3000, routes pre-compiled, no per-page stall

# Backend — drop --reload for day-to-day use; it only exists to pick up code edits
uvicorn app.main:app --port 8001
```

Re-run `yarn build` after pulling/making frontend changes; `yarn start` alone will keep serving the last build.

**PowerShell users**: if invoking the venv's uvicorn by full path from the project root instead of activating the venv, prefix with the call operator `&` — PowerShell parses a bare leading quoted string as a string literal, not a command, and errors with "Unexpected token":

```powershell
& "backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --app-dir backend
```

The FastAPI startup event runs `alembic upgrade head` and seeds master data + demo accounts automatically — no manual migration step needed as long as the local Postgres instance and `sericulture_mis` database exist.

`.claude/launch.json` defines `backend` (port 8001, `uvicorn.exe ... --app-dir backend`) and `frontend` (port 3000, `yarn --cwd ... dev`) configs for Claude Code's `preview_start` tooling — use those instead of hand-rolling the commands above when working via that tooling.

### Demo credentials
| Role | Mobile | Password |
|---|---|---|
| State Admin | `9999999999` | `Admin@123` |
| District Admin | `8888888888` | `District@123` |
| FIG President | `7777777777` | `Fig@123` |

## Roles, menus, and dashboards

Three roles: **STATE_ADMIN (SA)**, **DISTRICT_ADMIN (DA)**, **FIG_PRESIDENT (FP)**. Sidebar menus are defined per role in [frontend/src/app/(app)/AppShell.tsx](frontend/src/app/(app)/AppShell.tsx); dashboard widgets are in [frontend/src/app/(app)/dashboard/page.tsx](frontend/src/app/(app)/dashboard/page.tsx), fed by `GET /api/reports/dashboard` (role-aware response shape).

### State Admin (SA) — full state-wide access

Sidebar:
- **Dashboard**
- **Masters** (collapsible): Districts, Sericulture Blocks, Caste, Religion, Silk Types, Activities, Products, Silk Type × Activity × Product, Asset Types
- **Farmers & FIGs** (collapsible): Farmer Management, FIG Management
- **Meetings & Yield** (collapsible): Monthly Submission Status, Yield Reports
- **Land & GIS**: GPS Verification & Reports
- **Asset Management**: Assets (durable-asset tracking — see the Asset Management section below)
- **Training**: Training Requests
- **Schemes** (collapsible): Scheme Management, Allocations, Beneficiaries
- **User Management** (collapsible): State Admins, District Admins, FIG Presidents
- **Notifications**
- **Reports & Analytics** (collapsible, 11 items — merged from the previously-separate "Reports" and "Analytics" groups): Reports, Scheme Utilization, District Comparison, Onboarding Trend, Farmers Drill-down, FIGs Drill-down, Lands Drill-down, Production Explorer, Stock Explorer, DFL Efficiency, Byproduct Ratio.

Dashboard: 4 clickable stat cards (Total Farmers → Farmers Drill-down, Active FIGs → FIGs Drill-down, Districts → District Comparison, Activities → Activities master) · Farmer/FIG onboarding summary (total + this-month delta + by-district breakdown, each district row deep-links straight to that district's block-level drill-down) · Production-by-product tiles (month/FY toggle, each linking to Production Explorer pre-filtered by product) · Current-stock-by-product tiles (no period toggle — stock is point-in-time, each linking to Stock Explorer pre-filtered) · Monthly submission counter · Silk-type-wise FIG distribution bar chart · District submission heatmap · Planned vs Actual yield trend line chart · Year-on-year multi-series production trend (toggleable fiscal-year multi-select).

**Reports & Analytics**: `/reports/*` are fixed-shape, filterable, **Excel/PDF-exportable** rollup pages (numbers only, no charts — charts are a Dashboard/Analytics thing); `/analytics/*` are interactive breadcrumb drill-down explorers (`frontend/src/components/DrillDownExplorer.tsx`) — District → Block for Farmers/FIGs/Lands; District → Block → FIG → Farmer for Production/Stock. **Production and Stock are two different endpoints now, not one relabeled**: Production Explorer (`/analytics/products`, `GET /reports/analytics/products`) requires picking a Product and keeps the month/fiscal-year filter (production is a time-bound flow, correctly additive across months); Stock Explorer (`/analytics/stock`, `GET /reports/analytics/stock`) also requires a Product but has **no month/fiscal-year filter at all** — stock is a point-in-time balance and must never be summed across a period. See `backend/app/services/analytics.py` + `backend/app/routers/analytics.py`, and `DrillDownExplorer.tsx`'s generic `dimension` prop (`label`/`paramName`/`options`/`initialId`/`showPeriodFilter`) which drives both.

### District Admin (DA) — scoped to own district

Sidebar:
- **Dashboard**
- **Farmers & FIGs** (collapsible): Farmer Management, FIG Management
- **Meetings & Yield** (collapsible): Monthly Submission Status, Yield View (read-only)
- **Land**: Land Management
- **Asset Management**: Assets
- **Training**: Training
- **Schemes** (collapsible): Scheme Beneficiaries, District Allocations
- **Notifications**
- **Reports & Analytics** (collapsible, 10 items — same as SA minus District Comparison, which is SA-only).

Dashboard: same additions as SA (onboarding summary, production/stock tiles, YoY trend) but district-scoped throughout — the onboarding breakdown shows by-block (not by-district, since DA is already pinned to one district) · 4 stat cards (Farmers in District, Active FIGs, Activities Represented, Total FIG Members) · Action queue (GPS Verification Pending, Training Requests pending).

**Reports & Analytics**: same drill-down as SA's, pre-scoped to their own district — they land directly at Block level (no District-level list) and the backend rejects any attempt to pass a different `district_id`. DFL Efficiency and Byproduct Ratio are also available to DA (district-scoped), not SA-only.

### FIG President (FP) — scoped to own FIG

Sidebar:
- **Dashboard**
- **Monthly Submission** (collapsible): Submit This Month, Submission History
- **Non-Primary Yield**: Non-Primary Activity Yield
- **Members**: FIG Members
- **Land & GPS**: Land & GPS
- **Asset Management**: Assets (read-only — DA/SA create and verify, FP only views own-FIG holdings)
- **Notifications**: My Notifications
- **Analytics** (collapsible, 2 items — unchanged group name/count from before v3.0 Phase 3, since FP never had a separate Reports group to merge): Production Explorer, Stock Explorer (both renamed from the old "Yield Explorer"/relabeled-Stock pattern, now pointing at the real product-based endpoints).

Dashboard: "Your FIG" banner card (name, FIG ID, district) · 3 stat cards (Active Members, Meetings Logged, This month submission status badge with "Start submission" CTA if not yet submitted) · 4 quick-action tiles (Submit This Month, Non-Primary Yield, Submit GPS Coordinates, View Members) · Production-by-product and current-stock-by-product tiles (own-FIG-scoped) · Planned vs Actual yield trend line chart · Year-on-year trend. Header also shows a persistent "Submit this month" button. FP has no onboarding summary (not their concern) and is 403'd on `/reports/onboarding-trend`, DFL Efficiency, and Byproduct Ratio.

FP has no Farmers/FIGs/Lands drill-down (no district/block to descend through; their own roster is already `/figs`), but does get a member-wise Production/Stock breakdown within their own FIG — locked to `fig_id = user.fig_id`, `level=farmer` only.

## Business rules & codes

- **Farmer code**: `SERI-FRM-NNNNNN` (6 digits), floor `100001`, sequence skips any candidate ending in `0` — [backend/app/routers/farmers.py](backend/app/routers/farmers.py).
- **FIG code**: `SERI-FIG-NNNNN` (5 digits), floor `10001`, same skip-trailing-zero rule — [backend/app/routers/figs.py](backend/app/routers/figs.py).
- **FIG registration is a composite flow**, not a single form: create FIG → add members (picked only from farmers with no active FIG membership) → optionally set a president, which provisions a `FIG_PRESIDENT` login tied to that farmer's mobile number — [frontend/.../figs/page.tsx](frontend/src/app/(app)/figs/page.tsx).
- Farmer and FIG both support edit + activate/deactivate (soft-disable only, no hard delete).
- **Masters (Districts, Sericulture Blocks, Caste, Religion, Silk Types, Activities, Products, Silk Type × Activity × Product) support hard delete**, State-Admin-only: the row must already be deactivated (`is_active=false`) before the Delete button appears/the endpoint accepts it, and a `window.confirm()` names the record before the API call fires. FK conflicts (e.g. deleting an Activity still referenced by FIGs/yields) return a friendly `400`, not a 500 — see `delete_or_conflict` in [backend/app/core/db.py](backend/app/core/db.py) and the `DELETE /master/{entity}/{id}` endpoints spread across [backend/app/routers/master/](backend/app/routers/master/) (one submodule per entity group — see "Backend module layout" below).
- "Reset president password" is a distinct action from "Set/Update President" (separate endpoint/button on the FIG detail view — easy to conflate the two).
- Land GPS submission accepts manual lat/lng entry (an "Add point" button) as well as map-click; ≥3 points required before submit.
- `/meetings` is role-branching: State/District Admin get a month-by-FIG submission status grid, FIG President gets their own submission history.
- The FIG-President dashboard card resolves `fig_name` / `fig_code` / `district_name` server-side via `GET /api/reports/dashboard` — it does not display raw UUIDs.
- Reports support both calendar `month` and Indian fiscal-year (`fiscal_year`, e.g. `"2026-27"` = Apr 2026–Mar 2027) filters, mutually exclusive — see `backend/app/services/fiscal.py`. As of v3.0 Phase 3 the sidebar entry is the merged **"Reports & Analytics"** collapsible group for SA/DA (Reports pages keep this month-XOR-fiscal_year filter; `GET /api/reports/analytics/stock` is the one exception with no period filter at all — see the Stock bullet above).
- Allocating beyond a scheme's budget is allowed but returns a `warning` field (shown as a toast); registering a scheme beneficiary requires an allocation to already exist for that scheme+district and can't exceed its remaining balance.
- **Schemes have real targeting criteria, set by the State Admin, resolved by the District Admin** (added v3.2): `Scheme.beneficiary_kind` (FARMER|FIG), `target_all_districts`/`target_district_ids`, `target_silk_type_ids`, `target_genders`, `target_farmer_types` (target activities reuse the existing `activity_ids` column) — every list-valued field means "empty = no restriction, non-empty = must match." A State Admin authors + targets a scheme; a District Admin can only register beneficiaries who both match the criteria **and** fall in their own district (`services/scheme_targeting.py`'s `candidate_farmers()`/`candidate_figs()`, surfaced via `GET /schemes/{id}/candidates`). `Beneficiary` is polymorphic (`farmer_id` nullable, `fig_id` added, `beneficiary_type`) — registering against a FARMER-kind scheme with a `fig_id` (or vice versa) is a `400`.
- **Scheme lifecycle**: create → activate/deactivate (existing) → **archive** (new, State-Admin-only, requires `is_active=false` first — same "deactivate before delete/archive" guard shape as Masters hard-delete) → hidden from `GET /schemes` by default (`include_archived=true` to see them). **Publish** (`POST /schemes/{id}/publish`, State-Admin-only) resolves every targeted District Admin + FIG President and fans out a notification via `services/notifications.py`'s `create_notification()` (the same helper the manual `/notifications` send endpoint uses) — sets `Scheme.notified_at`, re-publishable.
- **Asset Management** (new module, v3.2): `AssetType` (16-row seeded catalog: rearing houses, mountages, reeling/spinning machines, looms, CFC/CRC shared infrastructure — **not** host-plant plantations, which are land, and **not** low-value consumables), `AssetInstance` (polymorphic `owner_type`/`owner_id` — farmer or FIG, no DB-level FK, same soft-reference pattern as `User.farmer_id`), `AssetVerificationLog` (append-only). `ownership_level` is `INDIVIDUAL | FIG | EITHER` — `EITHER` resolves at scheme-grant time to whichever the actual beneficiary is (`services/assets.py`'s `resolve_owner_for_asset()`). Assets are **created/verified by District/State Admin only** (mirrors land GPS verification — no separate "Circle Officer" role); FIG President is **read-only**, scoped to their own FIG + members.
- **Useful-life cooldown** is the mechanic connecting Assets to Schemes: `services/assets.py`'s `check_asset_cooldown()` takes `MAX(acquisition_date)` for an owner+asset-type across **every** `acquisition_mode` (self-declared, self-procured, and scheme-disbursed all count equally — otherwise pre-digital history would be invisible), compares against `today` vs. `last_acquired + useful_life_years`. An ineligible result is a **flag surfaced to the District Admin, not a hard block** — `POST /schemes/beneficiaries` (and the `/bulk` variant) requires a `cooldown_override_reason` to proceed when blocked, persisted on `Beneficiary.cooldown_override_reason` as an audit trail. Registering a beneficiary on a scheme with `grants_asset_type_id` set auto-creates the matching `AssetInstance` (`acquisition_mode="SCHEME_DISBURSEMENT"`, linked via `scheme_id`+`beneficiary_id`).
- **Route-ordering matters in `schemes.py`**: FastAPI matches path operations in registration order, so every literal path (`/allocations`, `/beneficiaries`, `/beneficiaries/bulk`) is registered **before** the catch-all `/{scheme_id}` routes — otherwise `GET /schemes/beneficiaries` gets swallowed by `GET /schemes/{scheme_id}` treating "beneficiaries" as a scheme ID. Keep new literal routes above the catch-all block if you add any.
- `Fig.total_members` is computed live from `fig_members`, not stored — there is no counter to drift.
- **`Sector`/`Stage` are gone (removed in v3.1)** — `SilkType`/`Activity`/`Product`/`SilkTypeActivityProduct` (STAP) is the single master now. Every former Stage reference points at a STAP row directly: `Fig.stap_id`, `Farmer.stap_ids`/`primary_stap_id`, `Yield_.stap_id` — a bare `activity_id` isn't enough because the same Activity spans all 4 silk types and can map to multiple Products within one, so only the (silk_type, activity, product) triple that STAP already captures is enough to stand in for what Stage encoded. `Scheme.silk_type_id`/`activity_id` and `Training.activity_id` are plain FKs (no STAP granularity needed — they're eligibility metadata, not yield records). A FIG's applicable byproducts are resolved via `Fig.stap_id → silk_type_id → byproduct Products` (`GET /figs/{id}/byproduct-options`) — no bridge lookup needed anymore.
- **`Yield_.activity_id`/`product_id`** are resolved server-side at submission time (`meetings.py`, both `POST /meetings` and `POST /yields/non-primary`) as a direct dereference of `stap_id` — never trust a client-supplied value for these.
- **Stock is a real snapshot, not a sum**: `Stock` (one row per farmer+product) is upserted via a delta (`produced − sold`) inline with every yield/byproduct write — see `backend/app/services/stock.py`. This is only correct because `Yield_`/`ByproductEntry` rows are immutable after submission (no edit/delete endpoint exists for either); if that ever changes, `Stock` needs a compensating-adjustment step, not just a delta upsert. The legacy `Yield_.stock_balance` field is still populated (from the fresh `Stock.closing_balance` after upsert, not raw user input) for backward compatibility, but as of v3.0 Phase 3, **no report or analytics endpoint reads it anymore** — `reports.py`/`analytics.py` dropped the field entirely rather than fixing the old `SUM()` bug, since Stock now has its own dedicated, period-less endpoints (`GET /reports/analytics/stock`, `GET /reports/stock-summary`).
- **Production is additive, Stock is not — never conflate the two.** Production (`planned_yield`/`actual_yield`/`earning`) is a time-bound flow, correctly summed across farmers, FIGs, and months (a fiscal year's total really is 12 months summed). Stock is a point-in-time level — summing it across months is meaningless and was the root of the pre-v3.0-Phase-3 bug. Any new report/analytics endpoint touching stock must query the `Stock` table directly and must never accept a `month`/`fiscal_year` parameter.
- **Byproducts are a separate table** (`ByproductEntry`, linked via `parent_yield_id`), not `Yield_` rows with `is_primary_stage=False` — that flag already means something else (a farmer's other whole-stage assignment via `POST /yields/non-primary`).
- **Postgres session timezone is `Asia/Calcutta`**, not UTC — a tz-aware Python `datetime` written into a `TIMESTAMP WITHOUT TIME ZONE` column gets silently converted to IST wall-clock time before storage. Never diff a DB-stored timestamp against `datetime.now(timezone.utc)` in Python; compute the diff in SQL instead (`func.now() - Column`), as `GET /stock`'s `age_days` does — both sides then share the same session-timezone context and stay correct regardless of server config.
- **Excel/PDF export is a single generic dispatcher**, not one endpoint per report: `GET /api/reports/export?report=<name>&format=xlsx|pdf` reuses each report's existing plain row-fetching function (e.g. `_yield_summary_rows`, `dfl_efficiency_rows`) so the export always matches the on-screen numbers exactly — see `backend/app/services/export.py` and `frontend/src/lib/export.ts`. Reports are numbers-only exports (no charts) by design; only 6 of the 8 dispatcher-supported reports have a dedicated frontend page with an Export button (`product-summary`/`stock-summary` are Dashboard-tile-only data sources with no standalone page).

## Backend module layout

`backend/app/models/`, `backend/app/schemas/`, and `backend/app/routers/master/` are **packages, not single files** (split in v3.3 for AI-maintainability — the originals were 674/379/1205-line monoliths). Each package's `__init__.py` re-exports everything the old single-file version exposed, so every existing `from app.models import X` / `from app.schemas import Y` call site and every `master.router` usage in `main.py` keeps working unchanged — this was verified via `openapi.json` path/method diffing (132/132 identical) plus an Alembic-autogenerate diff against the original monolithic content.

- `models/`: `_common.py` (`_uuid()`/`_now()` helpers) + one file per domain — `masters.py`, `users.py`, `farmers.py`, `figs.py`, `meetings.py`, `lands.py`, `schemes.py`, `assets.py`, `trainings.py`, `notifications.py`.
- `schemas/`: mirrors the same domain split — `auth.py`, `users.py`, `lands.py`, `assets.py`, `farmers.py`, `figs.py`, `meetings.py`, `schemes.py`, `trainings.py`, `notifications.py`.
- `routers/master/`: `_common.py` (shared `ActiveToggleIn`/query helpers) + `offices.py` (District/SubdivisionCdc/SericultureCircle/DirectorateOffice/FigSettings), `demographics.py` (Caste/Religion/EducationLevel), `yield_lookups.py` (LossReason/InputSourceCategory/InputSourceType), `production.py` (SilkType/Activity/Product/STAP — including the large `/silk-type-activity-products/{id}/options` endpoint), `assets.py` (AssetType catalog). `__init__.py` combines them into one `APIRouter(prefix="/master")` via `include_router()`, so the `/master/*` URL surface is byte-identical to before.

When adding a new master entity or model, add it to the relevant domain submodule (or create a new one) rather than growing `__init__.py` — that defeats the point of the split.

## Deployment (AWS EC2, Docker, UAT)

This is a **UAT deployment**, not production-grade: plain HTTP on an EC2 public IP, no domain, no TLS/reverse-proxy. Both `backend/Dockerfile` and `frontend/Dockerfile` are multi-stage, non-root, and built via the root `docker-compose.yml` (two services, `backend` + `frontend`, no local Postgres container — the database is external).

- **Database**: PostgreSQL + PostGIS on Supabase's free tier, via the **Session Pooler** (IPv4-compatible, port 5432, host `aws-0-<region>.pooler.supabase.com`) — not the direct connection (IPv6-only without a paid add-on) and not the Transaction pooler (port 6543, has psycopg v3 prepared-statement issues). Falls back to a Postgres+PostGIS container on the same EC2 instance if Supabase doesn't pan out.
- **Driver**: `requirements.txt` uses `psycopg[binary]>=3.1` (the v3 driver `DATABASE_URL`'s `postgresql+psycopg` dialect actually needs) — the old `psycopg2-binary` entry only worked locally because both happened to be installed in the dev `.venv`.
- **CORS**: `CORS_ORIGINS` (comma-separated, in `backend/.env`) now actually drives `app/main.py`'s `CORSMiddleware.allow_origins` — it used to be dead config with a hardcoded `["*"]`. Set it to the EC2 instance's public origin (e.g. `http://<ec2-ip>:3000`).
- **DB pool**: `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` env vars (default 5/5, down from a hardcoded 10/20) — kept low against Supabase free-tier connection caps.
- **PostGIS bootstrap**: the baseline Alembic migration (`82b4b3356c50_baseline.py`) runs `CREATE EXTENSION IF NOT EXISTS postgis` as its first statement, so a fresh database (Supabase or EC2-hosted) doesn't fail on `Land.boundary`'s `Geometry` column.
- **File uploads**: still local-disk (`UPLOAD_ROOT`, no S3/DMS), fixed at `/data/uploads` inside the backend container and backed by a `backend_uploads` named Docker volume — protects against routine `docker compose restart` wiping the container's writable layer (not full durability; that's a known, accepted gap for this UAT pass).
- **Frontend build-time config**: `NEXT_PUBLIC_BACKEND_URL` is a Docker build `ARG` (Next.js bakes `NEXT_PUBLIC_*` vars in at build time, not runtime) — must be set to the EC2 instance's public backend URL when building the image, not `localhost`.
- See `backend/.env.example` for the full real env-var list with placeholder values.
- Out of scope for this pass (tracked as follow-up, not silently dropped): HTTPS/TLS/domain/reverse-proxy, and the pre-existing security gaps below.

## Known gaps / gotchas

- No refresh-token revocation/blocklist yet; no annual report; no pagination on list tables. Full backlog in `memory/PRD.md`. (Excel/PDF export and a stock-position report were added in v3.0 Phase 3 — see `GET /api/reports/export` and `GET /api/reports/stock-summary`/`analytics/stock`.)
- Several endpoints have thin auth/scoping (public master-data & scheme reads, unscoped farmer-by-ID fetch, notification district-scoping bypass on some recipient types) — see "Known issues" in `memory/PRD.md`'s backlog.
- **Asset Management has no legacy-data CSV import, no mandatory pre-registration declaration gate, and no rollout-completion dashboard** — all three existed in the original feature spec but were explicitly descoped by the user in favor of District Admins entering existing assets directly (with photos) via the standalone `/assets` page. Not a bug, just scope not built this round — see the v3.2 entry in `memory/PRD.md`.
