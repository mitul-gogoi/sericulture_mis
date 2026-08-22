"""One-time script: create the correct Activity/Product/Silk-Type-Activity-Product (STAP)
dataset for Eri, Muga, and Mulberry, replacing the previous ad-hoc data. Tasar is left
untouched (already inactive, has no activities/products of its own).

Run this AFTER wiping the old master data with reset_transactional_data.py --confirm,
since that script hard-deletes all existing Activities/Products/STAP rows first — this
script assumes a clean slate for those three tables and will fail on unique-constraint
conflicts if run against data that already has Eri/Muga/Mulberry activities or products.

Run from backend/, with the venv activated:
    .venv/Scripts/python scripts/seed_production_master_data.py --confirm
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models import SilkType, Activity, Product, SilkTypeActivityProduct, InputSourceCategory

# Each silk type's process, in step order. "leaves" is tracked as an output-only metric
# (the silk type's Food Plant Plantation yield), not wired as an input to Rearing,
# matching the source data.
SILK_TYPE_SPECS = {
    "Eri": {
        "activities": [
            "Eri Food Plant Plantation", "Eri Egg Production (Eri Grainage)", "Eri Rearing",
            "Eri Spinning", "Eri Weaving",
        ],
        "products": {
            "Seedlings for Eri": ("Number", "Land Related", False, False),
            "Quality Leaves for Eri Silkworm Rearing": ("kg", None, False, False),
            "Eri Seed Cocoon": ("Number", "Produce Related", False, False),
            "Eri Egg (DFL)": ("Number", "Produce Related", False, False),
            "Eri Cocoon": ("kg", "Produce Related", False, False),
            "Eri Pupa": ("kg", None, True, False),
            "Eri Raw Silk": ("kg", "Produce Related", False, False),
            "Eri Fabric": ("Meter", None, False, False),
        },
        # (activity_name, role, product_name, input_group)
        "stap": [
            ("Eri Food Plant Plantation", "INPUT", "Seedlings for Eri", None),
            ("Eri Food Plant Plantation", "OUTPUT", "Quality Leaves for Eri Silkworm Rearing", None),
            ("Eri Egg Production (Eri Grainage)", "INPUT", "Eri Seed Cocoon", None),
            ("Eri Egg Production (Eri Grainage)", "OUTPUT", "Eri Egg (DFL)", None),
            ("Eri Rearing", "INPUT", "Eri Egg (DFL)", None),
            ("Eri Rearing", "OUTPUT", "Eri Cocoon", None),
            ("Eri Rearing", "OUTPUT", "Eri Pupa", None),
            ("Eri Spinning", "INPUT", "Eri Cocoon", None),
            ("Eri Spinning", "OUTPUT", "Eri Raw Silk", None),
            ("Eri Weaving", "INPUT", "Eri Raw Silk", None),
            ("Eri Weaving", "OUTPUT", "Eri Fabric", None),
        ],
    },
    "Muga": {
        "activities": [
            "Muga Food Plant Plantation", "Muga Grainage", "Muga Rearing", "Muga Reeling", "Muga Weaving",
        ],
        "products": {
            "Seedlings for Muga": ("Number", "Land Related", False, False),
            "Quality Leaves for Muga Silkworm Rearing": ("kg", None, False, False),
            "Muga Seed Cocoon": ("Number", "Produce Related", False, False),
            "Muga Egg (DFL)": ("Number", "Produce Related", False, False),
            # Grainage's own byproduct — distinct from the "Muga Cocoon" primary output, and
            # measured in kg (vs Cocoon's Number), matching the source table's own unit choice.
            "Muga Cut Cocoon": ("kg", "Produce Related", True, False),
            "Muga Cocoon": ("Number", "Produce Related", False, False),
            "Muga Raw Silk": ("kg", "Produce Related", False, False),
            "Muga Silk Waste": ("kg", None, True, False),
            "Muga Fabric": ("Meter", None, False, False),
        },
        "stap": [
            ("Muga Food Plant Plantation", "INPUT", "Seedlings for Muga", None),
            ("Muga Food Plant Plantation", "OUTPUT", "Quality Leaves for Muga Silkworm Rearing", None),
            ("Muga Grainage", "INPUT", "Muga Seed Cocoon", None),
            ("Muga Grainage", "OUTPUT", "Muga Egg (DFL)", None),
            ("Muga Grainage", "OUTPUT", "Muga Cut Cocoon", None),
            ("Muga Rearing", "INPUT", "Muga Egg (DFL)", None),
            ("Muga Rearing", "OUTPUT", "Muga Cocoon", None),
            ("Muga Reeling", "INPUT", "Muga Cocoon", None),
            ("Muga Reeling", "OUTPUT", "Muga Raw Silk", None),
            ("Muga Reeling", "OUTPUT", "Muga Silk Waste", None),
            ("Muga Weaving", "INPUT", "Muga Raw Silk", None),
            ("Muga Weaving", "OUTPUT", "Muga Fabric", None),
        ],
    },
    "Mulberry": {
        "activities": [
            "Mulberry Food Plant Plantation", "Mulberry Grainage", "Mulberry Rearing", "Mulberry Reeling", "Mulberry Weaving",
        ],
        "products": {
            "Seedlings for Mulberry": ("Number", "Land Related", False, False),
            "Quality Leaves for Mulberry Silkworm Rearing": ("kg", None, False, False),
            "Mulberry Seed Cocoon": ("Number", "Produce Related", False, False),
            "Mulberry Egg (DFL)": ("Number", "Produce Related", False, False),
            "Mulberry Cut Cocoon": ("kg", "Produce Related", True, False),
            "Mulberry Cocoon": ("kg", "Produce Related", False, False),
            "Mulberry Raw Silk": ("kg", "Produce Related", False, False),
            "Mulberry Silk Waste": ("kg", None, True, False),
            "Mulberry Fabric": ("Meter", None, False, False),
        },
        "stap": [
            ("Mulberry Food Plant Plantation", "INPUT", "Seedlings for Mulberry", None),
            ("Mulberry Food Plant Plantation", "OUTPUT", "Quality Leaves for Mulberry Silkworm Rearing", None),
            ("Mulberry Grainage", "INPUT", "Mulberry Seed Cocoon", None),
            ("Mulberry Grainage", "OUTPUT", "Mulberry Egg (DFL)", None),
            ("Mulberry Grainage", "OUTPUT", "Mulberry Cut Cocoon", None),
            ("Mulberry Rearing", "INPUT", "Mulberry Egg (DFL)", None),
            ("Mulberry Rearing", "OUTPUT", "Mulberry Cocoon", None),
            ("Mulberry Reeling", "INPUT", "Mulberry Cocoon", None),
            ("Mulberry Reeling", "OUTPUT", "Mulberry Raw Silk", None),
            ("Mulberry Reeling", "OUTPUT", "Mulberry Silk Waste", None),
            ("Mulberry Weaving", "INPUT", "Mulberry Raw Silk", None),
            ("Mulberry Weaving", "OUTPUT", "Mulberry Fabric", None),
        ],
    },
}


def main() -> None:
    if "--confirm" not in sys.argv:
        print("Creates the correct Eri/Muga/Mulberry Activity/Product/STAP dataset.")
        print("Run reset_transactional_data.py --confirm FIRST if old master data still exists.")
        print("Re-run with --confirm to proceed.")
        sys.exit(1)

    db = SessionLocal()
    try:
        silk_types = {s.silk_type_name: s for s in db.query(SilkType).all()}
        categories = {c.category_name: c.id for c in db.query(InputSourceCategory).all()}

        n_activities = n_products = n_stap = 0
        for silk_type_name, spec in SILK_TYPE_SPECS.items():
            st = silk_types[silk_type_name]

            activities = {}
            for step_no, name in enumerate(spec["activities"], start=1):
                a = Activity(activity_name=name, silk_type_id=st.id, step_no=step_no)
                db.add(a)
                activities[name] = a
                n_activities += 1
            db.flush()

            products = {}
            for name, (uom, category_name, is_byproduct, is_perishable) in spec["products"].items():
                p = Product(
                    product_name=name, unit_of_measure=uom, silk_type_id=st.id,
                    default_source_category_id=categories.get(category_name) if category_name else None,
                    is_byproduct=is_byproduct, is_perishable=is_perishable,
                )
                db.add(p)
                products[name] = p
                n_products += 1
            db.flush()

            for activity_name, role, product_name, input_group in spec["stap"]:
                db.add(SilkTypeActivityProduct(
                    silk_type_id=st.id, activity_id=activities[activity_name].id,
                    product_id=products[product_name].id, role=role, input_group=input_group,
                ))
                n_stap += 1

        db.commit()
        print(f"Created {n_activities} activities, {n_products} products, {n_stap} STAP mappings "
              f"across Eri, Muga, and Mulberry.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
