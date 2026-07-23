"""One-time script: wipe all Activities, Products, Farmers, and FIGs (plus everything
that depends on them) so State Admin can build real data from scratch through the UI.

Districts, Sericulture Circles, Sub-division/CDC offices, Silk Types, Castes, Religions,
Loss Reasons, Schemes/Allocations, FigSettings, DirectorateOffice, and State/District Admin
logins are all left untouched.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/reset_transactional_data.py --confirm
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.db import SessionLocal

# Order matters: each step clears rows that would otherwise FK-violate the next one.
STEPS = [
    ("Detach Training rows from Activities (Training itself is preserved)",
     'UPDATE trainings SET activity_id = NULL'),
    ("Delete Stock", 'DELETE FROM stock'),
    ("Delete ByproductEntry", 'DELETE FROM byproduct_entries'),
    ("Delete YieldInputEntry", 'DELETE FROM yield_input_entries'),
    ("Delete Yield_", 'DELETE FROM yields'),
    ("Delete Attendance", 'DELETE FROM attendance'),
    ("Delete Meeting", 'DELETE FROM meetings'),
    ("Delete Land", 'DELETE FROM lands'),
    ("Delete Beneficiary", 'DELETE FROM beneficiaries'),
    ("Delete FigMember", 'DELETE FROM fig_members'),
    ("Delete files uploaded by FIG_PRESIDENT users (FK blocks user delete)",
     "DELETE FROM files WHERE uploaded_by IN (SELECT id FROM users WHERE role = 'FIG_PRESIDENT')"),
    ("Delete notification_recipients addressed to FIG_PRESIDENT users (FK blocks user delete)",
     "DELETE FROM notification_recipients WHERE recipient_user_id IN (SELECT id FROM users WHERE role = 'FIG_PRESIDENT')"),
    ("Delete FIG_PRESIDENT logins (must precede Fig delete, real FK)",
     "DELETE FROM users WHERE role = 'FIG_PRESIDENT'"),
    ("Delete Fig", 'DELETE FROM figs'),
    ("Delete Farmer (farmers.primary_stap_id FKs into STAP, must precede its delete)",
     'DELETE FROM farmers'),
    ("Delete SilkTypeActivityProduct (hard FK to both activities and products)",
     'DELETE FROM silk_type_activity_products'),
    ("Delete Activity", 'DELETE FROM activities'),
    ("Delete Product", 'DELETE FROM products'),
]


def main() -> None:
    if "--confirm" not in sys.argv:
        print("This permanently deletes all Activities, Products, Farmers, and FIGs")
        print("(plus dependent yields/byproducts/stock/lands/meetings/scheme beneficiaries).")
        print("Districts, Circles, Silk Types, Schemes, and Admin logins are preserved.")
        print("Re-run with --confirm to proceed.")
        sys.exit(1)

    db = SessionLocal()
    try:
        for label, sql in STEPS:
            result = db.execute(text(sql))
            print(f"{label}: {result.rowcount} row(s) affected")
        db.commit()
        print("\nReset complete.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
