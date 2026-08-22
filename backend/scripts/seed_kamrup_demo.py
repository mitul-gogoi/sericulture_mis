"""One-time script: remove the leftover "Test" farmer/FIG placeholder data and replace it
with a small, fully-populated, realistic Kamrup Metropolitan demo dataset (3 FIGs x 5 farmers)
for a stakeholder demo. Every farmer/FIG field is filled in, and every dashboard section
(Production, Stock, Input consumption, Monthly submission, Yield records, GPS Verification,
Asset Management, Training Management, Scheme Management/Allocations/Beneficiaries) gets data.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/seed_kamrup_demo.py --confirm
"""
import math
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.core.aadhaar import aadhaar_fields
from app.services.geo import polygon_area_sqm, points_to_wkt
from app.seed import _fcode, _gcode
from app.models import (
    FigActivity,
    District, SericultureCircle, SubdivisionCdc, SilkType, Activity, Product, SilkTypeActivityProduct,
    Caste, Religion, EducationLevel, AssetType, InputSourceType, LossReason,
    User, Farmer, Fig, FigMember, Land, AssetInstance,
    Meeting, Attendance, Yield_, ByproductEntry, YieldInputEntry, Stock,
    Scheme, Allocation, Beneficiary, Training, _now,
)

random.seed(2026)
TODAY = date(2026, 7, 26)

MALE_FIRST = [
    "Bhaskar", "Anil", "Diganta", "Pranjal", "Nabin", "Ranjit", "Hemanta", "Bipul", "Dilip", "Jitu",
    "Pradip", "Manoj", "Ratul", "Kamal", "Rupam", "Ashok", "Bhupen", "Nayan", "Tarun", "Dipankar",
]
FEMALE_FIRST = [
    "Junali", "Malati", "Kabita", "Rekha", "Bina", "Nandita", "Juri", "Anima", "Priyanka", "Rina",
    "Mamoni", "Rupali", "Nirmali", "Deepika", "Sabita", "Runumi", "Jyotsna", "Momi", "Kongkon", "Bornali",
]
SURNAMES = [
    "Saikia", "Neog", "Bora", "Phukan", "Sonowal", "Gogoi", "Chetia", "Hazarika", "Dutta", "Baruah",
    "Das", "Kalita", "Deka", "Bhuyan", "Talukdar", "Barman", "Konwar", "Mahanta", "Choudhury", "Nath",
]
BANKS = [
    ("State Bank of India", "Chandrapur Branch", "SBIN0001234"),
    ("Assam Gramin Vikash Bank", "Dispur Branch", "ARGB0001234"),
    ("Punjab National Bank", "Sonapur Branch", "PUNB0001234"),
    ("State Bank of India", "Guwahati Main Branch", "SBIN0000567"),
    ("Assam Gramin Vikash Bank", "Sonapur Branch", "ARGB0002345"),
]
TRAINING_TOPICS = [
    "Improved Rearing Techniques for Higher Cocoon Yield",
    "Disease Management in Silkworm Rearing",
    "Reeling and Post-Cocoon Processing",
]
ASSET_BY_SILK = {
    "Eri": ["Mountage — Chandraki", "Mountage — Bamboo", "Rearing Trays/Stands"],
    "Muga": ["Reeling Device — Bhir (traditional)", "Mountage — Box-type (Jali)", "Rearing Trays/Stands"],
}

FIG_PLANS = [
    {
        "circle_name": "Chandrapur", "village": "South Chandrapur",
        "panchayat": "Chandrapur Gaon Panchayat", "post_office": "Chandrapur S.O",
        "pin_code": "781021",
        "silk_type": "Eri", "activity": "Eri Rearing", "product": "Eri Cocoon",
        "fig_name": "South Chandrapur Eri Producers FIG", "lat": 26.13, "lng": 91.82,
    },
    {
        "circle_name": "Dispur", "village": "Hatigaon",
        "panchayat": "Hatigaon Gaon Panchayat", "post_office": "Hatigaon S.O",
        "pin_code": "781006",
        "silk_type": "Muga", "activity": "Muga Rearing", "product": "Muga Cocoon",
        "fig_name": "Hatigaon Muga Rearers FIG", "lat": 26.13, "lng": 91.79,
    },
    {
        "circle_name": "Sonapur", "village": "Khetri",
        "panchayat": "Sonapur Gaon Panchayat", "post_office": "Sonapur S.O",
        "pin_code": "782402",
        "silk_type": "Muga", "activity": "Muga Reeling", "product": "Muga Raw Silk",
        "fig_name": "Khetri Muga Reelers FIG", "lat": 26.05, "lng": 92.02,
    },
]


