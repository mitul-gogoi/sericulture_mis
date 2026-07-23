"""One-time script: wipe EVERY transactional/user table, keeping only the State Admin's
Master Data (Directorate Office, Districts, Sub-division/CDC, Sericulture Circles, Caste,
Religion, Education Level, Silk Types, Activities, Products, Map Activity to Product / STAP
+ its source-type links, Loss Reasons, Input Source Categories, Input Source Types, Asset
Types, and FigSettings/"Minimum FIG Members"). All Users are deleted and replaced with a
single fresh State Admin login.

Unlike scripts/reset_transactional_data.py (which preserves Activities/Products/STAP so a
partially-built catalog survives), this script keeps ALL Master Data and wipes every
farmer/FIG/user/submission/scheme/asset/notification/file row on top of that.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/reset_all_except_masters.py --confirm
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.db import SessionLocal
from app.core.security import hash_password

NEW_ADMIN = {"name": "Director", "mobile_no": "1111111111", "password": "sa@123"}

# Order matters: each step clears rows that would otherwise FK-violate the next one.
# Master Data tables (districts, silk_types, activities, products,
# silk_type_activity_products, stap_source_types, loss_reasons, input_source_categories,
# input_source_types, asset_types, caste, religion, education_levels, sericulture_circles,
# subdivision_cdc_offices, directorate_offices, fig_settings) are never touched below.
STEPS = [
    ("Delete NotificationRecipient", 'DELETE FROM notification_recipients'),
    ("Delete Notification", 'DELETE FROM notifications'),
    ("Delete FileRecord", 'DELETE FROM files'),
    ("Delete AssetVerificationLog", 'DELETE FROM asset_verification_logs'),
    ("Delete YieldInputEntry (references yields + schemes)", 'DELETE FROM yield_input_entries'),
    ("Delete Stock (references yields + byproduct_entries)", 'DELETE FROM stock'),
    ("Delete ByproductEntry (references yields)", 'DELETE FROM byproduct_entries'),
    ("Delete AssetInstance (references schemes + beneficiaries)", 'DELETE FROM asset_instances'),
    ("Delete Beneficiary (references schemes, farmers, figs)", 'DELETE FROM beneficiaries'),
    ("Delete Allocation (references schemes)", 'DELETE FROM allocations'),
    ("Delete Scheme", 'DELETE FROM schemes'),
    ("Delete Attendance (references meetings, figs, farmers)", 'DELETE FROM attendance'),
    ("Delete Yield_ (references figs, farmers, meetings)", 'DELETE FROM yields'),
    ("Delete Training (references users)", 'DELETE FROM trainings'),
    ("Delete Meeting (references figs)", 'DELETE FROM meetings'),
    ("Delete Land (references farmers)", 'DELETE FROM lands'),
    ("Delete FigMember (references figs, farmers)", 'DELETE FROM fig_members'),
    ("Delete all Users (references figs — must precede Fig delete)", 'DELETE FROM users'),
    ("Delete Fig", 'DELETE FROM figs'),
    ("Delete Farmer", 'DELETE FROM farmers'),
]


def main() -> None:
    if "--confirm" not in sys.argv:
        print("This permanently deletes ALL farmers, FIGs, users, meetings, yields,")
        print("schemes, assets, notifications, and files. Master Data (Districts, Silk")
        print("Types, Activities, Products, STAP, Loss Reasons, Input Source")
        print("Categories/Types, Asset Types, Caste, Religion, Education Level,")
        print("Sericulture Circles, Sub-division/CDC, Directorate Office, FigSettings)")
        print("is preserved. A single new State Admin login is created afterward.")
        print("Re-run with --confirm to proceed.")
        sys.exit(1)

    db = SessionLocal()
    try:
        for label, sql in STEPS:
            result = db.execute(text(sql))
            print(f"{label}: {result.rowcount} row(s) affected")

        db.execute(
            text(
                "INSERT INTO users (id, mobile_no, password_hash, role, name, "
                "district_id, fig_id, farmer_id, failed_attempts, is_active, "
                "created_at, updated_at) "
                "VALUES (:id, :mobile_no, :password_hash, "
                "'STATE_ADMIN', :name, NULL, NULL, NULL, 0, true, now(), now())"
            ),
            {
                "id": str(uuid.uuid4()),
                "mobile_no": NEW_ADMIN["mobile_no"],
                "password_hash": hash_password(NEW_ADMIN["password"]),
                "name": NEW_ADMIN["name"],
            },
        )
        print(f"\nCreated new State Admin: {NEW_ADMIN['name']} / {NEW_ADMIN['mobile_no']}")

        db.commit()
        print("Reset complete.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
