"""Master data + demo accounts seeding."""
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    District, SericultureCircle, DirectorateOffice, FigSettings, Caste, Religion, EducationLevel, LossReason,
    Scheme, User, SilkType, Stock, AssetType, _now,
)

DISTRICTS = [
    "Bajali", "Baksa", "Barpeta", "Biswanath", "Bongaigaon", "Cachar",
    "Charaideo", "Chirang", "Darrang", "Dhemaji", "Dhubri", "Dibrugarh",
    "Dima Hasao", "Goalpara", "Golaghat", "Hailakandi", "Hojai", "Jorhat",
    "Kamrup", "Kamrup Metropolitan", "Karbi Anglong", "Kokrajhar", "Lakhimpur",
    "Majuli", "Morigaon", "Nagaon", "Nalbari", "Sivasagar", "Sonitpur",
    "South Salmara-Mankachar", "Sribhumi", "Tamulpur", "Tinsukia",
    "Udalguri", "West Karbi Anglong",
]

CIRCLES = [
    ("Kamrup Metropolitan", "Dispur"),
    ("Kamrup Metropolitan", "Sonapur"),
    ("Kamrup Metropolitan", "Chandrapur"),
    ("Kamrup", "Rangia"),
    ("Kamrup", "Hajo"),
    ("Kamrup", "Boko"),
    ("Nalbari", "Barkhetri"),
    ("Nalbari", "Tihu"),
    ("Nalbari", "Nalbari Sadar"),
    ("Barpeta", "Sarukhetri"),
    ("Barpeta", "Barpeta Sadar"),
    ("Barpeta", "Chenga"),
    ("Goalpara", "Balijana"),
    ("Goalpara", "Goalpara Sadar"),
    ("Goalpara", "Lakhipur"),
    ("Dhubri", "Gauripur"),
    ("Dhubri", "Bilasipara"),
    ("Dhubri", "Golakganj"),
    ("Bongaigaon", "Boitamari"),
    ("Bongaigaon", "Bongaigaon Sadar"),
    ("Sonitpur", "Tezpur"),
    ("Sonitpur", "Dhekiajuli"),
    ("Sonitpur", "Rangapara"),
    ("Lakhimpur", "Bihpuria"),
    ("Lakhimpur", "Lakhimpur Sadar"),
    ("Lakhimpur", "Narayanpur"),
    ("Dibrugarh", "Tengakhat"),
    ("Dibrugarh", "Barbaruah"),
    ("Dibrugarh", "Chabua"),
    ("Sivasagar", "Demow"),
    ("Sivasagar", "Nazira"),
    ("Sivasagar", "Sivasagar Sadar"),
    ("Jorhat", "Titabor"),
    ("Jorhat", "Jorhat Sadar"),
    ("Jorhat", "Teok"),
    ("Golaghat", "Sarupathar"),
    ("Golaghat", "Golaghat Sadar"),
    ("Golaghat", "Dergaon"),
    ("Nagaon", "Kaliabor"),
    ("Nagaon", "Nagaon Sadar"),
    ("Nagaon", "Raha"),
    ("Karbi Anglong", "Diphu"),
    ("Karbi Anglong", "Bokajan"),
    ("Karbi Anglong", "Howraghat"),
    ("Cachar", "Sonai"),
    ("Cachar", "Silchar Sadar"),
    ("Cachar", "Lakhipur"),
    ("Sribhumi", "Patharkandi"),
    ("Sribhumi", "Sribhumi Sadar"),
    ("Sribhumi", "Ratabari"),
    ("Bajali", "Bajali Sadar"),
    ("Bajali", "Pathsala"),
    ("Baksa", "Baksa Sadar"),
    ("Baksa", "Barama"),
    ("Biswanath", "Biswanath Chariali"),
    ("Biswanath", "Gohpur"),
    ("Charaideo", "Sonari"),
    ("Charaideo", "Charaideo Sadar"),
    ("Chirang", "Kajalgaon"),
    ("Chirang", "Chirang Sadar"),
    ("Darrang", "Mangaldai"),
    ("Darrang", "Sipajhar"),
    ("Dhemaji", "Dhemaji Sadar"),
    ("Dhemaji", "Sissiborgaon"),
    ("Dima Hasao", "Haflong"),
    ("Dima Hasao", "Maibang"),
    ("Hailakandi", "Hailakandi Sadar"),
    ("Hailakandi", "Lala"),
    ("Hojai", "Hojai Sadar"),
    ("Hojai", "Lanka"),
    ("Kokrajhar", "Kokrajhar Sadar"),
    ("Kokrajhar", "Gossaigaon"),
    ("Majuli", "Majuli Sadar"),
    ("Majuli", "Kamalabari"),
    ("Morigaon", "Morigaon Sadar"),
    ("Morigaon", "Mayong"),
    ("South Salmara-Mankachar", "Salmara"),
    ("South Salmara-Mankachar", "Mankachar"),
    ("Tamulpur", "Tamulpur Sadar"),
    ("Tamulpur", "Baganpara"),
    ("Tinsukia", "Tinsukia Sadar"),
    ("Tinsukia", "Doomdooma"),
    ("Tinsukia", "Margherita"),
    ("Udalguri", "Udalguri Sadar"),
    ("Udalguri", "Kalaigaon"),
    ("West Karbi Anglong", "Hamren"),
    ("West Karbi Anglong", "Amri"),
]

