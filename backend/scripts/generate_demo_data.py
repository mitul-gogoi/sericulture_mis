"""One-time script: wipe the dev DB and generate rich, realistic demo data
across all 35 Assam districts for a stakeholder demo.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/generate_demo_data.py --confirm
"""
import math
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import SQLModel
from sqlalchemy import text
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.services.geo import polygon_area_sqm, points_to_wkt
from app.seed import seed_all, _fcode, _gcode
from app.models import (
    FigActivity,
    District, SericultureCircle, SilkType, Activity, Product, SilkTypeActivityProduct,
    User, Farmer, Fig, FigMember, Meeting, Attendance, Yield_, ByproductEntry, YieldInputEntry, Stock,
    Land, Scheme, Allocation, Beneficiary, Training, Notification, NotificationRecipient, LossReason, InputSourceType,
    _now,
)

random.seed(42)  # reproducible demo data

TODAY = date(2026, 7, 10)

# ---------------------------------------------------------------------------
# Name pools (hand-rolled — no Faker dependency, and generic Faker wouldn't
# produce authentic Assamese names anyway)
# ---------------------------------------------------------------------------
MALE_FIRST = [
    "Bhaskar", "Anil", "Diganta", "Pranjal", "Nabin", "Ranjit", "Hemanta", "Bipul", "Dilip", "Jitu",
    "Pradip", "Manoj", "Ratul", "Kamal", "Rupam", "Ashok", "Bhupen", "Nayan", "Tarun", "Dipankar",
    "Prasanta", "Bikash", "Rupjyoti", "Sailen", "Sanjay", "Amar", "Girin", "Utpal", "Debojit", "Mukut",
    "Bidyut", "Pallab", "Rituraj", "Munin", "Padma", "Robin", "Suren", "Nipen", "Lakhi", "Bhaben",
]
FEMALE_FIRST = [
    "Junali", "Malati", "Kabita", "Rekha", "Bina", "Nandita", "Juri", "Anima", "Priyanka", "Rina",
    "Mamoni", "Rupali", "Nirmali", "Deepika", "Sabita", "Runumi", "Jyotsna", "Momi", "Kongkon", "Bornali",
    "Purnima", "Anjali", "Minoti", "Rupashree", "Dipika", "Pratima", "Konika", "Sangeeta",
    "Rimpi", "Barnali", "Ranjita", "Ratna", "Sarala", "Bhanita", "Sushmita", "Jonali", "Parul", "Mridula",
]
SURNAMES = [
    "Saikia", "Neog", "Bora", "Phukan", "Sonowal", "Gogoi", "Chetia", "Hazarika", "Dutta", "Baruah",
    "Das", "Kalita", "Deka", "Bhuyan", "Talukdar", "Barman", "Konwar", "Mahanta", "Choudhury", "Nath",
    "Deori", "Rajkhowa", "Bhagawati", "Doley", "Pegu", "Mili", "Kachari", "Rabha",
    "Handique", "Buragohain", "Duwarah", "Payeng", "Sarma", "Roy",
]
VILLAGE_ROOTS = [
    "Kalakhowa", "Sonapur", "Dhekiajuli", "Balijana", "Bihpuria", "Tengakhat", "Demow", "Titabor",
    "Sarupathar", "Kaliabor", "Sonai", "Patharkandi", "Rangapara", "Barkhetri", "Sarukhetri", "Gauripur",
    "Boitamari", "Mangaldai", "Sipajhar", "Hojai", "Lanka", "Haflong", "Maibang", "Kokrajhar", "Gossaigaon",
    "Kamalabari", "Mayong", "Salmara", "Chirang", "Sissiborgaon", "Bajali", "Barama", "Gohpur", "Sonari",
    "Doomdooma", "Kalaigaon", "Hamren", "Diphu", "Bokajan", "Nazira",
]
VILLAGE_SUFFIX = ["Gaon", "Chuburi", "Pathar", "Chariali", "Basti"]

