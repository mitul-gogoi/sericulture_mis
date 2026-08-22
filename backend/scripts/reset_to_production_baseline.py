"""Reset this database to the shape production is in: master data and admin logins only.

Production carries no farmers or FIGs, and therefore no monthly submissions, land/GIS,
assets, trainings, schemes or notifications. This brings a working database back to that
state so testing starts from the same baseline.

WHAT SURVIVES
    Every master-data table — Directorate Office, Districts, LACs, Designations, Caste,
    Religion, Education Level, Silk Types, Activities, Products, Map Activity to Product,
    Conversion Standards, Loss Reasons, Input Source Categories/Types, Asset Types and the
    Minimum FIG Members setting — plus every STATE_ADMIN and DISTRICT_ADMIN login.

WHAT GOES
    All transactional data, the FARMER and FIG_PRESIDENT logins that hang off farmers, and
    **all Sericulture Circles** — those are rebuilt from app/seed.py's CIRCLES on the next
    boot, which is what loads the Directorate's current mapping sheet.

ORDER
    Derived from the live foreign-key graph, not guessed. Three edges are easy to miss and
    each one aborts the run if got wrong:
      * `stock` FKs `yields` and `byproduct_entries` via last_source_* — stock goes first.
      * `asset_instances` points at farmers through a polymorphic owner_type/owner_id with
        NO foreign key, so it never shows up in a FK query.
      * FIG President logins have *sent* notifications, and notifications.sent_by_user_id
        FKs users — so notifications must go before the logins do.

    Everything runs in one transaction: a wrong edge rolls the whole thing back rather than
    leaving the database half-wiped.

Usage:  python scripts/reset_to_production_baseline.py --confirm
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402

FARMER_ROLES = "('FARMER', 'FIG_PRESIDENT')"

STEPS = [
    # --- assets (asset_instances has no FK to farmers — polymorphic owner) ---
    ("Asset verification logs", "DELETE FROM asset_verification_logs"),
    ("Asset GPS drafts", "DELETE FROM asset_gps_drafts"),
    ("Land GPS drafts", "DELETE FROM land_gps_drafts"),
    ("Assets", "DELETE FROM asset_instances"),

    # --- schemes & training (trainings reference schemes, so they go first) ---
    ("Training certificates", "DELETE FROM training_certificates"),
    ("Training attendance", "DELETE FROM training_attendance"),
    ("Scheme beneficiaries", "DELETE FROM beneficiaries"),
    ("Scheme allocations", "DELETE FROM allocations"),
    ("Trainings", "DELETE FROM trainings"),
    ("Schemes", "DELETE FROM schemes"),

    # --- farmer self-submission (Phase AJ) ---
    ("Farmer submission corrections", "DELETE FROM farmer_submission_corrections"),
    ("Farmer submissions", "DELETE FROM farmer_submissions"),
    ("Farmer draft entries", "DELETE FROM farmer_draft_entries"),
    ("Meeting corrections", "DELETE FROM meeting_corrections"),

    # --- production data: stock BEFORE the rows its last_source_* columns point at ---
    ("Stock", "DELETE FROM stock"),
    ("Yield input entries", "DELETE FROM yield_input_entries"),
    ("Byproduct entries", "DELETE FROM byproduct_entries"),
    ("Yields", "DELETE FROM yields"),
    ("Meeting attendance", "DELETE FROM attendance"),
    ("Meetings", "DELETE FROM meetings"),

    # --- land, membership ---
    ("Lands", "DELETE FROM lands"),
    ("FIG members", "DELETE FROM fig_members"),
    ("FIG activities", "DELETE FROM fig_activities"),

    # --- notifications & files (none in production) ---
    ("Notification recipients", "DELETE FROM notification_recipients"),
    ("Notifications", "DELETE FROM notifications"),
    ("Uploaded files", "DELETE FROM files"),

    # --- the logins that belong to farmers / FIG presidents ---
    ("District assignments for farmer logins",
     f"DELETE FROM user_districts WHERE user_id IN (SELECT id FROM users WHERE role IN {FARMER_ROLES})"),
    ("Farmer and FIG President logins",
     f"DELETE FROM users WHERE role IN {FARMER_ROLES}"),

    # --- and finally the records themselves ---
    ("FIGs", "DELETE FROM figs"),
    ("Farmers", "DELETE FROM farmers"),

    # Rebuilt from app/seed.py's CIRCLES on the next boot. Must come after farmers, lands
    # and stock, all of which reference a circle.
    ("Sericulture Circles (rebuilt from seed.py on next boot)", "DELETE FROM sericulture_circles"),
]

# Asserted afterwards so a wipe that overreaches into master data is caught here rather
# than discovered later by a confused user.
MUST_SURVIVE = [
    "directorate_office", "districts", "lacs", "designations", "castes", "religions",
    "education_levels", "silk_types", "activities", "products",
    "silk_type_activity_products", "conversion_standards", "loss_reasons",
    "input_source_categories", "input_source_types", "asset_types", "fig_settings",
]


def main() -> None:
    if "--confirm" not in sys.argv:
        print(__doc__)
        print("Refusing to run without --confirm.")
        sys.exit(1)

    db = SessionLocal()
    try:
        before = {t: db.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                  for t in MUST_SURVIVE}
        admins_before = db.execute(text(
            "SELECT count(*) FROM users WHERE role IN ('STATE_ADMIN','DISTRICT_ADMIN')")).scalar()

        print("Deleting:")
        total = 0
        for label, sql in STEPS:
            n = db.execute(text(sql)).rowcount
            total += max(n, 0)
            print(f"   {label:<52} {n:>5}")
        db.commit()
        print(f"\n   {'total rows removed':<52} {total:>5}")

        after = {t: db.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                 for t in MUST_SURVIVE}
        admins_after = db.execute(text(
            "SELECT count(*) FROM users WHERE role IN ('STATE_ADMIN','DISTRICT_ADMIN')")).scalar()

        print("\nMaster data (must be unchanged):")
        drift = [t for t in MUST_SURVIVE if before[t] != after[t]]
        for t in MUST_SURVIVE:
            flag = "  <-- CHANGED" if before[t] != after[t] else ""
            print(f"   {t:<34} {after[t]:>5}{flag}")
        print(f"\n   admin logins kept: {admins_after} (was {admins_before})")

        if drift or admins_after != admins_before:
            print("\nWARNING: something outside the wipe list changed — investigate before use.")
        else:
            print("\nDone. Restart the backend: seed.py will rebuild the Sericulture Circles "
                  "and map each to its LAC.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