class _SeqCounter:
    def __init__(self, start: int):
        self.n = start

    def next(self) -> int:
        self.n += 1
        while self.n % 10 == 0:
            self.n += 1
        return self.n


def _full_name(gender: str) -> tuple[str, str]:
    first = random.choice(MALE_FIRST if gender == "Male" else FEMALE_FIRST)
    return first, random.choice(SURNAMES)


def _aadhaar() -> dict:
    """Aadhaar is never stored raw — return the three derived columns directly."""
    return aadhaar_fields("".join(str(random.randint(0, 9)) for _ in range(12)))


def _pan() -> str:
    letters = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5))
    digits = "".join(str(random.randint(0, 9)) for _ in range(4))
    return f"{letters}{digits}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"


def _dob() -> date:
    return TODAY - timedelta(days=random.randint(25 * 365, 55 * 365))


def _small_polygon(lat0: float, lng0: float) -> list[dict]:
    radius = random.uniform(0.0004, 0.0008)
    points = []
    for i in range(5):
        angle = (2 * math.pi * i / 5) + random.uniform(-0.15, 0.15)
        r = radius * random.uniform(0.85, 1.15)
        points.append({"latitude": lat0 + r * math.sin(angle), "longitude": lng0 + r * math.cos(angle)})
    return points


def _rate_range(product_name: str) -> tuple[float, float]:
    n = product_name.lower()
    if "raw silk" in n:
        return (2800, 5500)
    if "cocoon" in n:
        return (280, 550)
    return (50, 200)


def _planned_range(product_name: str) -> tuple[float, float]:
    n = product_name.lower()
    if "raw silk" in n:
        return (2, 8)
    if "cocoon" in n:
        return (20, 75)
    return (5, 25)


def delete_test_data(db) -> None:
    test_farmers = db.query(Farmer).filter(Farmer.first_name == "Test").all()
    test_ids = [f.id for f in test_farmers]
    if not test_ids:
        print("No Test farmers found — nothing to delete.")
        return
    fig_ids = {fm.fig_id for fm in db.query(FigMember).filter(FigMember.farmer_id.in_(test_ids)).all()}
    n_users = db.query(User).filter(User.farmer_id.in_(test_ids)).delete(synchronize_session=False)
    db.query(FigMember).filter(FigMember.farmer_id.in_(test_ids)).delete(synchronize_session=False)
    if fig_ids:
        db.query(Fig).filter(Fig.id.in_(fig_ids)).delete(synchronize_session=False)
    db.query(Farmer).filter(Farmer.id.in_(test_ids)).delete(synchronize_session=False)
    db.commit()
    print(f"Deleted {len(test_ids)} Test farmer(s), {len(fig_ids)} Test FIG(s), {n_users} login(s).")


def resolve_kamrup_context(db):
    district = db.query(District).filter(District.district_name == "Kamrup Metropolitan").first()
    circles = {c.circle_name: c for c in db.query(SericultureCircle).filter(SericultureCircle.district_id == district.id).all()}
    cdcs = {c.office_name: c for c in db.query(SubdivisionCdc).filter(SubdivisionCdc.district_id == district.id).all()}
    for circle_name, cdc_name in [("Dispur", "Dispur CDC"), ("Sonapur", "Sonapur SDO")]:
        circle = circles[circle_name]
        if not circle.subdivision_cdc_id and cdc_name in cdcs:
            circle.subdivision_cdc_id = cdcs[cdc_name].id
            db.add(circle)
    db.commit()
    print("SDO/CDC backfilled for Dispur and Sonapur circles (Chandrapur already had one).")
    return district, circles


