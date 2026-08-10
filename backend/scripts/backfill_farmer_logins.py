"""One-time script: create a FARMER login (mobile + default password "farmer@123") for every
existing Farmer that doesn't already have one, so the farmer-login feature applies retroactively
instead of only to newly-registered farmers.

Safe to re-run — already-provisioned farmers (and farmers who already have some other login, e.g.
a FIG_PRESIDENT account under the same mobile) are skipped, never overwritten or duplicated.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/backfill_farmer_logins.py --confirm
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.core.security import hash_password, DEFAULT_FARMER_PASSWORD
from app.models import Farmer, User

if "--confirm" not in sys.argv:
    print(__doc__)
    print("Refusing to run without --confirm (this creates real login accounts).")
    sys.exit(1)

db = SessionLocal()
try:
    farmers = db.query(Farmer).all()
    existing_logins_by_farmer = {
        u.farmer_id: u for u in db.query(User).filter(User.farmer_id.isnot(None)).all()
    }
    existing_mobiles = {u.mobile_no for u in db.query(User).all()}

    created = 0
    already_had_login = 0
    skipped_collisions: list[tuple[Farmer, User]] = []

    for f in farmers:
        if f.id in existing_logins_by_farmer:
            already_had_login += 1
            continue
        if f.mobile_no in existing_mobiles:
            colliding = db.query(User).filter(User.mobile_no == f.mobile_no).first()
            skipped_collisions.append((f, colliding))
            continue
        db.add(User(
            mobile_no=f.mobile_no, password_hash=hash_password(DEFAULT_FARMER_PASSWORD),
            role="FARMER", farmer_id=f.id, district_id=f.district_id,
            name=f"{f.first_name} {f.last_name}".strip(),
        ))
        existing_mobiles.add(f.mobile_no)
        created += 1

    db.commit()

    print(f"Total farmers: {len(farmers)}")
    print(f"Created new FARMER logins: {created}")
    print(f"Already had a login: {already_had_login}")
    print(f"Skipped (mobile collision): {len(skipped_collisions)}")
    for f, colliding in skipped_collisions:
        print(f"  - {f.farmer_code} ({f.mobile_no}) — mobile already used by {colliding.role} login {colliding.id}")
finally:
    db.close()