TRAINING_TOPICS = [
    "Improved Rearing Techniques for Higher Cocoon Yield", "Disease Management in Silkworm Rearing",
    "DFL Production and Grainage Best Practices", "Reeling and Post-Cocoon Processing",
    "Byproduct Utilization for Additional Income", "Modern Host-Plant Plantation Management",
    "FIG Governance and Record-Keeping", "Market Linkages for Sericulture Produce",
]
NOTIFICATION_TITLES = [
    "Monthly submission deadline reminder", "New scheme announcement: apply now",
    "Training calendar for next quarter released", "GPS verification drive — action needed",
    "Cocoon price advisory update", "System maintenance notice",
]
BENEFIT_MATERIALS = [
    "Rearing house upgrade kit", "Ratchet wheel + spindle set",
    "Host-plant saplings (500 nos)", "DFL supply voucher",
]

# Approximate per-district lat/lng anchors — plausible, not surveyed
DISTRICT_CENTROIDS = {
    "Kamrup Metropolitan": (26.15, 91.75), "Kamrup": (26.20, 91.55), "Nalbari": (26.45, 91.45),
    "Barpeta": (26.48, 91.00), "Goalpara": (26.15, 90.62), "Dhubri": (26.02, 89.98),
    "Bongaigaon": (26.48, 90.55), "Sonitpur": (26.65, 92.80), "Lakhimpur": (27.23, 94.10),
    "Dibrugarh": (27.48, 94.90), "Dima Hasao": (25.05, 93.00), "Sivasagar": (26.98, 94.63),
    "Jorhat": (26.75, 94.22), "Golaghat": (26.52, 93.97), "Nagaon": (26.35, 92.68),
    "Karbi Anglong": (26.05, 93.42), "Cachar": (24.82, 92.78), "Sribhumi": (24.83, 92.35),
    "Bajali": (26.55, 91.15), "Baksa": (26.72, 91.28), "Biswanath": (26.73, 93.15),
    "Charaideo": (27.05, 95.05), "Chirang": (26.55, 90.60), "Darrang": (26.45, 92.03),
    "Dhemaji": (27.48, 94.58), "Hailakandi": (24.68, 92.57), "Hojai": (26.00, 92.85),
    "Kokrajhar": (26.40, 90.27), "Majuli": (26.95, 94.20), "Morigaon": (26.25, 92.35),
    "South Salmara-Mankachar": (25.92, 89.85), "Tamulpur": (26.65, 91.30), "Tinsukia": (27.49, 95.36),
    "Udalguri": (26.75, 92.10), "West Karbi Anglong": (25.85, 92.95),
}

# Districts that additionally get a demo-able FIG President login (Kamrup Metropolitan's
# Bhaskar Saikia already comes from seed_all() — these add geographic/silk-type variety)
CURATED_FP_DISTRICTS = ["Dibrugarh", "Sivasagar", "Sribhumi", "Jorhat", "Kokrajhar", "Golaghat"]

LAND_TYPE_POOL = ["Owned"] * 6 + ["Leased"] * 2 + ["Community"] * 1 + ["Government"] * 1 + ["Forest"] * 1
GPS_STATUS_POOL = ["Verified"] * 10 + ["Pending"] * 5 + ["Not Submitted"] * 3 + ["Failed"] * 2


class _SeqCounter:
    """Mirrors the routers' farmer/fig code numbering: increment, skip multiples of 10."""
    def __init__(self, start: int):
        self.n = start

    def next(self) -> int:
        self.n += 1
        while self.n % 10 == 0:
            self.n += 1
        return self.n


def _village_name() -> str:
    return f"{random.choice(VILLAGE_ROOTS)} {random.choice(VILLAGE_SUFFIX)}"


def _full_name(gender: str) -> tuple[str, str]:
    first = random.choice(MALE_FIRST if gender == "Male" else FEMALE_FIRST)
    return first, random.choice(SURNAMES)


def _rate_range(product_name: str) -> tuple[float, float]:
    n = product_name.lower()
    if "dfl" in n:
        return (3, 6)
    if "raw silk" in n:
        return (2800, 5500)
    if "cut cocoon" in n:
        return (180, 350)
    if "cocoon" in n:
        return (280, 550)
    if "fabric" in n:
        return (150, 320)
    if "pupae" in n:
        return (40, 90)
    if "reel waste" in n or "noil" in n:
        return (70, 140)
    if "gicha" in n or "ghicha" in n:
        return (380, 650)
    return (50, 200)