CASTES = ["General", "OBC", "SC", "ST", "MOBC"]
RELIGIONS = ["Hindu", "Muslim", "Christian", "Sikh", "Buddhist", "Jain", "Other"]
# EDUCATION_LEVELS = [
#     "Illiterate", "Below Primary", "Primary", "Middle", "Secondary",
#     "Higher Secondary", "Graduate", "Post Graduate", "Diploma", "Professional",
# ]

LOSS_REASONS = [
    "Disease outbreak (flacherie) in silkworms (ৰেচম পলুৰ ৰোগৰ প্ৰাদুৰ্ভাৱ (ফ্লেচেৰী))",
    "Water scarcity affected host-plant growth (পানীৰ নাটনিৰ বাবে পোষক উদ্ভিদৰ বৃদ্ধিত প্ৰভাৱ পৰিছে)",
    "Unseasonal cold wave caused high larval mortality (অকাল শীতল লহৰে পলুৰ উচ্চ মৃত্যুৰ হাৰৰ কাৰণ হৈ পৰিছে)",
    "Heavy rainfall damaged rearing house (প্ৰৱল বৰষুণে পলু পোহা ঘৰটো ক্ষতিগ্ৰস্ত কৰিলে)",
    "Pest infestation reduced cocoon quality (কীট-পতংগৰ আক্ৰমণে লেটাৰ গুণগত মান হ্ৰাস কৰিলে)",
    "Power outage disrupted grainage operations (বিদ্যুৎ কৰ্তনে গ্ৰেইনেজ কাৰ্যকলাপ ব্যাহত কৰিলে)"
]

SILK_TYPES = ["Eri", "Muga", "Mulberry", "Tasar"]

# (name, category, silk_types, ownership_level, useful_life_years, typically_scheme_funded)
# Durable, cooldown-relevant assets only — host-plant plantations are land (Land & GIS) and
# low-value consumables are disbursement line items, so neither belongs here.
ASSET_TYPES = [
    ("Rearing House", "STRUCTURE", ["Eri", "Mulberry"], "INDIVIDUAL", 6, True),
    ("Chawki Rearing Centre (CRC)", "SHARED_INFRASTRUCTURE", ["Mulberry"], "FIG", 8, True),
    ("Common Facility Centre (CFC) — Reeling/Degumming", "SHARED_INFRASTRUCTURE",
     ["Eri", "Muga", "Mulberry"], "FIG", 8, True),
    ("Mountage — Chandraki", "EQUIPMENT", ["Eri"], "INDIVIDUAL", 3, True),
    ("Mountage — Bamboo", "EQUIPMENT", ["Eri", "Muga"], "INDIVIDUAL", 3, True),
    ("Mountage — Plastic", "EQUIPMENT", ["Eri"], "INDIVIDUAL", 5, True),
    ("Mountage — Rotary", "EQUIPMENT", ["Mulberry"], "INDIVIDUAL", 5, True),
    ("Mountage — Box-type (Jali)", "EQUIPMENT", ["Muga"], "INDIVIDUAL", 4, True),
    ("Reeling Device — Bhir (traditional)", "EQUIPMENT", ["Muga"], "INDIVIDUAL", 6, True),
    ("Reeling Machine — Motorised/Cottage Basin/Filature", "EQUIPMENT",
     ["Muga", "Mulberry"], "EITHER", 8, True),
    ("Degumming Unit (eco-friendly)", "EQUIPMENT", ["Eri"], "EITHER", 6, True),
    ("Spinning Machine (motorised)", "EQUIPMENT", ["Eri"], "INDIVIDUAL", 5, True),
    ("Loom — Throw-shuttle", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 8, True),
    ("Loom — Fly-shuttle", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 8, True),
    ("Disinfectant Sprayer", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 4, True),
    ("Rearing Trays/Stands", "EQUIPMENT", ["Eri", "Muga", "Mulberry"], "INDIVIDUAL", 4, True),
]