def resolve_stap(db, silk_type_name: str, activity_name: str, product_name: str) -> dict:
    row = (
        db.query(SilkTypeActivityProduct, SilkType, Activity, Product)
        .join(SilkType, SilkType.id == SilkTypeActivityProduct.silk_type_id)
        .join(Activity, Activity.id == SilkTypeActivityProduct.activity_id)
        .join(Product, Product.id == SilkTypeActivityProduct.product_id)
        .filter(
            SilkType.silk_type_name == silk_type_name,
            Activity.activity_name == activity_name,
            Product.product_name == product_name,
            SilkTypeActivityProduct.role == "OUTPUT",
        )
        .first()
    )
    if not row:
        raise RuntimeError(f"STAP not found for {silk_type_name}/{activity_name}/{product_name}")
    stap, st, act, prod = row
    return {
        "id": stap.id, "activity_id": act.id, "product_id": prod.id, "product_name": prod.product_name,
        "uom": prod.unit_of_measure, "silk_type": st.silk_type_name, "silk_type_id": st.id,
    }


def build_stap_indexes(db):
    rows = (
        db.query(SilkTypeActivityProduct, SilkType, Activity, Product)
        .join(SilkType, SilkType.id == SilkTypeActivityProduct.silk_type_id)
        .join(Activity, Activity.id == SilkTypeActivityProduct.activity_id)
        .join(Product, Product.id == SilkTypeActivityProduct.product_id)
        .all()
    )
    byproduct_by = defaultdict(list)
    input_by = defaultdict(list)
    for stap, st, act, prod in rows:
        row = {"product_id": prod.id, "product_name": prod.product_name, "uom": prod.unit_of_measure}
        key = (st.silk_type_name, act.id)
        if stap.role == "OUTPUT" and prod.is_byproduct:
            byproduct_by[key].append(row)
        elif stap.role == "INPUT":
            input_by[key].append(row)
    return byproduct_by, input_by


def create_figs_and_farmers(db, district, circles) -> list[dict]:
    farmer_seq = _SeqCounter(100000)
    fig_seq = _SeqCounter(10000)
    mobile = [9854100000]
    castes = db.query(Caste).all()
    religions = db.query(Religion).all()
    edu_levels = db.query(EducationLevel).all()

    fig_records = []
    for plan in FIG_PLANS:
        circle = circles[plan["circle_name"]]
        stap = resolve_stap(db, plan["silk_type"], plan["activity"], plan["product"])
        formation_date = TODAY - timedelta(days=random.randint(365, 730))
        fig = Fig(
            fig_code=_gcode(fig_seq.next()), fig_name=plan["fig_name"], silk_type_id=stap["silk_type_id"],
            district_id=district.id, seri_circle_id=circle.id, formation_date=formation_date,
            village_name=plan["village"], panchayat_name=plan["panchayat"], post_office=plan["post_office"],
            pin_code=plan["pin_code"],
            address=f"Ward Committee Office, {plan['village']}",
            meeting_venue=f"Community Hall, {plan['village']}",
        )
        db.add(fig)
        db.flush()
        # A FIG's activities live in their own table now, not on a single stap_id.
        db.add(FigActivity(fig_id=fig.id, activity_id=stap["activity_id"]))

        fig_farmers = []
        for _ in range(5):
            gender = "Female" if random.random() < 0.5 else "Male"
            first, last = _full_name(gender)
            mobile[0] += 1
            bank_name, branch_name, ifsc = random.choice(BANKS)
            farmer = Farmer(
                farmer_code=_fcode(farmer_seq.next()), first_name=first, last_name=last, gender=gender,
                date_of_birth=_dob(), mobile_no=str(mobile[0]), **_aadhaar(), pan_no=_pan(),
                education_level_id=random.choice(edu_levels).id,
                farmer_type=random.choice(["Small", "Marginal", "Medium"]),
                experience_years=random.randint(3, 20),
                caste_id=random.choice(castes).id, religion_id=random.choice(religions).id,
                family_member_male=random.randint(1, 3), family_member_female=random.randint(1, 3),
                district_id=district.id, seri_circle_id=circle.id, village_name=plan["village"],
                gaon_panchayat=plan["panchayat"], development_block=f"{plan['circle_name']} Development Block",
                post_office=plan["post_office"], pin_code=plan["pin_code"],
                stap_ids=[stap["id"]], experience_activity_ids=[stap["activity_id"]],
                account_number="".join(str(random.randint(0, 9)) for _ in range(11)),
                bank_name=bank_name, branch_name=branch_name, ifsc_code=ifsc,
            )
            db.add(farmer)
            fig_farmers.append(farmer)
        db.flush()

        for idx, farmer in enumerate(fig_farmers):
            role = "President" if idx == 0 else "Member"
            db.add(FigMember(
                fig_id=fig.id, farmer_id=farmer.id, role=role,
                joining_date=datetime.combine(formation_date, datetime.min.time(), tzinfo=timezone.utc),
            ))

        president = fig_farmers[0]
        mobile[0] += 1
        fp_mobile = str(mobile[0])
        db.add(User(
            mobile_no=fp_mobile, name=f"{president.first_name} {president.last_name}",
            password_hash=hash_password("Fig@123"), role="FIG_PRESIDENT",
            fig_id=fig.id, farmer_id=president.id, district_id=district.id,
        ))

        fig_records.append({"fig": fig, "farmers": fig_farmers, "stap": stap, "plan": plan, "fp_mobile": fp_mobile})

    db.commit()
    print(f"Created {len(fig_records)} FIGs, {sum(len(r['farmers']) for r in fig_records)} farmers, "
          f"{len(fig_records)} FIG President logins.")
    return fig_records