def _planned_range(product_name: str) -> tuple[float, float]:
    n = product_name.lower()
    if "dfl" in n:
        return (150, 700)
    if "raw silk" in n:
        return (2, 8)
    if "cut cocoon" in n:
        return (8, 35)
    if "cocoon" in n:
        return (20, 75)
    if "fabric" in n:
        return (15, 55)
    return (5, 25)


def _input_qty_range(product_name: str) -> tuple[float, float]:
    n = product_name.lower()
    if "dfl" in n:
        return (100, 500)
    if "leaf" in n or "foliage" in n:
        return (30, 200)
    if "larvae" in n:
        return (200, 4000)
    if "saplings" in n or "seeds" in n:
        return (20, 300)
    if "manure" in n or "compost" in n:
        return (10, 60)
    if "cocoon" in n:
        return (5, 40)
    if "silk" in n or "yarn" in n:
        return (2, 15)
    return (1, 20)


def _month_range(n: int, end_year: int, end_month: int) -> list[str]:
    months = []
    y, m = end_year, end_month
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(months))


def _random_formation_date() -> date:
    if random.random() < 0.3:
        days_back = random.randint(30, 180)
    else:
        days_back = random.randint(180, 3 * 365)
    return TODAY - timedelta(days=days_back)


def _weighted_created_at(months: list[str]) -> datetime:
    weights = list(range(1, len(months) + 1))
    mo = random.choices(months, weights=weights)[0]
    y, m = map(int, mo.split("-"))
    day = random.randint(1, 28)
    return datetime(y, m, day, random.randint(8, 18), random.randint(0, 59), tzinfo=timezone.utc)


def _mid_month_date(mo: str) -> date:
    y, m = map(int, mo.split("-"))
    day = min(28, max(1, 15 + random.randint(-5, 5)))
    return date(y, m, day)


def _small_polygon(lat0: float, lng0: float) -> list[dict]:
    """5 roughly-evenly-spaced points around (lat0, lng0) — matches the ≥5-point GPS submission rule."""
    radius = random.uniform(0.0003, 0.0007)
    points = []
    for i in range(5):
        angle = (2 * math.pi * i / 5) + random.uniform(-0.15, 0.15)
        r = radius * random.uniform(0.85, 1.15)
        points.append({"latitude": lat0 + r * math.sin(angle), "longitude": lng0 + r * math.cos(angle)})
    return points


def wipe_all(db) -> None:
    names = [t.name for t in SQLModel.metadata.sorted_tables]
    db.execute(text("TRUNCATE TABLE " + ", ".join(f'"{n}"' for n in names) + " CASCADE"))
    db.commit()
    print(f"Wiped {len(names)} tables.")


def _create_land(db, farmer: Farmer, district_name: str, block_land_ids: list[str]) -> None:
    land_type = random.choice(LAND_TYPE_POOL)
    status = random.choice(GPS_STATUS_POOL)
    land = Land(
        farmer_id=farmer.id, dag_no=f"D-{random.randint(100, 999)}",
        patta_no=f"P-{random.randint(1000, 9999)}", land_type=land_type,
        gps_verified=status,
    )
    if status != "Not Submitted":
        lat0, lng0 = DISTRICT_CENTROIDS[district_name]
        lat0 += random.uniform(-0.05, 0.05)
        lng0 += random.uniform(-0.05, 0.05)
        pts = _small_polygon(lat0, lng0)
        area = polygon_area_sqm(pts)
        land.gps_points = pts
        land.boundary = points_to_wkt(pts)
        land.land_area_sqm = area
        land.land_area_bigha = area / 2400.0
        land.land_area_hectare = area / 10000.0
        if status in ("Verified", "Failed"):
            land.verified_at = _now()
        if status == "Failed":
            land.failure_reason = "GPS boundary does not match land revenue records"
        if status in ("Verified", "Pending") and block_land_ids and random.random() < 0.04:
            land.overlap_detected = True
            land.overlapping_parcel_ids = [random.choice(block_land_ids)]
    db.add(land)
    block_land_ids.append(land.id)