# (scheme_name, description, silk_type_name, eligible_farmer_type, budget, disbursement_type,
#  support_type, [(silk_type_name, activity_name), ...])
SCHEMES = [
    ("Muga Silk Promotion 2025", "Subsidy for Muga rearing households", "Muga", "All", 5000000, "DBT", "Cash", [
        ("Muga", "Muga: Host Plant Cultivation (Som)"),
        ("Muga", "Muga: Host Plant Cultivation (Soalu)"),
        ("Muga", "Muga: Mounting and Cocoon Spinning"),
    ]),
    ("Mulberry Plantation Support", "Plant saplings and DFLs distribution", "Mulberry", "Small / Marginal", 3000000, "Material", "Kind", [
        ("Mulberry", "Mulberry: Mulberry Garden Cultivation"),
        ("Mulberry", "Mulberry: Rearing House Disinfection and DFL Procurement"),
    ]),
    ("Eri Spinning Equipment Grant", "Spindle and ratchet wheel distribution", "Eri", "All", 2000000, "Both", "Kind", [
        ("Eri", "Eri: Hand Spinning of Yarn (Takli)"),
        ("Eri", "Eri: Hand Spinning of Yarn (Charkha)"),
    ]),
    ("Tasar Sericulture Development Programme", "Support for Tasar host-plantation and rearing infrastructure", "Tasar", "All", 4000000, "Both", "Kind", [
        ("Tasar", "Tasar: Host Plant Cultivation (Arjun)"),
        ("Tasar", "Tasar: Host Plant Cultivation (Asan)"),
        ("Tasar", "Tasar: Host Plant Cultivation (Sal)"),
        ("Tasar", "Tasar: Outdoor Rearing on Trees - Late Instars"),
    ]),
    ("Women SHG Sericulture Livelihood Grant", "Livelihood grant for women-led sericulture SHGs", "Eri", "Small / Marginal", 2500000, "DBT", "Cash", [
        ("Eri", "Eri: Hand Spinning of Yarn (Takli)"),
        ("Eri", "Eri: Hand Spinning of Yarn (Charkha)"),
        ("Eri", "Eri: Warping and Sizing"),
    ]),
]


def _fcode(seq: int) -> str:
    return f"SERI-FRM-{seq:06d}"


def _gcode(seq: int) -> str:
    return f"SERI-FIG-{seq:05d}"


def _seed_districts(db: Session) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in DISTRICTS:
        row = db.query(District).filter(District.district_name == d).first()
        if not row:
            row = District(district_name=d)
            db.add(row)
            db.flush()
        out[d] = row.id
    return out


def _seed_circles(db: Session, district_map: dict[str, str]) -> None:
    for dn, cn in CIRCLES:
        exists = db.query(SericultureCircle).filter(
            SericultureCircle.district_id == district_map[dn], SericultureCircle.circle_name == cn,
        ).first()
        if not exists:
            db.add(SericultureCircle(circle_name=cn, district_id=district_map[dn]))


def _seed_directorate_office(db: Session) -> None:
    if not db.query(DirectorateOffice).first():
        db.add(DirectorateOffice())


def _seed_fig_settings(db: Session) -> None:
    if not db.query(FigSettings).first():
        db.add(FigSettings())


def _seed_lookups(db: Session) -> None:
    for c in CASTES:
        if not db.query(Caste).filter(Caste.caste_name == c).first():
            db.add(Caste(caste_name=c))
    for r in RELIGIONS:
        if not db.query(Religion).filter(Religion.religion_name == r).first():
            db.add(Religion(religion_name=r))
    for lr in LOSS_REASONS:
        if not db.query(LossReason).filter(LossReason.reason_name == lr).first():
            db.add(LossReason(reason_name=lr))


def _seed_education_levels(db: Session) -> None:
    for name in EDUCATION_LEVELS:
        if not db.query(EducationLevel).filter(EducationLevel.education_level_name == name).first():
            db.add(EducationLevel(education_level_name=name))


def _seed_asset_types(db: Session) -> None:
    for name, category, silk_types, ownership, life, funded in ASSET_TYPES:
        if not db.query(AssetType).filter(AssetType.name == name).first():
            db.add(AssetType(name=name, category=category, silk_types=silk_types,
                             ownership_level=ownership, useful_life_years=life,
                             typically_scheme_funded=funded))


def _seed_schemes(db: Session, silk_type_map: dict[str, str], activity_map: dict[tuple[str, str], str]) -> None:
    for name, desc, st_name, eft, budget, disb, support, act_refs in SCHEMES:
        if not db.query(Scheme).filter(Scheme.scheme_name == name).first():
            act_ids = [activity_map[ref] for ref in act_refs if ref in activity_map]
            db.add(Scheme(scheme_name=name, description=desc,
                          silk_type_id=silk_type_map.get(st_name),
                          activity_ids=act_ids,
                          eligible_farmer_type=eft,
                          total_budget_rs=budget, disbursement_type=disb,
                          support_type=support))
    db.flush()