def create_lands_and_assets(db, fig_records: list[dict]) -> None:
    asset_types = {a.name: a for a in db.query(AssetType).all()}
    n_lands = n_assets = 0
    for rec in fig_records:
        lat0, lng0 = rec["plan"]["lat"], rec["plan"]["lng"]
        pool = ASSET_BY_SILK[rec["plan"]["silk_type"]]
        for i, farmer in enumerate(rec["farmers"]):
            status = "Pending" if i == 4 else "Verified"
            land = Land(
                farmer_id=farmer.id, dag_no=f"D-{random.randint(100, 999)}",
                patta_no=f"P-{random.randint(1000, 9999)}", land_type="Owned", gps_verified=status,
            )
            pts = _small_polygon(lat0 + random.uniform(-0.01, 0.01), lng0 + random.uniform(-0.01, 0.01))
            area = polygon_area_sqm(pts)
            land.gps_points = pts
            land.boundary = points_to_wkt(pts)
            land.land_area_sqm = area
            land.land_area_bigha = area / 2400.0
            land.land_area_hectare = area / 10000.0
            if status == "Verified":
                land.verified_at = _now()
            db.add(land)
            n_lands += 1

            at_name = random.choice(pool)
            at = asset_types.get(at_name)
            if at:
                db.add(AssetInstance(
                    asset_type_id=at.id, owner_type="FARMER", owner_id=farmer.id, quantity=1,
                    acquisition_date=TODAY - timedelta(days=random.randint(60, 500)),
                    acquisition_mode="SELF_DECLARED_AT_REGISTRATION", status="FUNCTIONAL",
                    verification_status=random.choice(["UNVERIFIED", "CIRCLE_VERIFIED"]),
                    confidence="FARMER_SELF_DECLARED",
                ))
                n_assets += 1
    db.commit()
    print(f"Created {n_lands} GPS-verified lands and {n_assets} asset instances.")