def _random_input_source(source_type_ids: dict[str, str], active_scheme_ids: list[str]) -> tuple[str, str | None]:
    roll = random.random()
    if roll < 0.50:
        return source_type_ids["Own Source"], None
    if roll < 0.80:
        return source_type_ids["Market Source"], None
    if roll < 0.95 and active_scheme_ids:
        return source_type_ids["Government Source"], random.choice(active_scheme_ids)
    return source_type_ids["Government Land"], None


def generate_demo_data(db) -> dict:
    print("Loading master data...")
    # Explicit ordering keeps district/FIG -> sequential-mobile-number assignment deterministic
    # across re-runs (Postgres row order is otherwise unspecified without ORDER BY), so the
    # curated demo accounts hardcoded on the login page keep pointing at the same districts/FIGs.
    districts = {d.district_name: d for d in db.query(District).order_by(District.district_name).all()}
    did_to_name = {d.id: name for name, d in districts.items()}
    active_scheme_ids = [s.id for s in db.query(Scheme).filter(Scheme.is_active).all()]
    source_type_ids = {s.source_name: s.id for s in db.query(InputSourceType).all()}
    loss_reason_ids = [lr.id for lr in db.query(LossReason).all()]
    circles_by_district = defaultdict(list)
    for c in db.query(SericultureCircle).order_by(SericultureCircle.district_id, SericultureCircle.circle_name).all():
        circles_by_district[did_to_name[c.district_id]].append(c)

    stap_join = db.query(SilkTypeActivityProduct, SilkType, Activity, Product).join(
        SilkType, SilkType.id == SilkTypeActivityProduct.silk_type_id
    ).join(
        Activity, Activity.id == SilkTypeActivityProduct.activity_id
    ).join(
        Product, Product.id == SilkTypeActivityProduct.product_id
    ).all()

    output_staps = []
    input_staps = []
    byproduct_by_silktype_activity = defaultdict(list)
    input_by_silktype_activity = defaultdict(list)
    for stap, st, act, prod in stap_join:
        row = {
            "id": stap.id, "silk_type": st.silk_type_name, "activity": act.activity_name,
            "activity_id": stap.activity_id, "silk_type_id": stap.silk_type_id,
            "product_id": prod.id, "product_name": prod.product_name,
            "uom": prod.unit_of_measure, "is_byproduct_product": prod.is_byproduct,
        }
        if stap.role == "OUTPUT":
            output_staps.append(row)
            if prod.is_byproduct:
                byproduct_by_silktype_activity[(st.silk_type_name, stap.activity_id)].append(row)
        else:
            input_staps.append(row)
            input_by_silktype_activity[(st.silk_type_name, stap.activity_id)].append(row)

    # A FIG/Farmer's primary production stage must be a genuine primary output, not a byproduct.
    fig_assignable = [r for r in output_staps if not r["is_byproduct_product"]]

    existing_da_district_ids = {u.district_id for u in db.query(User).filter(User.role == "DISTRICT_ADMIN").all()}
    curated_fp_used: set[str] = set()

    months = _month_range(14, TODAY.year, TODAY.month)  # 2025-06 .. 2026-07

    farmer_seq = _SeqCounter(100001)
    fig_seq = _SeqCounter(10001)
    farmer_mobile = [7000000000]
    da_mobile = [8100000000]
    fp_mobile = [7700000000]

    all_farmers_for_schemes: list[tuple[str, str, str]] = []  # (farmer_id, district_name, silk_type)
    district_da_id_map: dict[str, str] = {}
    demo_summary = {"district_admins": [], "fig_presidents": []}

    for dist_idx, district_name in enumerate(districts.keys()):
        district = districts[district_name]
        dist_circles = circles_by_district[district_name]

        if district.id not in existing_da_district_ids:
            da_mobile[0] += 1
            mobile = str(da_mobile[0])
            da_user = User(mobile_no=mobile, name=f"{district_name} DA",
                            password_hash=hash_password("District@123"),
                            role="DISTRICT_ADMIN", district_id=district.id)
            db.add(da_user)
            requesting_da_id = da_user.id
            demo_summary["district_admins"].append((district_name, mobile))
        else:
            requesting_da_id = db.query(User).filter(
                User.district_id == district.id, User.role == "DISTRICT_ADMIN").first().id
            demo_summary["district_admins"].append((district_name, "(canonical) 8888888888"))
        district_da_id_map[district_name] = requesting_da_id

        block_land_ids: list[str] = []

        for circle in dist_circles:
            n_figs = random.choice([1, 1, 2])
            for _ in range(n_figs):
                stap = random.choice(fig_assignable)
                village = _village_name()
                fig = Fig(
                    fig_code=_gcode(fig_seq.next()), fig_name=f"{village} {stap['silk_type']} Producers FIG",
                    silk_type_id=stap["silk_type_id"], district_id=district.id, seri_circle_id=circle.id,
                    formation_date=_random_formation_date(), meeting_venue=f"Community Hall, {village}",
                )
                db.add(fig)
                db.flush()  # models have no ORM relationship() declarations, so flush ordering
                            # across tables isn't automatic — make dependent rows' FK targets real
                # A FIG's activities live in their own table now, not on a single stap_id.
                db.add(FigActivity(fig_id=fig.id, activity_id=stap["activity_id"]))

                fig_farmers: list[tuple[Farmer, dict | None]] = []
                for _ in range(random.randint(13, 16)):
                    gender = "Female" if random.random() < 0.55 else "Male"
                    first, last = _full_name(gender)
                    farmer_mobile[0] += 1
                    secondary = None
                    stap_ids = [stap["id"]]
                    if random.random() < 0.25:
                        cand = random.choice(fig_assignable)
                        if cand["id"] != stap["id"]:
                            secondary = cand
                            stap_ids.append(cand["id"])
                    created_at = _weighted_created_at(months)
                    farmer = Farmer(
                        farmer_code=_fcode(farmer_seq.next()), first_name=first, last_name=last, gender=gender,
                        mobile_no=str(farmer_mobile[0]), district_id=district.id, seri_circle_id=circle.id,
                        village_name=_village_name(), stap_ids=stap_ids,
                        farmer_type=random.choice(["Small", "Small", "Marginal", "Marginal", "Medium"]),
                        created_at=created_at, updated_at=created_at,
                    )
                    db.add(farmer)
                    fig_farmers.append((farmer, secondary))
                    all_farmers_for_schemes.append((farmer.id, district_name, stap["silk_type"]))
                db.flush()

                for idx, (farmer, _) in enumerate(fig_farmers):
                    role = "President" if idx == 0 else "Member"
                    db.add(FigMember(
                        fig_id=fig.id, farmer_id=farmer.id, role=role,
                        joining_date=datetime.combine(fig.formation_date, datetime.min.time(), tzinfo=timezone.utc),
                    ))

                if district_name in CURATED_FP_DISTRICTS and district_name not in curated_fp_used:
                    curated_fp_used.add(district_name)
                    president = fig_farmers[0][0]
                    fp_mobile[0] += 1
                    mobile = str(fp_mobile[0])
                    db.add(User(
                        mobile_no=mobile, name=f"{president.first_name} {president.last_name} (FP)",
                        password_hash=hash_password("Fig@123"), role="FIG_PRESIDENT",
                        fig_id=fig.id, farmer_id=president.id, district_id=district.id,
                    ))
                    demo_summary["fig_presidents"].append((district_name, stap["silk_type"], mobile))

                relevant_months = [mo for mo in months if mo >= fig.formation_date.strftime("%Y-%m")]
                lo, hi = _planned_range(stap["product_name"])
                rlo, rhi = _rate_range(stap["product_name"])
                for mo in relevant_months:
                    if random.random() > 0.80:
                        continue
                    meeting_date = _mid_month_date(mo)
                    submitted_at = datetime.combine(meeting_date, datetime.min.time(), tzinfo=timezone.utc)
                    meeting = Meeting(
                        fig_id=fig.id, meeting_title=f"Monthly Meeting - {mo}", meeting_date=meeting_date,
                        meeting_venue=fig.meeting_venue, meeting_month=mo, submitted_at=submitted_at,
                    )
                    db.add(meeting)
                    db.flush()

                    present_map = {}
                    for farmer, _ in fig_farmers:
                        present = random.random() < 0.90
                        present_map[farmer.id] = present
                        db.add(Attendance(meeting_id=meeting.id, fig_id=fig.id, farmer_id=farmer.id, is_present=present))

                    for farmer, secondary in fig_farmers:
                        if not present_map[farmer.id]:
                            continue
                        planned = round(random.uniform(lo, hi), 1)
                        loss_reason_id = None
                        if random.random() < 0.05:
                            actual = round(planned * random.uniform(0.20, 0.45), 1)
                            loss_reason_id = random.choice(loss_reason_ids) if loss_reason_ids else None
                        else:
                            actual = round(planned * random.uniform(0.75, 1.15), 1)
                        sold_qty = round(actual * random.uniform(0.55, 0.9), 1)
                        sold_rate = round(random.uniform(rlo, rhi), 2)
                        yld = Yield_(
                            fig_id=fig.id, farmer_id=farmer.id, stap_id=stap["id"], activity_id=stap["activity_id"],
                            product_id=stap["product_id"], meeting_id=meeting.id, yield_month=mo,
                            is_primary_stage=True, planned_yield=planned, actual_yield=actual,
                            next_month_plan=round(planned * random.uniform(0.9, 1.2), 1),
                            sold_quantity=sold_qty, sold_rate=sold_rate, earning=round(sold_qty * sold_rate, 2),
                            loss_reason_id=loss_reason_id, submitted_at=submitted_at,
                        )
                        db.add(yld)
                        db.flush()

                        if not stap["is_byproduct_product"] and random.random() < 0.4:
                            bp_options = byproduct_by_silktype_activity.get((stap["silk_type"], stap["activity_id"]))
                            if bp_options:
                                bp = random.choice(bp_options)
                                bp_planned = round(actual * random.uniform(0.05, 0.15), 1)
                                bp_qty = round(bp_planned * random.uniform(0.85, 1.1), 1)
                                bp_sold = round(bp_qty * random.uniform(0.5, 0.9), 1)
                                brlo, brhi = _rate_range(bp["product_name"])
                                bp_rate = round(random.uniform(brlo, brhi), 2)
                                db.add(ByproductEntry(
                                    parent_yield_id=yld.id, farmer_id=farmer.id, fig_id=fig.id,
                                    product_id=bp["product_id"], yield_month=mo, unit_of_measure=bp["uom"],
                                    quantity=bp_qty, planned_quantity=bp_planned,
                                    next_month_plan=round(bp_planned * random.uniform(0.9, 1.2), 1),
                                    stock_balance=round(bp_qty * random.uniform(0.1, 0.4), 1),
                                    sold_quantity=bp_sold, sold_rate=bp_rate,
                                    earning=round(bp_sold * bp_rate, 2), submitted_at=submitted_at,
                                ))

                        in_options = input_by_silktype_activity.get((stap["silk_type"], stap["activity_id"]))
                        if in_options and random.random() < 0.6:
                            for inp in random.sample(in_options, min(len(in_options), random.randint(1, 2))):
                                ilo, ihi = _input_qty_range(inp["product_name"])
                                src_type_id, src_scheme_id = _random_input_source(source_type_ids, active_scheme_ids)
                                db.add(YieldInputEntry(
                                    parent_yield_id=yld.id, farmer_id=farmer.id, fig_id=fig.id,
                                    product_id=inp["product_id"], yield_month=mo, unit_of_measure=inp["uom"],
                                    quantity=round(random.uniform(ilo, ihi), 1),
                                    source_type_id=src_type_id, scheme_id=src_scheme_id, submitted_at=submitted_at,
                                ))

                        if secondary and random.random() < 0.3:
                            lo2, hi2 = _planned_range(secondary["product_name"])
                            planned2 = round(random.uniform(lo2, hi2), 1)
                            actual2 = round(planned2 * random.uniform(0.7, 1.1), 1)
                            sold2 = round(actual2 * random.uniform(0.5, 0.85), 1)
                            rlo2, rhi2 = _rate_range(secondary["product_name"])
                            rate2 = round(random.uniform(rlo2, rhi2), 2)
                            db.add(Yield_(
                                fig_id=fig.id, farmer_id=farmer.id, stap_id=secondary["id"],
                                activity_id=secondary["activity_id"], product_id=secondary["product_id"],
                                yield_month=mo, is_primary_stage=False, planned_yield=planned2, actual_yield=actual2,
                                sold_quantity=sold2, sold_rate=rate2, earning=round(sold2 * rate2, 2),
                                submitted_at=submitted_at,
                            ))

                for farmer, _ in fig_farmers:
                    if random.random() < 0.9:
                        _create_land(db, farmer, district_name, block_land_ids)

        db.commit()
        print(f"[{dist_idx + 1}/{len(districts)}] {district_name}: done")

    _generate_schemes_allocations_beneficiaries(db, districts, all_farmers_for_schemes)
    _generate_trainings(db, districts, district_da_id_map)
    _generate_notifications(db)
    _build_stock_snapshot(db)
    db.commit()
    return demo_summary


