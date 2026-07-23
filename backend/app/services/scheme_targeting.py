"""Resolve which farmers/FIGs a scheme's targeting criteria matches within a district.

The State Admin sets targeting criteria on the Scheme (districts, silk types, genders,
farmer types, activities); the District Admin then picks actual beneficiaries from the
candidate pool this module computes, scoped to their own district.

Every list-valued targeting field follows the same convention: an empty list means
"no restriction on this dimension" (matches everyone), a non-empty list means "must be
one of these".
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Farmer, Fig, FigMember, Beneficiary, SilkTypeActivityProduct
from app.services.assets import check_asset_cooldown


def scheme_targets_district(scheme, district_id: str) -> bool:
    return bool(scheme.target_all_districts) or district_id in (scheme.target_district_ids or [])


def _stap_silk_type_map(db: Session) -> dict:
    return {s.id: s.silk_type_id for s in db.query(SilkTypeActivityProduct).all()}


def candidate_farmers(db: Session, scheme, district_id: str) -> list[dict]:
    if not scheme_targets_district(scheme, district_id):
        return []

    stap_silk_type = _stap_silk_type_map(db)
    target_silk_types = set(scheme.target_silk_type_ids or [])
    target_genders = set(scheme.target_genders or [])
    target_farmer_types = set(scheme.target_farmer_types or [])
    target_activities = set(scheme.activity_ids or [])
    target_castes = set(scheme.target_caste_ids or [])
    target_religions = set(scheme.target_religion_ids or [])
    target_education = set(scheme.target_education_level_ids or [])

    farmers = db.query(Farmer).filter(Farmer.district_id == district_id, Farmer.is_active).all()
    existing_beneficiary_ids = {
        b.farmer_id for b in db.query(Beneficiary).filter(
            Beneficiary.scheme_id == scheme.id, Beneficiary.farmer_id.isnot(None)).all()
    }

    out = []
    for f in farmers:
        if target_genders and f.gender not in target_genders:
            continue
        if target_farmer_types and (f.farmer_type or "") not in target_farmer_types:
            continue
        if target_silk_types:
            farmer_silk_types = {stap_silk_type.get(sid) for sid in (f.stap_ids or [])}
            if not (farmer_silk_types & target_silk_types):
                continue
        if target_activities:
            if not (set(f.experience_activity_ids or []) & target_activities):
                continue
        if target_castes and (f.caste_id or "") not in target_castes:
            continue
        if target_religions and (f.religion_id or "") not in target_religions:
            continue
        if target_education and (f.education_level_id or "") not in target_education:
            continue
        if scheme.target_pwd_only and not f.is_pwd:
            continue

        cooldown = (check_asset_cooldown(db, "FARMER", f.id, scheme.grants_asset_type_id)
                   if scheme.grants_asset_type_id else None)
        out.append({
            "id": f.id, "farmer_code": f.farmer_code,
            "name": f"{f.first_name} {f.last_name}".strip(),
            "gender": f.gender, "farmer_type": f.farmer_type,
            "already_beneficiary": f.id in existing_beneficiary_ids,
            "cooldown": cooldown,
        })
    return out


def candidate_figs(db: Session, scheme, district_id: str) -> list[dict]:
    if not scheme_targets_district(scheme, district_id):
        return []

    stap_silk_type = _stap_silk_type_map(db)
    target_silk_types = set(scheme.target_silk_type_ids or [])
    target_activities = set(scheme.activity_ids or [])

    figs = db.query(Fig).filter(Fig.district_id == district_id, Fig.is_active).all()
    existing_beneficiary_ids = {
        b.fig_id for b in db.query(Beneficiary).filter(
            Beneficiary.scheme_id == scheme.id, Beneficiary.fig_id.isnot(None)).all()
    }

    out = []
    for g in figs:
        if target_silk_types and stap_silk_type.get(g.stap_id) not in target_silk_types:
            continue
        if target_activities:
            stap = db.query(SilkTypeActivityProduct).filter(SilkTypeActivityProduct.id == g.stap_id).first()
            if not stap or stap.activity_id not in target_activities:
                continue

        cooldown = (check_asset_cooldown(db, "FIG", g.id, scheme.grants_asset_type_id)
                   if scheme.grants_asset_type_id else None)
        out.append({
            "id": g.id, "fig_code": g.fig_code, "name": g.fig_name,
            "total_members": db.query(FigMember).filter(
                FigMember.fig_id == g.id, FigMember.is_active).count(),
            "already_beneficiary": g.id in existing_beneficiary_ids,
            "cooldown": cooldown,
        })
    return out