def create_meetings_and_yields(db, fig_records: list[dict]) -> None:
    months = []
    y, m = TODAY.year, TODAY.month
    for _ in range(5):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months = list(reversed(months))

    byproduct_by, input_by = build_stap_indexes(db)
    source_type_ids = {s.source_name: s.id for s in db.query(InputSourceType).all()}
    loss_reason_ids = [lr.id for lr in db.query(LossReason).all()]

    n_meetings = n_yields = n_bp = n_inputs = 0
    for rec in fig_records:
        fig, stap = rec["fig"], rec["stap"]
        lo, hi = _planned_range(stap["product_name"])
        rlo, rhi = _rate_range(stap["product_name"])
        for mo in months:
            meeting_date = date(int(mo[:4]), int(mo[5:7]), random.randint(10, 20))
            submitted_at = datetime.combine(meeting_date, datetime.min.time(), tzinfo=timezone.utc)
            meeting = Meeting(
                fig_id=fig.id, meeting_title=f"Monthly Meeting - {mo}", meeting_date=meeting_date,
                meeting_venue=fig.meeting_venue, meeting_month=mo, submitted_at=submitted_at,
            )
            db.add(meeting)
            db.flush()
            n_meetings += 1

            for farmer in rec["farmers"]:
                present = random.random() < 0.9
                db.add(Attendance(meeting_id=meeting.id, fig_id=fig.id, farmer_id=farmer.id, is_present=present))
                if not present:
                    continue
                planned = round(random.uniform(lo, hi), 1)
                loss_reason_id = None
                if random.random() < 0.08 and loss_reason_ids:
                    actual = round(planned * random.uniform(0.2, 0.45), 1)
                    loss_reason_id = random.choice(loss_reason_ids)
                else:
                    actual = round(planned * random.uniform(0.8, 1.15), 1)
                sold_qty = round(actual * random.uniform(0.6, 0.9), 1)
                sold_rate = round(random.uniform(rlo, rhi), 2)
                yld = Yield_(
                    fig_id=fig.id, farmer_id=farmer.id, stap_id=stap["id"], activity_id=stap["activity_id"],
                    product_id=stap["product_id"], meeting_id=meeting.id, yield_month=mo, is_primary_stage=True,
                    planned_yield=planned, actual_yield=actual, sold_quantity=sold_qty, sold_rate=sold_rate,
                    earning=round(sold_qty * sold_rate, 2), loss_reason_id=loss_reason_id, submitted_at=submitted_at,
                )
                db.add(yld)
                db.flush()
                n_yields += 1

                bp_options = byproduct_by.get((stap["silk_type"], stap["activity_id"]))
                if bp_options and random.random() < 0.4:
                    bp = random.choice(bp_options)
                    bp_qty = round(actual * random.uniform(0.05, 0.15), 1)
                    db.add(ByproductEntry(
                        parent_yield_id=yld.id, farmer_id=farmer.id, fig_id=fig.id, product_id=bp["product_id"],
                        yield_month=mo, unit_of_measure=bp["uom"], quantity=bp_qty, planned_quantity=bp_qty,
                        sold_quantity=round(bp_qty * 0.6, 1), sold_rate=round(random.uniform(50, 150), 2),
                        submitted_at=submitted_at,
                    ))
                    n_bp += 1

                in_options = input_by.get((stap["silk_type"], stap["activity_id"]))
                if in_options and random.random() < 0.6:
                    inp = random.choice(in_options)
                    src_id = source_type_ids.get(random.choice(["Own Source", "Market Source"]))
                    db.add(YieldInputEntry(
                        parent_yield_id=yld.id, farmer_id=farmer.id, fig_id=fig.id, product_id=inp["product_id"],
                        yield_month=mo, unit_of_measure=inp["uom"], quantity=round(random.uniform(5, 40), 1),
                        source_type_id=src_id, submitted_at=submitted_at,
                    ))
                    n_inputs += 1
        db.commit()
    print(f"Created {n_meetings} meetings, {n_yields} yields, {n_bp} byproduct entries, {n_inputs} input entries.")


def build_stock_snapshot(db) -> None:
    rows = db.execute(text("""
        WITH combined AS (
            SELECT farmer_id, fig_id, product_id, actual_yield AS produced, sold_quantity AS sold,
                   yield_month, submitted_at
            FROM yields WHERE product_id IS NOT NULL
            UNION ALL
            SELECT farmer_id, fig_id, product_id, quantity AS produced, sold_quantity AS sold,
                   yield_month, submitted_at
            FROM byproduct_entries
        )
        SELECT c.farmer_id, c.fig_id, c.product_id,
               COALESCE(SUM(c.produced), 0) - COALESCE(SUM(c.sold), 0) AS closing,
               COALESCE(bool_or(p.is_perishable), false) AS is_perishable,
               MAX(c.yield_month) AS last_month, MAX(c.submitted_at) AS last_at
        FROM combined c JOIN products p ON p.id = c.product_id
        GROUP BY c.farmer_id, c.product_id, c.fig_id
    """)).fetchall()
    existing = {(s.farmer_id, s.product_id) for s in db.query(Stock).all()}
    n = 0
    for r in rows:
        key = (r.farmer_id, r.product_id)
        if key in existing:
            continue
        existing.add(key)
        db.add(Stock(
            farmer_id=r.farmer_id, fig_id=r.fig_id, product_id=r.product_id,
            opening_balance=0, closing_balance=r.closing, is_perishable=r.is_perishable,
            last_produced_month=r.last_month, last_entry_at=r.last_at or _now(),
        ))
        n += 1
    db.commit()
    print(f"Stock snapshot: {n} new rows.")


