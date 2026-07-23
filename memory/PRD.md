# Sericulture MIS — PRD & Tracking (v3.0)

## Original Problem Statement
Build a web application implementing the **Sericulture MIS Business Requirements** PRD for the Directorate of Sericulture, Government of Assam.

## Architecture
Monorepo · API-first · decoupled frontend/backend.

```
/ (repo root)
├── docker-compose.yml         # backend + frontend services, backend_uploads named volume
├── backend/
│   ├── Dockerfile, .dockerignore
│   ├── alembic.ini, alembic/  # Database migrations (baseline + future)
│   ├── app/
│   │   ├── main.py            # FastAPI factory, routers, Alembic-on-startup, seeding
│   │   ├── core/               # config, db engine, security, deps, slowapi limiter
│   │   ├── models/             # package: _common.py + one file per domain (masters/users/farmers/figs/meetings/lands/schemes/assets/trainings/notifications), __init__.py re-exports all
│   │   ├── schemas/            # package: same domain split as models/, __init__.py re-exports all
│   │   ├── routers/            # 12 modular routers under /api/*; routers/master/ is itself a package (offices/demographics/yield_lookups/production/assets submodules, __init__.py combines into one /master-prefixed router)
│   │   ├── services/           # geo (Shoelace + WKT), storage (local disk)
│   │   └── seed.py
│   ├── requirements.txt, .env, .env.example
└── frontend/                  # Next.js 15 App Router + TypeScript
    ├── Dockerfile, .dockerignore
    ├── package.json           # scripts: start, build, types:gen, test:e2e
    ├── playwright.config.ts
    ├── e2e/auth.spec.ts       # E2E tests
    └── src/
        ├── app/
        │   ├── login/page.tsx
        │   └── (app)/         # auth-gated route group
        │       ├── AppShell.tsx
        │       └── (12+ pages: dashboard, farmers, figs, submission, ...) — each page owns its data-fetching and composes prop-driven components from components/<feature>/
        ├── components/        # FileUpload.tsx, ViewField.tsx, and per-feature subfolders (farmers/, figs/, schemes/, ...) of small non-data-fetching components
        └── lib/
            ├── api.ts         # axios + refresh-token interceptor
            ├── auth.tsx
            ├── types.ts
            ├── api-types.ts   # generated TS bindings (re-exports)
            └── openapi.d.ts   # auto-generated from FastAPI
```

## Tech Stack
| Layer | Technology |
|---|---|
| Backend framework | **FastAPI** (modular routers) |
| Backend language | **Python 3.11** |
| Database | **PostgreSQL 15 + PostGIS 3** |
| ORM | **SQLModel + SQLAlchemy 2** |
| Migrations | **Alembic** baseline + autogenerate, run on startup |
| Frontend framework | **Next.js 15 App Router** |
| Frontend language | **TypeScript 5.7** strict |
| Type sharing | **`openapi-typescript`** generates frontend types from FastAPI OpenAPI |
| State | **TanStack Query v5** |
| Auth | **JWT bearer + refresh tokens + slowapi 5/min rate-limit + per-user lockout** |
| Geospatial | **PostGIS `ST_Intersects`** for overlap detection |
| File storage | Local disk (Docker volume in deployment) |
| E2E tests | **Playwright** |
| UI | Tailwind, Manrope + IBM Plex Sans, Mulberry green / Muga yellow palette |

## Latest v3.3 — Emergent Cleanup, Backend Module Split, Frontend Component Extraction, Deployment Infra (Jul 2026)

Three-part effort ahead of putting the app in front of real UAT testers: (1) remove leftover tooling from the original Emergent.sh cloud sandbox this app was bootstrapped on, (2) split the three largest, most-tangled files (backend `models/`, `schemas/`, `routers/master.py`) and the three largest frontend pages (`farmers`, `figs`, `schemes`) into smaller, domain-scoped modules — done as a mechanical, zero-behavior-change refactor since Claude Code is the sole maintainer going forward and smaller files mean cheaper, safer future edits — and (3) add Docker/deployment infrastructure for an AWS EC2 + Supabase UAT deploy.