def _generate_schemes_allocations_beneficiaries(db, districts, all_farmers_for_schemes) -> None:
    schemes = db.query(Scheme).all()
    target = next((s for s in schemes if "Women SHG" in s.scheme_name), schemes[-1] if schemes else None)
    if target:
        target.is_active = False

    silk_types = {s.id: s.silk_type_name for s in db.query(SilkType).all()}
    silk_type_by_scheme = {s.id: silk_types.get(s.silk_type_id) for s in schemes}

    for scheme in schemes:
        for district in districts.values():
            allocated = round((scheme.total_budget_rs / 35) * random.uniform(0.6, 1.8), 2)
            frac = random.choice([0.0, 0.0, 0.3, 0.5, 0.65, 0.8, 0.95, 1.0])
            utilised = round(allocated * frac, 2)
            db.add(Allocation(
                scheme_id=scheme.id, district_id=district.id, allocated_amount_rs=allocated,
                utilised=utilised, remaining=round(allocated - utilised, 2),
            ))

    sample = random.sample(all_farmers_for_schemes, min(500, len(all_farmers_for_schemes)))
    for farmer_id, district_name, silk_type in sample:
        matching = [s for s in schemes if silk_type_by_scheme.get(s.id) in (None, silk_type)]
        if not matching:
            continue
        scheme = random.choice(matching)
        district = districts[district_name]
        kind = random.choice(["cash", "material", "both", "none"])
        db.add(Beneficiary(
            scheme_id=scheme.id, farmer_id=farmer_id, district_id=district.id,
            benefit_amount=round(random.uniform(2000, 15000), 2) if kind in ("cash", "both") else 0,
            benefit_material=random.choice(BENEFIT_MATERIALS) if kind in ("material", "both") else None,
            disbursement_date=(TODAY - timedelta(days=random.randint(10, 400))) if random.random() < 0.7 else None,
        ))
    db.commit()
    print("Schemes/Allocations/Beneficiaries done.")