def loosen_scheme_and_seed_beneficiaries(db, district, fig_records: list[dict]) -> None:
    scheme = db.query(Scheme).filter(Scheme.scheme_name == "Silk Rearing Training Program").first()
    if not scheme:
        print("No existing scheme found — skipping Allocation/Beneficiary seeding.")
        return
    scheme.target_caste_ids = []
    scheme.target_religion_ids = []
    scheme.target_pwd_only = False
    db.add(scheme)

    existing_alloc = db.query(Allocation).filter(
        Allocation.scheme_id == scheme.id, Allocation.district_id == district.id
    ).first()
    if not existing_alloc:
        db.add(Allocation(
            scheme_id=scheme.id, district_id=district.id,
            allocated_amount_rs=50000, utilised=15000, remaining=35000,
        ))

    all_farmers = [f for rec in fig_records for f in rec["farmers"]]
    for farmer in random.sample(all_farmers, min(3, len(all_farmers))):
        db.add(Beneficiary(
            scheme_id=scheme.id, farmer_id=farmer.id, beneficiary_type="FARMER", district_id=district.id,
            benefit_amount=5000, disbursement_date=TODAY - timedelta(days=random.randint(10, 120)),
        ))
    db.commit()
    print("Scheme targeting loosened; Allocation + 3 Beneficiaries seeded for Kamrup Metropolitan.")


def rename_da_and_seed_trainings(db, district) -> str:
    da = db.query(User).filter(User.mobile_no == "8123456780").first()
    if da:
        da.name = "Bhaskar Saikia"
        db.add(da)
        db.commit()
    statuses = ["Approved", "Completed", "Pending"]
    for i, status in enumerate(statuses):
        topic = TRAINING_TOPICS[i]
        from_d = TODAY + timedelta(days=random.randint(-90, 30))
        to_d = from_d + timedelta(days=2)
        t = Training(
            topic=topic, description=f"District-level training on {topic.lower()}.",
            proposed_from_date=from_d, proposed_to_date=to_d,
            proposed_venue="Kamrup Metropolitan Training Centre, Guwahati",
            estimated_participants=25, requesting_da_id=da.id, district_id=district.id, status=status,
        )
        if status in ("Approved", "Completed"):
            t.approval_remarks = "Approved as per district quota"
            t.approval_from_date = from_d
            t.approval_to_date = to_d
            t.approved_venue = t.proposed_venue
            t.approved_at = _now()
        if status == "Completed":
            t.actual_from_date = from_d
            t.actual_to_date = to_d
            t.actual_venue = t.proposed_venue
            t.actual_participants = 22
            t.completion_report = "Training completed successfully with good farmer participation."
            t.completed_at = _now()
        db.add(t)
    db.commit()
    print("District Admin renamed; 3 trainings seeded.")
    return da.name if da else "(DA not found)"


def print_summary(fig_records: list[dict], da_name: str) -> None:
    print("\n=== Demo logins ===")
    print("  State Admin:      1111111111 / sa@123")
    print(f"  District Admin:   8123456780 / District@123  ({da_name}, Kamrup Metropolitan)")
    for rec in fig_records:
        print(f"  FIG President:    {rec['fp_mobile']} / Fig@123  ({rec['fig'].fig_name})")


if __name__ == "__main__":
    if "--confirm" not in sys.argv:
        print("This deletes the 5 'Test' farmers + their FIG/login, and adds 3 realistic")
        print("Kamrup Metropolitan FIGs (5 farmers each) with full data across every module.")
        print("Re-run with --confirm to proceed: python scripts/seed_kamrup_demo.py --confirm")
        sys.exit(1)

    db = SessionLocal()
    try:
        delete_test_data(db)
        district, circles = resolve_kamrup_context(db)
        fig_records = create_figs_and_farmers(db, district, circles)
        create_lands_and_assets(db, fig_records)
        create_meetings_and_yields(db, fig_records)
        build_stock_snapshot(db)
        loosen_scheme_and_seed_beneficiaries(db, district, fig_records)
        da_name = rename_da_and_seed_trainings(db, district)
        print_summary(fig_records, da_name)
        print("\nDone.")
    finally:
        db.close()