- ✅ **Phase A — Emergent-sandbox cleanup**: deleted `.emergent/`, `backend/server.py` (Linux-only Postgres bootstrap that shelled out to `apt-get`/`sudo`/`pg_ctlcluster` — Windows dev uses `uvicorn app.main:app` directly), its only test consumer, root `tests/`, `test_reports/`, `test_result.md`, and the inert root `.gitconfig`. Corrected 2 "Emergent OS"/"Emergent Object Storage" mentions in this document's architecture tables to "local disk."
- ✅ **Phase B — Backend module split**, verified zero-behavior-change: `models/__init__.py` (674 lines) → package of 11 domain files; `schemas/__init__.py` (379 lines) → package of 11 domain files; `routers/master.py` (1205 lines, ~79 endpoints across 16 unrelated entities) → package of 6 domain files combined into one `/master`-prefixed router. Every existing `from app.models import X`/`from app.schemas import Y` call site and every `master.router` usage in `main.py` needed **zero changes** — each package's `__init__.py` re-exports everything the monolith used to expose. Verified via `openapi.json` path/method-set diffing (132 paths before, 132 after, zero differences) plus an Alembic-autogenerate diff run against a temporarily-restored copy of the original monolithic file (identical warnings on both sides, proving the split introduced no schema drift), plus curl smoke tests exercising a read + a full create→toggle→delete write cycle on every new submodule.
- ✅ **Phase C — Frontend component extraction**, following the existing `AssetRowsEditor`/`LandRowsEditor` pattern (small, prop-driven, no local data-fetching — the parent page keeps every `useQuery`/`useMutation` and passes data + callbacks down): promoted a shared `ViewField` component out of duplicate copies in `farmers`/`figs`; split `farmers/page.tsx` (860→~330 lines) into `StapGroupPicker`/`FarmerRow`/`FarmerFilterPanel`/`FarmerRegisterModal`/`FarmerEditModal`/`FarmerViewModal`; split `figs/page.tsx` (589 lines) into `FigRow`/`FigFilterPanel`/`FigRegisterModal` plus a `FigDetailModal` shell composing `FigDetailView`/`FigEditForm`/`FigMembersPanel`/`FigPresidentPanel`; split `schemes/page.tsx` (536 lines) into `ActivityPicker`/`SchemeCard`/`SchemeViewModal` plus a `SchemeFormModal` shell composing `SchemeBasicFields`/`SchemeTargetingFields`. Verified via `tsc --noEmit` (clean), `yarn build` (all bundle sizes dropped, e.g. `/figs` 8.56 kB), and a full manual click-through against a production build (`yarn start`, not `yarn dev` — dev-mode Fast Refresh was found to abort in-flight requests mid-test) covering FIG registration, detail view, edit, member add, set/reset president, and deactivate toggle, each confirmed via real network responses and a direct API check.
- ✅ **Phase D — Deployment infrastructure**: `requirements.txt`'s `psycopg2-binary` → `psycopg[binary]>=3.1` (the v3 driver `DATABASE_URL`'s `postgresql+psycopg` dialect actually needs — the old entry only worked locally because both happened to be installed in the dev `.venv`); `CORS_ORIGINS` (previously dead config sitting unused in `.env` while `main.py` hardcoded `allow_origins=["*"]`) now actually drives `CORSMiddleware` via new `Settings.CORS_ORIGINS`; new `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` settings (default 5/5, down from a hardcoded 10/20) for Supabase free-tier connection caps; baseline Alembic migration now runs `CREATE EXTENSION IF NOT EXISTS postgis` as its first statement so a fresh database doesn't fail on `Land.boundary`'s `Geometry` column; new `backend/.env.example`. Added multi-stage, non-root `Dockerfile`s for both apps (frontend's takes `NEXT_PUBLIC_BACKEND_URL` as a build `ARG`, since Next.js bakes `NEXT_PUBLIC_*` vars in at build time), `output: "standalone"` in `next.config.js`, and a root `docker-compose.yml` (backend + frontend services, `backend_uploads` named volume protecting `/data/uploads` against routine container restarts — no S3/DMS, by explicit user decision). CORS verified via curl (`http://localhost:3000` origin gets `Access-Control-Allow-Origin` echoed back, an unlisted origin gets none).
- 📋 **Docker build/compose verification not completed this round**: Docker isn't available in the sandboxed dev environment this work was done in, so `docker build`/`docker compose up`/a fresh-database PostGIS extension test could not actually be run — Dockerfiles and compose config were reviewed but not executed. Needs a real run (locally or on the target EC2 instance) before go-live.
- 📋 **User-caught process mistake**: an unrelated, unauthorized `rm -rf` accidentally deleted the (empty, non-DMS/S3) `backend/file_uploads` local-disk upload directory mid-session; the user confirmed no real data was at risk (UAT, no S3/DMS in use) and the empty directory was recreated. Documented here per the project's standing practice of recording incidents, not to imply any production data was lost.
- 📋 **E2E suite found stale, unrelated to this round's changes**: `frontend/e2e/auth.spec.ts` is 15/16 failing — several test names reference `Sector`/`Stage` entities removed in v3.1, and most tests fail at the shared `login()` helper's `waitForURL` step, suggesting a demo-credential or seed-data mismatch against the current DB. Not touched this round; flagged as a pre-existing gap.

## Latest v3.2 — Asset Management + Scheme Module Redesign (targeting, two-tier selection, notifications) (Jul 2026)

Driven by an Asset Management Feature Spec that assumed Scheme-module infrastructure (Disbursement/UtilizationCheck/multi-stage-workflow tables) which doesn't exist in this codebase — the real Scheme module was flat `Scheme → Allocation → Beneficiary` CRUD. Rather than build the spec's imagined subsystem, the two features were redesigned together around what actually exists, per explicit user decisions: assets are created/verified by DA/SA only (no new "Circle Officer" role, mirrors land GPS verification); no CSV import/legacy-declaration-gate/rollout-dashboard (DA adds existing assets with photos instead); scheme-disbursed assets auto-map to farmer-or-FIG per the asset type's ownership level.

- ✅ **New Asset Management module**: `AssetType` (16-row seeded catalog — rearing houses, mountages, reeling/spinning machines, looms, CFC/CRC shared infrastructure; deliberately excludes host-plant plantations, which are land, and low-value consumables), `AssetInstance` (polymorphic `owner_type`/`owner_id` — farmer or FIG, no DB-level FK, mirrors the existing `User.farmer_id` soft-reference pattern), `AssetVerificationLog` (append-only physical-verification audit trail). `ownership_level` has a third value beyond the spec's binary Individual/FIG — `EITHER` — for the 2 asset types (Reeling Machine, Degumming Unit) the spec itself calls "Individual or FIG," resolved at grant-time to whichever the actual scheme beneficiary is.
- ✅ **Useful-life cooldown is the core mechanic**: `services/assets.py`'s `check_asset_cooldown()` takes `MAX(acquisition_date)` for an owner+asset-type (across every `acquisition_mode` — self-declared, self-procured, or scheme-disbursed all count equally, otherwise pre-digital history would be invisible), compares against `today` vs. `last_acquired + useful_life_years`. An ineligible result is a **flag**, not a hard block — District Admins can override with a mandatory reason (`Beneficiary.cooldown_override_reason`), audited not bypassed.
- ✅ **Assets router** (`/api/assets`) — DA/SA create+verify (owner-district-scoped for DA), FIG President read-only (own FIG + members only). `POST /assets/{id}/verify` writes an append-only log row and updates `status`/`verification_status`. Farmer registration atomically self-declares assets alongside lands (`FarmerIn.assets`, same `db.flush()`-then-loop pattern as the existing land-rows capture); the DA-facing standalone `/assets` page additionally supports evidence photos via the existing `FileUpload`/`category`-folder convention.
- ✅ **Scheme module gains real targeting**: State Admin sets criteria on the `Scheme` itself — `beneficiary_kind` (Farmer or FIG), `target_all_districts`/`target_district_ids`, `target_silk_type_ids`, `target_genders`, `target_farmer_types` (reuses the existing `activity_ids` column for target activities) — every list-valued field follows "empty = no restriction, non-empty = must match" throughout. District Admin then picks actual beneficiaries from the criteria-matched candidate pool within their own district only (`services/scheme_targeting.py`'s `candidate_farmers()`/`candidate_figs()`, each candidate annotated with `already_beneficiary` + a live cooldown check when the scheme has a `grants_asset_type_id`).
- ✅ **Scheme lifecycle**: deactivate-then-archive (`is_archived`/`archived_at`, archived hidden by default, requires already-inactive first — same guard shape as the existing Masters hard-delete), search by name, and `POST /schemes/{id}/publish` which resolves targeted FIG-President+District-Admin users and fans out a notification (`services/notifications.py`'s `create_notification()`, extracted from the inline logic that used to live only in the manual-send endpoint — refactored, not rewritten, so the existing `/notifications` endpoint's behavior is byte-for-byte unchanged).
- ✅ **`Beneficiary` made polymorphic**: `farmer_id` is now nullable, `fig_id` + `beneficiary_type` added. Registering a beneficiary against a scheme with `grants_asset_type_id` set auto-creates the matching `AssetInstance` (`acquisition_mode="SCHEME_DISBURSEMENT"`, linked back via `scheme_id`+`beneficiary_id`) with the owner resolved by `services/assets.py`'s `resolve_owner_for_asset()` — INDIVIDUAL asset types go to the farmer, FIG asset types resolve to the farmer's active FIG membership (or the FIG itself for a FIG-kind scheme), EITHER follows whichever the beneficiary actually is. New `POST /schemes/beneficiaries/bulk` registers many selected candidates in one call with per-row partial-success error reporting.
- ✅ **Route-ordering bug caught and fixed during verification**: FastAPI matches path operations in registration order, so the initial draft's `GET /schemes/{scheme_id}` (registered early) was silently swallowing `GET /schemes/beneficiaries` and `GET /schemes/allocations` (treating "beneficiaries"/"allocations" as a `scheme_id` and 404ing). Fixed by moving every literal-path route before the catch-all `/{scheme_id}` routes, with an explicit comment recorded in `schemes.py` warning future edits not to reintroduce it.
- ✅ **Frontend**: new `masters/asset-types` catalog page (bespoke — silk-type multi-checkbox, ownership/useful-life/scheme-funded fields), new standalone `/assets` page (Add-with-photo + Verify-with-photo modals for DA/SA, read-only table for FP), `AssetRowsEditor`/`AssetsList` components wired into the Farmer Register/Edit/View dialogs' new "Existing Assets (Self-Declared)" section. `schemes/page.tsx` expanded into a full targeting-criteria authoring form (district/silk-type/gender/farmer-type checkboxes, beneficiary-kind + granted-asset selects) plus search, archive, and publish actions; `schemes/beneficiaries/page.tsx` rebuilt around the DA candidate-selection flow — pick a scheme targeting their district, see the matched pool with cooldown badges (eligible/blocked-until-date), multi-select with per-row benefit amount + override-reason field that only appears when a selected row is cooldown-blocked, bulk-register.
- ✅ **Verified end-to-end via curl + in-browser across all 3 roles**: asset-type catalog CRUD lifecycle including the deactivate-before-delete guard; ownership-level mismatch rejected both directions (FIG-only asset → farmer, and vice versa) at both the standalone-page and farmer-registration entry points; district/FIG scoping enforced on every asset endpoint; cooldown math confirmed correct for both farmer-owned and FIG-owned assets; scheme targeting confirmed to correctly narrow the DA candidate pool (gender + silk-type intersection tested with a real farmer, cooldown badge shown); beneficiary registration blocked without an override reason and succeeded with one, auto-creating the correctly-owned asset in both the FARMER and FIG cases; bulk registration's partial-success/per-row-error reporting confirmed with a mix of valid and invalid entries; archive lifecycle (block-while-active → deactivate → archive → hidden-by-default → visible via `include_archived`) confirmed; publish confirmed to create `NotificationRecipient` rows that surface correctly in the FIG President's inbox. `tsc --noEmit` clean, `openapi.d.ts` regenerated.
- 📋 **Not built this round, by explicit user decision**: legacy-data CSV import, mandatory pre-registration asset-declaration gate, and a rollout-completion dashboard (all present in the original spec) — the user opted for DA-driven asset entry with photos instead, since the legacy-capture exercise wasn't needed for this deployment's timeline.

## Latest v3.1 — Sector/Stage Consolidation + District List Correction (Jul 2026)

The State Admin noticed the Masters menu still carried both `Sector`/`Stage` (the original flat masters) and `SilkType`/`Activity`/`Product`/`SilkTypeActivityProduct` (added in Phase 1, bridged only by a `legacy_stage_id` column) — visibly duplicated, never actually merged. Separately flagged that the District master still listed "Karimganj" instead of Assam's real-world renamed "Sribhumi," and was missing 10 districts that exist today. This round removes `Sector`/`Stage` outright and fixes the district list.

- ✅ **`Sector` and `Stage` tables dropped entirely** — `SilkType`/`Activity`/`Product`/`SilkTypeActivityProduct` (STAP) are now the single master. Every former Stage reference (`Fig.stage_id`, `Farmer.stage_ids`/`primary_stage_id`, `Yield_.stage_id`) is repointed to a STAP row directly (`stap_id`/`stap_ids`/`primary_stap_id`) rather than a bare `activity_id` — a bare Activity can't disambiguate silk type or specific product (the same Activity spans all 4 silk types and can map to multiple Products within one), so only the (silk_type, activity, product) triple STAP already captures preserves what Stage used to represent. `Scheme.sector_id`/`stage_id` → `silk_type_id`/`activity_id`; `Training.stage_id` → `activity_id` (both plain Activity FKs — eligibility metadata, not yield records, so full STAP granularity isn't needed there).
- ✅ **One combined expand/migrate/contract Alembic migration** (`35f566bcc2d9`): backfills every new column from the old one via the existing `legacy_stage_id` bridge (raw SQL for scalar FKs, a small Python loop for `Farmer.stap_ids`'s JSON array — easier to verify than a `jsonb_agg` construct at this volume), tightens `figs.stap_id`/`yields.stap_id` to `NOT NULL` only after confirming zero unresolved rows, then drops the old columns/tables. FK/index/unique-constraint names are discovered dynamically via `sa.inspect()` rather than hardcoded, since the baseline migration relied on Postgres auto-naming inconsistently. Verified end-to-end against a `pg_dump`/`pg_restore` copy of the real dev DB before ever touching it live.
- ✅ **`meetings.py`'s legacy_stage_id bridge lookup (`_resolve_activity_product`) deleted** — since `Fig.stap_id`/a client-supplied `stap_id` now point directly at the STAP row, `activity_id`/`product_id` are a direct dereference, no bridge needed. Same simplification in `figs.py`'s `/figs/{id}/byproduct-options`.
- ✅ **District list corrected**: discovered mid-migration that the live dev DB actually already had *both* "Karimganj" and a separately-added "Sribhumi" row (the State Admin had added Sribhumi via the Masters UI ahead of this fix) — the rename migration (`e20a2188b717`) handles both cases, merging Karimganj's dependents into the existing Sribhumi row (with duplicate-safe handling for `blocks`' and `allocations`' unique constraints) when one already exists, or a simple in-place rename otherwise. `seed.py`'s `DISTRICTS` completed to the full, authoritative 35 (10 net-new: Bajali, Baksa, Biswanath, Charaideo, Chirang, Hojai, South Salmara-Mankachar, Tamulpur, Udalguri, West Karbi Anglong), auto-inserted by the existing idempotent `_seed_districts()`.
- ✅ **Frontend repointed throughout**: `masters/sectors`/`masters/stages` pages deleted; Figs/Farmers create+edit forms now show a combined "SilkType · Activity · Product" STAP select/checkboxes instead of a bare Stage dropdown; Non-Primary Yield page (the most Stage-entangled screen) fully rewritten to STAP; Dashboard's Sector bar chart → Silk-type bar chart, "Stages"/"Stages Represented" tiles → "Activities"; Reports' stage-wise production table/chart → product-wise (repointing `_yield_summary_rows()`, confirmed still pending from Phase 3 since the frontend hadn't been touched yet).
- ✅ **Verified end-to-end** via isolated preview instances (fresh `pg_restore` copy + dedicated port, never touching the live dev DB/server): confirmed `/master/sectors`/`/master/stages` now 404, STAP/District/Activity endpoints correct, full migration+seed cycle runs clean, `tsc --noEmit` clean, and in-browser as SA (dashboard "Activities" tile + Silk-type distribution chart, Masters nav, Figs list showing combined STAP labels) and FIG President (Non-Primary Activity Yield page renders with new terminology, zero console errors). Temporary `backend-verify`/`frontend-verify` launch configs and DBs cleaned up afterward.
- ⚠️ **Live dev DB not yet migrated** — the two new Alembic migrations apply automatically the next time the real backend (`uvicorn`, port 8001) is restarted, per this project's existing startup-runs-`alembic upgrade head` behavior. This is a real, one-way schema change to the live dev DB (drops `sectors`/`stages`, merges the live Karimganj+Sribhumi district rows) — flagging explicitly since it wasn't applied during this session, only verified against a disposable copy.

## Latest v3.0 — Dashboard & Reports Rework, Phase 3 (Jul 2026)

Continuation of the v3.0 rework: Phase 3 covers Dashboard/Reports/Analytics, refined mid-flight after the user clarified two concepts that Phase 1+2 hadn't yet separated: **Production** (`Yield_.planned_yield`/`actual_yield`) is a time-bound flow, correctly additive across months and up the Farmer→FIG→Block→District→State hierarchy; **Stock** is a point-in-time level that must never be summed across a period — it only ever reports the *current* balance, filtered by product, with no month/year concept at all.

- ✅ **Stock removed entirely from every production-period endpoint** rather than patched — `reports.py`'s `yield-summary` and `services/analytics.py`'s `_yield_aggregates()`/`_yield_row()` (and all 4 `yields_by_*` functions) dropped the `stock`/`stock_balance` column completely. Production reports are now pure production reports.
- ✅ **Stock gets its own hierarchy**, querying the `Stock` table directly (not `Yield_`): new `stock_by_district/_block/_fig/_farmer` in `services/analytics.py` + `GET /reports/analytics/stock` — filtered only by `product_id`, **no `month`/`fiscal_year` param exists on this endpoint at all**, verified in-browser to return an identical total regardless of when queried.
- ✅ **New product-based production drill-down**: `GET /reports/analytics/products` (sibling to the untouched stage-based `/reports/analytics/yields`, not a mode param — `Product.unit_of_measure` vs `Stage.output_unit` make the two response shapes incompatible). This is now the "Production Explorer" nav target, replacing the old stage-based Yield Explorer; `YieldStockExplorer.tsx` (which was literally the same endpoint re-labeled for "stock" — a known gap flagged back in Phase 1/2) is retired in favor of direct `DrillDownExplorer` usage on `/analytics/products` and a rewritten `/analytics/stock`.
- ✅ **`DrillDownExplorer.tsx` generalized**: `requireStage`/`stages` props replaced by a generic `dimension` config (`label`, `paramName`, `options`, `initialId`, `showPeriodFilter`) so Production (Product + period filter) and Stock (Product, no period filter) share one component. New `initialPath` prop seeds the breadcrumb from a URL param (e.g. `?district_id=`) so a Dashboard link lands the user already-drilled one level down, not at an empty top-level page — verified: clicking a district's onboarding count from the Dashboard lands directly on that district's block-level breakdown with data already showing, zero extra clicks.
- ✅ **`GET /reports/product-summary`** (product-wise production + byproduct totals, `silk_types` resolved as a *list* since products like Woven Fabric/Pupae/Reel Waste are shared across multiple silk types) and **`GET /reports/stock-summary`** (current stock totals per product, no period param) feed new Dashboard tiles (`dashboard/ProductTiles.tsx`), each tile linking to the matching Explorer pre-filtered via `?product_id=`.
- ✅ **Farmer/FIG onboarding trend**: `GET /reports/onboarding-trend` (Farmer uses `created_at`, FIG uses `formation_date` — the real-world onboarding date, more meaningful than the system timestamp), defaults to trailing 12 months, SA state-wide/DA district-scoped/FP 403. New `dashboard/OnboardingSummary.tsx` shows total + this-month delta + a by-district (SA) or by-block (DA, already scoped) breakdown, each row deep-linking into Farmers/FIGs Drill-down.
- ✅ **DFL yield-efficiency** (`GET /reports/analytics/dfl-efficiency`, SA+DA only) pairs each silk type's `"{SilkType} Cocoon"` product with its `"{SilkType} DFL"` product by name-match (excludes `"Cut Cocoon"`) — **flagged as fragile to Product renames via the Master CRUD**; a `Product.dfl_pair_product_id` self-FK is logged as a follow-up hardening, not built this round. **Byproduct-yield-ratio** (`GET /reports/analytics/byproduct-ratio`, SA+DA only) joins `ByproductEntry.parent_yield_id → Yield_.id` grouped by district+product.
- ✅ **Year-on-year trend**: `GET /reports/yoy-trend` (`fiscal_years` repeated query param, 1-6 values, optional `product_id`) feeds a new `MultiSeriesTrendChart` on the Dashboard with a toggleable fiscal-year multi-select.
- ✅ **"Reports" and "Analytics" merged into one "Reports & Analytics" nav group** for SA (11 items) and DA (10 items), per the original design note — every existing href preserved. FIG President's separate "Analytics" group (2 items) is unchanged in name/count, just repointed from the retired Yield Explorer to the new Production Explorer.
- ✅ **Excel/PDF export** — new `backend/app/services/export.py` (`rows_to_xlsx` via `openpyxl`, `rows_to_pdf` via `reportlab.platypus.Table`, numbers only, no charts) + a single `GET /reports/export?report=&format=` dispatcher reusing each report's existing row-fetch function (`_yield_summary_rows`, `_product_summary_rows`, `_stock_summary_rows`, `_district_comparison_rows`, `_scheme_utilization_rows`, `dfl_efficiency_rows`, `byproduct_ratio_by_district`, `_onboarding_trend_rows`) so the export always matches what's on screen. New `frontend/src/lib/export.ts` (blob-fetch + synthetic download) and `ExportButtons.tsx`, wired into all 6 Reports pages that have dedicated UI (`product-summary`/`stock-summary` are Dashboard-tile-only, no dedicated page to attach a button to).
- ✅ **Verified end-to-end** via isolated preview instances across all 3 roles with zero console errors: production/stock endpoints confirmed correctly split (stock period-independent, production still period-scoped), role-gating on every new endpoint (DA allowed, FP 403 where expected), Excel/PDF export downloads confirmed via both curl (file-type + content-match against `openpyxl` read-back) and in-browser click. No test data was created during this round (all verification was read-only).
- 📋 **Roadmap unchanged**: Phases 4–9 (drill-down-stops-at-FIG-with-roster redesign, demand/fulfillment, disease/issue monitoring, scheme eligibility-gap, training attendance, land/rearing-house profile + infrastructure) remain as recorded in the v3.0 Phase 1+2 entry below, not yet started.

## Latest v3.0 — Silk Type/Activity/Product Masters + Byproduct & Stock Rework, Phase 1+2 (Jul 2026)

Driven by a new user-stories document (~87 stories) describing a substantially richer system than what existed. Scoped to **Phase 1+2 only** — the two phases the user's actual complaint ("Dashboard, Reports & Analytics" and "products and stocks") covers; **Phases 3–9 are recorded as a roadmap below**, not yet built.

- ✅ **New master data**: `SilkType`, `Activity`, `Product` (unit-of-measure + `is_perishable` + `is_byproduct` flags), and a `SilkTypeActivityProduct` junction table defining valid (silk type, activity, product) combinations — replacing the old flat `Sector`+`Stage` model's conflation of silk type + activity + unit into one table. All 4 follow the existing `master.py`/`MasterCrud.tsx` CRUD pattern (3 flat masters reuse `MasterCrud` directly; the junction table gets a bespoke page under `/masters/silk-type-activity-products` since it needs 3 cascading FK selects and a grouped-by-silk-type view, not a flat table). `MasterCrud.tsx`'s `FieldType` gained a `"checkbox"` variant for the two boolean Product flags.
- ✅ **Existing data migrated forward, not left behind**: the 12 real seeded `Stage` rows (e.g. "Eri Rearing") got 1:1 mapped to `(SilkType, Activity, Product)` triples via a `legacy_stage_id` bridge column on the mapping table; `Yield_` gained additive nullable `activity_id`/`product_id` columns, backfilled for all existing rows via one SQL `UPDATE...FROM` statement (no Python loop). `Fig.stage_id`/`Farmer.stage_ids`/`Scheme.stage_id`/`Training.stage_id` deliberately kept pointing at the unchanged `stages` table — repointing those to the new structure is out of scope for this round.
- ✅ **Byproducts are now first-class**: new `ByproductEntry` table (`parent_yield_id` linking back to the primary production entry), submitted via a new "Byproducts (optional)" step in the FIG President's monthly submission wizard — options are resolved per-FIG from its silk type via the mapping bridge (`GET /figs/{id}/byproduct-options`), so a Muga FIG only ever sees Pupae/Reel Waste, not Eri's Gicha/Ghicha Yarn.
- ✅ **Stock is now a real, correctly-computed snapshot** — new `Stock` table, one row per (farmer, product), upserted via a single `INSERT...ON CONFLICT DO UPDATE` delta (produced − sold) inline with every production write (`backend/app/services/stock.py`), replacing the old `stock_balance` field which was just a number FIG Presidents typed in monthly and then **summed** (not latest-value) across every report. A one-time backfill recomputed real opening stock from all existing `Yield_` history, discarding the old untrustworthy values. Perishable age (`age_days`) is computed **in SQL** (`now() - last_entry_at`) rather than in Python — discovered during verification that the Postgres session runs in `Asia/Calcutta`, silently converting tz-aware UTC timestamps to IST wall-clock on write into timezone-naive columns; a Python-side `datetime.now(timezone.utc)` diff against the stored value produced a negative age. Doing the diff in SQL sidesteps the ambiguity entirely.
- ✅ **Fixed a real, previously-silent bug**: the submission wizard had no "Planned" input field at all, so `Yield_.planned_yield` was always persisted as `0` — meaning every planned-vs-actual / yield-achievement-% comparison anywhere in the app was against a dead zero baseline. Both the primary wizard (`submission/page.tsx`) and non-primary page now show a "Planned" column prefilled from the previous month's `next_month_plan`.
- ✅ **Verified end-to-end** via isolated preview instances: full submission flow (Planned prefill → Yield & stock → Byproducts → Review → Submit) exercised in-browser as FIG President, confirmed via direct DB inspection that `Yield_.activity_id`/`product_id` resolve correctly, `Stock.closing_balance` accumulates correctly across two consecutive months (35 → 75) rather than resetting, byproduct stock (Pupae, `is_perishable=true`) computed separately from primary product stock (Muga Cocoon, `is_perishable=false`); role-gating (SA-only masters, DA/FP both 403) and FK-conflict delete-guard on a referenced Product all confirmed; all test data cleaned up afterward.
- 📋 **Backlog roadmap recorded (not built this round)**: Phase 3 (dashboard/reports rework — fix the `SUM`→latest-value stock bug in `analytics.py`/`reports.py`, product-type production totals, yield-efficiency/byproduct-ratio views, consolidate Reports+Analytics into one menu item); Phase 4 (analytics drill-down redesign — stop at FIG level with an on-demand farmer roster instead of auto-drilling to a farmer-aggregate terminal level; today Farmers/FIGs/Lands explorers only reach block level, never FIG); Phase 5 (demand & fulfillment matching, perishables excluded); Phase 6 (disease/issue monitoring with heatmaps); Phase 7 (structured scheme eligibility criteria + "eligible but not availed" gap reporting); Phase 8 (training session attendance, mirroring the `Meeting`/`Attendance` pattern); Phase 9 (farmer land/rearing-house profile enrichment + infrastructure reporting + exports).

## Latest v2.9 — Hard Delete for Masters (Jul 2026)
- ✅ **Masters (Sectors, Stages, Districts, Sericulture Blocks, Caste, Religion) now support permanent delete**, not just soft-disable. New `delete_or_conflict(db, row, msg)` helper in `backend/app/core/db.py` (sibling to `commit_or_conflict`) catches Postgres FK `IntegrityError`s and turns them into a friendly `400` instead of a raw 500.
- ✅ **6 new `DELETE /api/master/{entity}/{id}` endpoints** in `master.py`, State-Admin-only (existing `_SA` dependency, unchanged for DA/FP), each requiring the row to already be `is_active=false` (400 "Deactivate ... before deleting" otherwise) and reporting exactly which dependent records block the delete (e.g. deleting a referenced Stage names "FIGs, yield records, schemes, or training requests").
- ✅ **Frontend**: `MasterCrud.tsx` (drives all 6 Masters pages) gained a destructive "Delete" button, shown only once a row is deactivated, gated behind a `window.confirm()` naming the record — matches the existing single-confirm-dialog convention used elsewhere (e.g. retracting a notification). No changes needed to the 6 individual page files.
- ✅ **Verified end-to-end** via isolated preview instances: active-row delete blocked, full create→deactivate→delete UI flow (confirm dialog fires with correct message, row disappears, row actually gone from DB), FK-conflict path tested against a real referenced Stage (restored afterward), DA/FP both 403 on the new endpoints.

## Latest v2.8 — Performance Fixes + Analytics Drill-Down Module (Jul 2026)
- ✅ **Root-caused "slow after login / slow every page" complaint**: the app had never been run as a production build — `frontend/package.json`'s `start` script silently ran `next dev` (JIT-compiles each route on first visit). Fixed the script to run `next start`; `CLAUDE.md` now documents build-vs-dev explicitly. Backend `--reload` also flagged as dev-only overhead.
- ✅ **Frontend bundle**: `recharts` (dashboard + reports) now dynamically imported (`ssr:false`), mirroring the existing `GpsMap` pattern; `next.config.js` gets `experimental.optimizePackageImports` for `@phosphor-icons/react` (imported via a root barrel in the always-mounted `AppShell`).
- ✅ **Backend query cleanup**: `district-comparison` and `scheme-utilization` rewritten from Python-side full-table aggregation loops to single SQL `GROUP BY`/`JOIN` queries — same anti-pattern the new Analytics module was built to avoid from day one.
- ✅ **New Analytics module** — breadcrumb drill-down explorers for Farmers, FIGs, Lands (District → Block) and Yields/Stock (District → Block → FIG → Farmer, one Stage selected at a time so units never mix). New `backend/app/services/analytics.py` + `backend/app/routers/analytics.py` (4 endpoints under `/reports/analytics`), new `frontend/src/components/DrillDownExplorer.tsx` + 5 thin pages under `/analytics/*`. Role scoping: SA sees everything; DA is pinned to their own district (starts one level in); FP only gets Yield/Stock at farmer level, pinned to their own FIG — Farmers/FIGs/Lands return a flat 403 for FP. New indexes: `Fig.block_id`, composite `(stage_id, yield_month, fig_id)` on `yields` (migration `30a6b671695c`).
- ✅ **Mobile app / external API readiness assessed** (not implemented this round): backend is fully decoupled JSON+JWT, directly usable by a React Native/Flutter FIG President app as-is. Gaps flagged for before wider exposure — no service-account/API-key auth for third-party integrations (only human login exists), no rate limiting beyond login, `POST /lands`+`POST /lands/gps` don't verify the target farmer belongs to the caller's FIG, `GET /figs/{id}` has the same unscoped-by-ID gap as the already-documented `GET /farmers/{id}`.

## Latest v2.7 — Fiscal-Year Reporting + Data Integrity Fixes (Jul 2026)
- ✅ **Fiscal-year (April–March) support** — new `backend/app/services/fiscal.py` (`month_to_fy`/`fy_to_months`); `GET /reports/yield-summary` and `GET /reports/monthly-trend` now accept `fiscal_year` alongside `month` (mutually exclusive); `GET /yields` (meetings.py) got the same treatment.
- ✅ **Two new reports**: `GET /reports/scheme-utilization` (budget vs. allocated vs. disbursed, per scheme + per district, role-scoped) and `GET /reports/district-comparison` (SA-only; submission rate + yield achievement for the selected period, GPS-verified % and scheme-utilization % as all-time snapshots) — new pages `/reports/scheme-utilization` and `/reports/district-comparison`, Reports sidebar entry is now a collapsible group for SA/DA.
- ✅ **Over-allocation guard**: allocating beyond a scheme's `total_budget_rs` is now allowed but returns a `warning` in the response, surfaced as a toast on `/schemes/allocations`.
- ✅ **Beneficiary registration now requires an existing allocation** for that scheme+district (400 if missing) and rejects amounts exceeding the remaining balance (400) — closes two of the items from the code-audit "Known issues" below.
- ✅ **`Fig.total_members` is no longer a stored counter** — computed live from `fig_members` in `list_figs`/`get_fig`; column dropped via Alembic migration `3739ad1dcf6c`. Eliminates the drift risk noted in the code audit.
- ✅ **`_commit_or_conflict` extracted** from `master.py` into `core/db.py` as `commit_or_conflict`, now shared with `schemes.py`'s allocation-create endpoint (defense-in-depth against duplicate scheme+district races).

## Latest v2.6 — Critical Fix: PostgreSQL Data Persistence (Feb 2026)
- 🔴 **Root cause**: `/var/lib/postgresql/15/main` sat on the container's ephemeral overlay FS. Every pod restart wiped it; the bootstrap re-installed PG and reseeded a fresh DB, so user-created records disappeared.
- ✅ **Fix**: `server.py` bootstrap now relocates the PG cluster to the persistent volume at `/data/db/postgres15` and keeps `/var/lib/postgresql/15/main` as a symlink. Three cases handled idempotently:
  1. Symlink already correct → no-op.
  2. Persistent volume has data → discard freshly-installed ephemeral cluster and symlink.
  3. First bootstrap → move the fresh cluster to the persistent volume and symlink.
- ✅ **Applied to the running system** without waiting for a pod restart (stop backend + PG, `mv`, symlink, chown, restart).
- ✅ **Verified via new pytest suite** `/app/backend/tests/test_persistence.py`: SA + DA created via API survive a simulated pod restart (stop backend + PG, wipe `/var/lib/postgresql/15/main`, re-run `relocate_pg_data_to_persistent()`, restart everything).
- ✅ **E2E regression**: 17/17 Playwright tests still passing (~95s). Fixed a flaky `waitForLoadState("networkidle")` in the page-render test — now uses `domcontentloaded` + explicit `h1` visibility check.

## Latest v2.5 — State Admins Sub-menu (Feb 2026)
- ✅ Added **State Admins** sub-menu under `User Management` for SA role (first in the group).
- ✅ New backend endpoint `POST /api/users/state-admin` (SA-only) — create additional State Admin accounts.
- ✅ Enhanced `PATCH /api/users/{id}/active` to reject deactivating the **last active State Admin** (system safety).
- ✅ New page `/users/state-admins` with Add / Edit (name / mobile / password) / Activate / Deactivate. Self-account is badged "You" and its deactivate button is disabled.
- ✅ E2E suite grew from 16 → 17 tests, all passing (~123s).

## Latest v2.4 — Full Sidebar Restructure + User & Scheme CRUD (Feb 2026)
- ✅ **All 3 role sidebars restructured** with collapsible groups for every group with ≥2 items:
  - **SA**: Masters (6), Farmers & FIGs (2), Meetings & Yield (2), Schemes (3: Management / Allocations / Beneficiaries), User Management (2: District Admins / FIG Presidents). Single-item groups (Dashboard, Land & GIS, Training, Notifications, Reports) stay flat for cleaner UX.
  - **DA**: Farmers & FIGs (2), Meetings & Yield (2), Schemes (2: Beneficiaries / District Allocations). Others flat.
  - **FP**: Monthly Submission (2). Others flat.
- ✅ **Active-link detection now uses longest-prefix match** so `/schemes/allocations` no longer marks `/schemes` (parent) as active.
- ✅ **New backend CRUD endpoints** (SA-only):
  - `PATCH /api/users/{id}`, `PATCH /api/users/{id}/active`, `GET /api/users?all=true` — edit any user, activate/deactivate, self-deactivation blocked, one-active-DA-per-district guard.
  - `PATCH /api/schemes/{id}`, `PATCH /api/schemes/{id}/active`, `GET /api/schemes?all=true` — edit scheme fields, toggle active, include inactive in admin list.
- ✅ **New / rewritten frontend pages** with full Add/Edit/Activate-Deactivate UI:
  - `/users` — District Admins with create + edit (name, mobile, password, district) + toggle.
  - `/users/fig-presidents` — FIG Presidents list with edit + toggle (accounts still auto-created via FIG assignment).
  - `/schemes` — Scheme Management (card grid) with Add / Edit / Deactivate for SA, read-only for DA.
  - `/schemes/allocations` — District-wise allocations with Add for SA.
  - `/schemes/beneficiaries` — Beneficiary registration (SA + DA), auto-deducts from allocation.
- ✅ **E2E suite grew from 11 → 16 tests** (all passing in ~104s):
  - Expand all collapsible groups in SA sidebar and verify sub-items
  - DA sees collapsible Schemes group with Beneficiaries + District Allocations
  - FP Monthly Submission expandable
  - Scheme: create → edit budget → deactivate → reactivate
  - Allocations + Beneficiaries pages render
  - DA list page + FP toggle-active flow

## Latest v2.3 — Masters Menu Restructure + CRUD UI (Feb 2026)
- ✅ **Sidebar Masters group is now expandable/collapsible** with 6 sub-menu items: Sectors, Stages, Districts, Sericulture Blocks, Caste, Religion. Auto-expands when the current route is under `/masters/*`.
- ✅ **Schemes removed** from Masters (Schemes remains under its own top-level menu — it is not a master).
- ✅ **Full CRUD UI** for each master (State Admin only): Add / Edit / Activate / Deactivate. Backed by new endpoints:
  - `POST /api/master/{sectors|stages|districts|blocks|castes|religions}` (SA-only)
  - `PATCH /api/master/{entity}/{id}` (SA-only)
  - `PATCH /api/master/{entity}/{id}/active` (SA-only)
  - `GET /api/master/{entity}?all=true` — includes inactive rows for admin views
- ✅ **New pages**: `/masters/sectors`, `/masters/stages`, `/masters/districts`, `/masters/blocks`, `/masters/caste`, `/masters/religion`. Old `/masters` now redirects to `/masters/sectors`.
- ✅ **Shared component** `components/MasterCrud.tsx` — one reusable table/form driver with `data-testid` on every interactive element.
- ✅ **E2E suite grew from 8 → 11 tests** (all passing in ~75s):
  - Sidebar Masters group expand + verify all 6 sub-items visible
  - Sector: create → deactivate → reactivate flow
  - Stage: create bound to a sector
  - DA users blocked from Masters CRUD (menu group hidden)
- Regenerated `src/lib/openapi.d.ts` via `yarn types:gen`.

## Latest v2.2 — Code Quality Cleanup (Feb 2026)
- ✅ **Ruff lint clean**: Removed all 32 E701/E702/E741 warnings across 9 routers (farmers, figs, lands, meetings, notifications, schemes, trainings, users, upload). Split multi-statement lines and renamed ambiguous `l` → `land`/`ld` in `app/routers/lands.py`.
- ✅ **E2E regression clean**: Playwright 8/8 still passing (~41s) after cleanup.
- Note: `is None`/`is not None` idioms in `reports.py:58` and `alembic/env.py:20` were verified as **correct PEP 8** (constant-comparison rule applies to values, not `None`).

## Latest v2.1 — All 5 Backlog Items Delivered
1. ✅ **Alembic baseline migration** — `alembic/versions/82b4b3356c50_baseline.py` creates all 21 tables. Startup runs `alembic upgrade head` instead of `metadata.create_all`. PostGIS system tables excluded via `include_object` filter. GeoAlchemy2 import auto-included in templates.
2. ✅ **`openapi-typescript` autogen** — `yarn types:gen` fetches `/openapi.json` → 2583-line `src/lib/openapi.d.ts`. Re-exported via `lib/api-types.ts`.
3. ✅ **File-upload UI** — reusable `<FileUpload>` component. Wired into:
   - Farmers form (photo + bank passbook + account details)
   - Notifications form (attachment)
   - Attachment view link in inbox with auth token in query string
4. ✅ **Playwright E2E suite** — 8/8 tests passing in 45s:
   - Invalid credentials reject
   - SA/DA/FP login + role-scoped sidebar
   - Logout flow
   - Multi-page navigation (Farmers, FIGs, Schemes, Reports)
   - Notifications inbox
   - Monthly Submission wizard renders
5. ✅ **Selected-recipient picker** — Notifications form now offers `SELECTED_DA` and `SELECTED_FP` options. Surfaces a scrollable checkbox picker showing user name + district. State Admin sees all DAs/FPs across districts; District Admin sees only FPs in their district.

## Demo Credentials (`/app/memory/test_credentials.md`)
| Role | Mobile | Password |
|---|---|---|
| State Admin | `9999999999` | `Admin@123` |
| District Admin | `8888888888` | `District@123` |
| FIG President | `7777777777` | `Fig@123` |

## Verification Summary
| Test | Result |
|---|---|
| Backend `/api/auth/login` 3 roles | ✅ All return JWT + refresh + user object |
| Refresh-token rotation | ✅ |
| Rate limit (5/min) on login | ✅ 4th bad attempt → 429 |
| Role enforcement (FP → POST /api/farmers) | ✅ 403 |
| Master endpoints (sectors, stages, districts) | ✅ Seeded counts match |
| File upload to Emergent OS | ✅ Returns object path |
| Alembic upgrade head | ✅ Creates all 21 tables clean |
| Playwright E2E 8/8 | ✅ Passed in 45s |
| Frontend dashboard renders with sidebar | ✅ |

## Backlog (P1 — next)
- Refresh-token blocklist / Redis store
- District-wise comparison report + PDF export
- Stock-position report
- Annual report module
- Pagination + advanced filters on tables
- Auto-aggregation tables (district + state level monthly snapshots)
- GitHub Actions CI workflow (pytest + next build + playwright)
- Farmer auto-inactivation when not part of any active FIG

### Known issues (code audit, Jul 2026)
Found via a full backend code audit. Three items originally listed here (duplicate-allocation `IntegrityError` handling, negative `Allocation.remaining`, `Fig.total_members` drift) were fixed in v2.7 above — removed from this list. Remaining, not yet fixed:
- `master.py` read endpoints and `schemes.py`'s `GET ""` have no `Depends(get_current_user)` at all — effectively public/unauthenticated reads, despite `master.py`'s own docstring claiming "public to any authenticated user."
- `GET /farmers/{farmer_id}` has no role/district scope check — inconsistent with the scoped `GET /farmers` list endpoint; a DISTRICT_ADMIN or FIG_PRESIDENT can fetch another district's farmer by ID directly.
- `trainings.complete` doesn't verify the completing DA matches the training's district/requester — any DISTRICT_ADMIN could complete another district's approved training.
- `notifications` `ALL_DA_AND_FP` and `SELECTED_*` recipient types bypass the DA-district-scoping that's enforced on `ALL_FP`/`ALL_DA` — a DA could notify users outside their district via those paths.
- `Meeting`/`Yield_` models have a `submission_status` field that's never transitioned away from the default `"Submitted"` anywhere in the routers — looks like an incomplete/abandoned draft-approval workflow.
- `GET /figs/{fig_id}` has no role/district scope check, same class of gap as `GET /farmers/{farmer_id}` above (found during the mobile/external-API readiness assessment, v2.8).
- `POST /lands` and `POST /lands/gps` accept a `FIG_PRESIDENT` role but never verify the target farmer belongs to the caller's own FIG (v2.8).
- No API-key/service-account/OAuth2-client-credentials auth exists anywhere — the only auth mechanism is human mobile+password login. Fine for a first-party FIG President mobile app; a real gap before granting any third-party external portal write access (v2.8).
- No rate limiting on any endpoint except login — write endpoints (farmer/FIG/meeting creation, etc.) are fully unthrottled (v2.8).