def _seed_silk_types(db: Session) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in SILK_TYPES:
        row = db.query(SilkType).filter(SilkType.silk_type_name == name).first()
        if not row:
            row = SilkType(silk_type_name=name)
            db.add(row)
            db.flush()
        out[name] = row.id
    return out


def _backfill_stock_snapshot(db: Session) -> None:
    if db.query(Stock).first():
        return  # already backfilled once; real-time upserts take over from here on
    rows = db.execute(text("""
        SELECT y.farmer_id, y.fig_id, y.product_id,
               COALESCE(SUM(y.actual_yield), 0) - COALESCE(SUM(y.sold_quantity), 0) AS closing,
               COALESCE(bool_or(p.is_perishable), false) AS is_perishable,
               MAX(y.yield_month) AS last_month,
               MAX(y.submitted_at) AS last_at
        FROM yields y JOIN products p ON p.id = y.product_id
        WHERE y.product_id IS NOT NULL
        GROUP BY y.farmer_id, y.product_id, y.fig_id
    """)).fetchall()
    seen: set[tuple[str, str]] = set()
    for r in rows:
        key = (r.farmer_id, r.product_id)
        if key in seen:
            continue
        seen.add(key)
        db.add(Stock(
            farmer_id=r.farmer_id, fig_id=r.fig_id, product_id=r.product_id,
            opening_balance=0, closing_balance=r.closing,
            is_perishable=r.is_perishable,
            last_produced_month=r.last_month, last_entry_at=r.last_at or _now(),
        ))
    db.flush()


def _seed_state_admin(db: Session) -> None:
    if not db.query(User).filter(User.mobile_no == settings.STATE_ADMIN_MOBILE).first():
        db.add(User(mobile_no=settings.STATE_ADMIN_MOBILE, name="State Admin",
                    password_hash=hash_password(settings.STATE_ADMIN_PASSWORD),
                    role="STATE_ADMIN"))


def _seed_district_admin(db: Session) -> "District | None":
    kamrup_metro = db.query(District).filter(District.district_name == "Kamrup Metropolitan").first()
    if kamrup_metro and not db.query(User).filter(User.mobile_no == settings.DISTRICT_ADMIN_MOBILE).first():
        db.add(User(mobile_no=settings.DISTRICT_ADMIN_MOBILE, name="Kamrup Metro DA",
                    password_hash=hash_password(settings.DISTRICT_ADMIN_PASSWORD),
                    role="DISTRICT_ADMIN", district_id=kamrup_metro.id))
    return kamrup_metro




def seed_all(db: Session) -> None:
    district_map = _seed_districts(db)
    _seed_circles(db, district_map)
    _seed_directorate_office(db)
    _seed_fig_settings(db)
    _seed_lookups(db)
    _seed_asset_types(db)

    _seed_silk_types(db)
    # Activities/Products/STAP/Schemes are no longer auto-seeded — State Admin builds
    # these up from scratch via Master Data. Demo State/District Admin logins are no
    # longer auto-seeded either — the one real State Admin login is created once via
    # scripts/reset_all_except_masters.py and must not be silently recreated on every
    # backend restart (that undid an explicit "remove all users but one" data wipe).
    # Education levels are likewise no longer auto-seeded here — EDUCATION_LEVELS above
    # is a stale/incomplete list from before the full Education Level master data set was
    # built up directly via Master Data; calling _seed_education_levels() would either
    # NameError (constant is commented out) or reintroduce a shorter, inconsistent list.
    _ensure_protected_admin(db)
    _backfill_stock_snapshot(db)

    db.commit()


def _ensure_protected_admin(db: Session) -> None:
    """Keep the permanent super-admin correctly named and always active.

    Deliberately never touches password_hash. The password lives only in the database,
    so it is not in this public repository, and this function does not need to know it.
    Creates nothing: if the account does not exist, it is not invented here -- it is
    created once by scripts/reset_all_except_masters.py.
    """
    u = db.query(User).filter(User.mobile_no == settings.PROTECTED_ADMIN_MOBILE).first()
    if not u:
        return
    changed = False
    if u.name != settings.PROTECTED_ADMIN_NAME:
        u.name = settings.PROTECTED_ADMIN_NAME
        changed = True
    if not u.is_active:
        u.is_active = True
        changed = True
    if u.role != "STATE_ADMIN":
        u.role = "STATE_ADMIN"
        changed = True
    if changed:
        print(f"[seed] super admin {settings.PROTECTED_ADMIN_MOBILE} restored to active STATE_ADMIN")