def _generate_trainings(db, districts, district_da_id_map) -> None:
    statuses = ["Pending", "Approved", "Rejected", "Completed"]
    for district_name, district in districts.items():
        da_id = district_da_id_map[district_name]
        for _ in range(random.randint(2, 4)):
            status = random.choices(statuses, weights=[3, 3, 1, 4])[0]
            topic = random.choice(TRAINING_TOPICS)
            from_d = TODAY + timedelta(days=random.randint(-120, 60))
            to_d = from_d + timedelta(days=random.randint(1, 3))
            t = Training(
                topic=topic, description=f"District-level training on {topic.lower()}.",
                proposed_from_date=from_d, proposed_to_date=to_d,
                proposed_venue=f"{district_name} Training Centre",
                estimated_participants=random.randint(15, 40),
                requesting_da_id=da_id, district_id=district.id, status=status,
            )
            if status == "Rejected":
                t.rejection_reason = "Budget constraints for this quarter"
            elif status in ("Approved", "Completed"):
                t.approval_remarks = "Approved as per district quota"
                t.approval_from_date = from_d
                t.approval_to_date = to_d
                t.approved_venue = t.proposed_venue
                t.approved_at = _now()
            if status == "Completed":
                t.actual_from_date = from_d
                t.actual_to_date = to_d
                t.actual_venue = t.proposed_venue
                t.actual_participants = max(5, t.estimated_participants - random.randint(0, 5))
                t.completion_report = "Training completed successfully with good farmer participation."
                t.completed_at = _now()
            db.add(t)
    db.commit()
    print("Trainings done.")


