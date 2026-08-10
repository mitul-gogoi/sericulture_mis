"""One-time script: wipe all Conversion Standard rows so they can be reseeded from a
corrected, scope-accurate dataset (see seed_conversion_standards_full.py). Nothing else
is touched — no Farmer/FIG/Yield data references ConversionStandard by FK.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/reset_conversion_standards.py --confirm
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models import ConversionStandard


def main() -> None:
    if "--confirm" not in sys.argv:
        print("This permanently deletes all Conversion Standard rows.")
        print("Re-run with --confirm to proceed.")
        sys.exit(1)

    db = SessionLocal()
    try:
        rows = db.query(ConversionStandard).all()
        for r in rows:
            db.delete(r)
        db.commit()
        print(f"Deleted {len(rows)} Conversion Standard row(s).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
