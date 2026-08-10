"""One-time script: seed a Conversion Standard for every real Input->Output pair that is
actually configured in "Map Activity to Product" (SilkTypeActivityProduct) for Eri, Muga,
and Mulberry (Tasar untouched, matching seed_production_master_data.py's own convention).

Design, per explicit user correction (this replaces an earlier version of this script that
generated a full N x N permutation of every product pair regardless of any real relationship
— the user flagged two problems with that: (1) it produced physically nonsensical/reversed
pairs, e.g. "Quality Leaves -> Seedlings" when the real STAP mapping is Seedlings -> Leaves,
and (2) because several unrelated standards ended up pointing at the same output product, the
Yield View rendered one "Expected (via X)" sub-column per matching standard — for a product
like Eri Cocoon that meant 6+ Expected columns instead of one):

For each Activity in a silk type's real production chain, take that Activity's own INPUT
product (every Activity in this app's data has exactly one) and pair it with each of that
Activity's own OUTPUT products (Rearing/Grainage/Reeling activities that produce two outputs
in parallel — e.g. Eri Rearing: Egg(DFL) -> {Cocoon, Pupa} — get one standard per output, same
input). This is intentionally NOT the same set of edges as the earlier full-permutation
version: no synthetic "skip ahead" or "reserve some cocoon as seed stock" edges are invented
here — only what Map Activity to Product itself actually encodes, so every output product
ends up with exactly one Conversion Standard, matching the app's own real single-step chain
and eliminating the "many Expected columns per output" problem at the data level rather than
needing a "pick the closest one" heuristic in the Yield View.

Percentage ranges are grounded in real sericulture reference data researched for this task
(Central Silk Board, Directorate of Sericulture Assam, published agricultural-extension
figures) — see the per-pair comments. A couple of pairs (host-plant leaf yield per seedling,
fabric meters per kg yarn) have no single authoritative published figure and are reasonable
order-of-magnitude estimates instead, flagged as such — not presented as verified.

Run from backend/, with the venv activated (run reset_conversion_standards.py --confirm
first if standards from an earlier run of this script already exist):
    .venv/Scripts/python scripts/seed_conversion_standards_full.py --confirm
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models import SilkType, Product, ConversionStandard

# (input_product_name, output_product_name) -> (output_min_qty, output_max_qty) per 100
# input units. Mirrors seed_production_master_data.py's SILK_TYPE_SPECS "stap" lists exactly
# — one entry per (Activity, its one INPUT product, one of its OUTPUT products).
PAIRS = {
    "Eri": {
        # Food Plant Plantation — leaf yield per seedling: no single authoritative published
        # figure found; reasonable order-of-magnitude estimate.
        ("Seedlings for Eri", "Quality Leaves for Eri Silkworm Rearing"): (400, 600),
        # Eri Egg Production (Grainage) — published grainage-performance study: cocoon:DFL
        # ratio ~4.46:1 -> ~20-25 DFL per 100 seed cocoons.
        ("Eri Seed Cocoon", "Eri Egg (DFL)"): (20, 25),
        # Eri Rearing, output 1/2 — kept identical to the value already configured via the
        # UI before this pass (not re-derived), since it's real admin-entered master data.
        ("Eri Egg (DFL)", "Eri Cocoon"): (20, 25),
        # Eri Rearing, output 2/2 — Rearing's real input is Egg(DFL), producing Cocoon and
        # Pupa in parallel (per Map Activity to Product), not Cocoon->Pupa as an extra step.
        # Derived from the Egg->Cocoon yield above scaled by the published Eri cocoon
        # composition (shell 8.93% / floss 5.79% / pupa 85.05% of cocoon weight).
        ("Eri Egg (DFL)", "Eri Pupa"): (17, 21),
        # Eri Spinning — Eri shell ratio 8.93-16.78% across published studies -> cocoon(kg)
        # -> raw silk(kg).
        ("Eri Cocoon", "Eri Raw Silk"): (12, 16),
        # Eri Weaving — fabric meters per kg raw silk yarn: no single published figure
        # (varies by fabric weight/weave); reasonable order-of-magnitude estimate.
        ("Eri Raw Silk", "Eri Fabric"): (600, 900),
    },
    "Muga": {
        ("Seedlings for Muga", "Quality Leaves for Muga Silkworm Rearing"): (400, 600),
        ("Muga Seed Cocoon", "Muga Egg (DFL)"): (20, 25),
        # Muga Grainage, output 2/2 — moth-emergence byproduct of the same seed cocoon input.
        ("Muga Seed Cocoon", "Muga Cut Cocoon"): (5, 10),
        # Muga Rearing — DFL:cocoon ratio ~1:45-1:52 (muga's characteristically high
        # outdoor-rearing mortality, per published rearing-practice figures).
        ("Muga Egg (DFL)", "Muga Cocoon"): (4200, 5200),
        # Muga Reeling, output 1/2 — published figure: ~4500-5500 cocoons per kg raw silk.
        ("Muga Cocoon", "Muga Raw Silk"): (15, 20),
        # Muga Reeling, output 2/2 — reeling byproduct (waste/floss silk), roughly
        # proportional to cocoon input; estimate.
        ("Muga Cocoon", "Muga Silk Waste"): (3, 5),
        ("Muga Raw Silk", "Muga Fabric"): (600, 900),
    },
    "Mulberry": {
        ("Seedlings for Mulberry", "Quality Leaves for Mulberry Silkworm Rearing"): (400, 600),
        ("Mulberry Seed Cocoon", "Mulberry Egg (DFL)"): (20, 25),
        ("Mulberry Seed Cocoon", "Mulberry Cut Cocoon"): (5, 10),
        # Mulberry Rearing — DFL:cocoon yield ~42-73 kg/100 DFL across published field
        # studies (crossbreed to high-performing bivoltine).
        ("Mulberry Egg (DFL)", "Mulberry Cocoon"): (45, 65),
        # Mulberry Reeling, output 1/2 — renditta 6-8 for good bivoltine (100/renditta).
        ("Mulberry Cocoon", "Mulberry Raw Silk"): (12, 16),
        ("Mulberry Cocoon", "Mulberry Silk Waste"): (3, 5),
        ("Mulberry Raw Silk", "Mulberry Fabric"): (600, 900),
    },
}


def main() -> None:
    if "--confirm" not in sys.argv:
        print("Seeds a Conversion Standard for every real Input->Output pair configured in")
        print("Map Activity to Product, for Eri, Muga, and Mulberry (Tasar untouched).")
        print("Re-run with --confirm to proceed.")
        sys.exit(1)

    db = SessionLocal()
    try:
        created = 0
        for silk_type_name, pairs in PAIRS.items():
            st = db.query(SilkType).filter(SilkType.silk_type_name == silk_type_name).first()
            if not st:
                print(f"Skipping {silk_type_name}: silk type not found")
                continue

            existing_pairs = {
                (cs.input_product_id, cs.output_product_id)
                for cs in db.query(ConversionStandard).filter(ConversionStandard.silk_type_id == st.id).all()
            }

            for (in_name, out_name), (out_min, out_max) in pairs.items():
                in_product = db.query(Product).filter(Product.product_name == in_name).first()
                out_product = db.query(Product).filter(Product.product_name == out_name).first()
                if not in_product or not out_product:
                    print(f"Skipping {silk_type_name}: '{in_name}' -> '{out_name}' — product not found")
                    continue
                if (in_product.id, out_product.id) in existing_pairs:
                    continue

                standard_input_qty = 100.0
                min_pct = round(out_min / standard_input_qty * 100, 4)
                max_pct = round(out_max / standard_input_qty * 100, 4)
                db.add(ConversionStandard(
                    silk_type_id=st.id, input_product_id=in_product.id, output_product_id=out_product.id,
                    standard_input_qty=standard_input_qty, output_min_qty=out_min, output_max_qty=out_max,
                    min_pct=min_pct, max_pct=max_pct, is_active=True,
                ))
                created += 1

        db.commit()
        print(f"Created {created} Conversion Standard(s) across Eri, Muga, and Mulberry.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