def _generate_notifications(db) -> None:
    state_admin = db.query(User).filter(User.role == "STATE_ADMIN").first()
    da_users = db.query(User).filter(User.role == "DISTRICT_ADMIN").all()
    fp_users = db.query(User).filter(User.role == "FIG_PRESIDENT").all()
    recipient_types = ["ALL_DA", "ALL_FP", "ALL_DA_AND_FP", "SELECTED_DA", "SELECTED_FP"]

    for _ in range(18):
        rtype = random.choice(recipient_types)
        sender = state_admin if rtype.startswith("ALL") or random.random() < 0.6 or not da_users else random.choice(da_users)
        notif = Notification(
            title=random.choice(NOTIFICATION_TITLES),
            details="Please review the details and take necessary action at the earliest.",
            attachment_path="/uploads/demo/notice.pdf" if random.random() < 0.3 else None,
            sent_by_user_id=sender.id, sent_by_role=sender.role, recipient_type=rtype,
        )
        db.add(notif)
        if rtype == "ALL_DA":
            targets = da_users
        elif rtype == "ALL_FP":
            targets = fp_users
        elif rtype == "ALL_DA_AND_FP":
            targets = da_users + fp_users
        elif rtype == "SELECTED_DA":
            targets = random.sample(da_users, min(5, len(da_users)))
        else:
            targets = random.sample(fp_users, min(3, len(fp_users))) if fp_users else []
        for u in targets:
            is_read = random.random() < 0.6
            db.add(NotificationRecipient(
                notification_id=notif.id, recipient_user_id=u.id,
                is_read=is_read, read_at=_now() if is_read else None,
            ))
    db.commit()
    print("Notifications done.")


def _build_stock_snapshot(db) -> None:
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
    seen: set[tuple[str, str]] = set()
    for r in rows:
        key = (r.farmer_id, r.product_id)
        if key in seen:
            continue
        seen.add(key)
        db.add(Stock(
            farmer_id=r.farmer_id, fig_id=r.fig_id, product_id=r.product_id,
            opening_balance=0, closing_balance=r.closing, is_perishable=r.is_perishable,
            last_produced_month=r.last_month, last_entry_at=r.last_at or _now(),
        ))
    db.commit()
    print(f"Stock snapshot: {len(seen)} rows.")


def print_summary(db, demo_summary: dict) -> None:
    tables = [
        "districts", "sericulture_circles", "castes", "religions", "silk_types",
        "activities", "products", "input_source_types",
        "silk_type_activity_products", "schemes", "allocations", "beneficiaries", "users",
        "farmers", "figs", "fig_members", "meetings", "attendance", "yields", "byproduct_entries",
        "yield_input_entries", "stock", "lands", "trainings", "notifications", "notification_recipients",
    ]
    print("\n=== Row counts ===")
    for name in tables:
        count = db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
        print(f"  {name}: {count}")

    print("\n=== District Admin demo logins (password: District@123) ===")
    for d, m in demo_summary["district_admins"]:
        print(f"  {d}: {m}")

    print("\n=== FIG President demo logins (password: Fig@123) ===")
    print("  Kamrup Metropolitan (Muga): 7777777777  [canonical]")
    for d, st, m in demo_summary["fig_presidents"]:
        print(f"  {d} ({st}): {m}")


if __name__ == "__main__":
    if "--confirm" not in sys.argv:
        print("This will WIPE ALL DATA in the database and regenerate rich demo data.")
        print("Re-run with --confirm to proceed: python scripts/generate_demo_data.py --confirm")
        sys.exit(1)

    db = SessionLocal()
    try:
        wipe_all(db)
        seed_all(db)
        summary = generate_demo_data(db)
        print_summary(db, summary)
        print("\nDone.")
    finally:
        db.close()
