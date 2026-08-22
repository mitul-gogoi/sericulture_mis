"use client";
import { toggleInList, type SchemeFormState } from "./schemeForm";
import type { SilkType, District, AssetType, Caste, Religion, EducationLevel, SchemeBeneficiaryKind } from "@/lib/types";

const GENDERS = ["Male", "Female", "Other"];
// Must stay in step with the Farmer Type options on the farmer register/edit forms --
// targeting a type no farmer can hold would silently match nobody.
const FARMER_TYPES = ["Small", "Medium", "Large"];

export function SchemeTargetingFields({
  form, setForm, districts, silkTypes, assetTypes, castes, religions, educationLevels,
}: {
  form: SchemeFormState; setForm: (f: SchemeFormState) => void;
  districts: District[]; silkTypes: SilkType[]; assetTypes: AssetType[];
  castes: Caste[]; religions: Religion[]; educationLevels: EducationLevel[];
}) {
  return (
    <>
      <div className="col-span-2 border-t pt-4 mt-1" style={{ borderColor: "var(--border)" }}>
        <div className="font-heading font-bold text-base mb-2">Targeting Criteria</div>
        <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
          Leave a dimension unchecked/empty to apply to everyone. The District Admin selects actual
          beneficiaries from whoever matches these criteria within their own district.
        </p>
      </div>

      <label><span className="label-tag block mb-1">Beneficiary Kind</span>
        <select data-testid="schemes-input-beneficiary-kind" className="input" value={form.beneficiary_kind}
          onChange={(e) => setForm({ ...form, beneficiary_kind: e.target.value as SchemeBeneficiaryKind })}>
          <option value="FARMER">Farmers</option>
          <option value="FIG">FIGs</option>
        </select></label>
      <label><span className="label-tag block mb-1">Asset Granted (auto-created on registration)</span>
        <select data-testid="schemes-input-grants-asset" className="input" value={form.grants_asset_type_id}
          onChange={(e) => setForm({ ...form, grants_asset_type_id: e.target.value })}>
          <option value="">None</option>
          {assetTypes.filter((t) => t.is_active).map((t) => (<option key={t.id} value={t.id}>{t.name}</option>))}
        </select></label>

      <div className="col-span-2">
        <label className="flex items-center gap-2 text-sm mb-2">
          <input type="checkbox" checked={form.target_all_districts}
            onChange={(e) => setForm({ ...form, target_all_districts: e.target.checked })} />
          All districts
        </label>
        {!form.target_all_districts && (
          <div className="grid grid-cols-3 gap-1 max-h-40 overflow-y-auto p-3 border rounded" style={{ borderColor: "var(--border)" }}>
            {districts.map((d) => (
              <label key={d.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.target_district_ids.includes(d.id)}
                  onChange={() => setForm({ ...form, target_district_ids: toggleInList(form.target_district_ids, d.id) })} />
                {d.district_name}
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="col-span-2">
        <span className="label-tag block mb-1">Target Silk Types (empty = all)</span>
        <div className="flex flex-wrap gap-3">
          {silkTypes.map((s) => (
            <label key={s.id} className="flex items-center gap-1.5 text-sm">
              <input type="checkbox" checked={form.target_silk_type_ids.includes(s.id)}
                onChange={() => setForm({ ...form, target_silk_type_ids: toggleInList(form.target_silk_type_ids, s.id) })} />
              {s.silk_type_name}
            </label>
          ))}
        </div>
      </div>

      {form.beneficiary_kind === "FARMER" && (
        <>
          <div>
            <span className="label-tag block mb-1">Target Genders (empty = all)</span>
            <div className="flex flex-wrap gap-3">
              {GENDERS.map((g) => (
                <label key={g} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" checked={form.target_genders.includes(g)}
                    onChange={() => setForm({ ...form, target_genders: toggleInList(form.target_genders, g) })} />
                  {g}
                </label>
              ))}
            </div>
          </div>
          <div>
            <span className="label-tag block mb-1">Target Farmer Types (empty = all)</span>
            <div className="flex flex-wrap gap-3">
              {FARMER_TYPES.map((t) => (
                <label key={t} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" checked={form.target_farmer_types.includes(t)}
                    onChange={() => setForm({ ...form, target_farmer_types: toggleInList(form.target_farmer_types, t) })} />
                  {t}
                </label>
              ))}
            </div>
          </div>
          <div>
            <span className="label-tag block mb-1">Target Caste (empty = all)</span>
            <div className="flex flex-wrap gap-3">
              {castes.map((c) => (
                <label key={c.id} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" checked={form.target_caste_ids.includes(c.id)}
                    onChange={() => setForm({ ...form, target_caste_ids: toggleInList(form.target_caste_ids, c.id) })} />
                  {c.caste_name}
                </label>
              ))}
            </div>
          </div>
          <div>
            <span className="label-tag block mb-1">Target Religion (empty = all)</span>
            <div className="flex flex-wrap gap-3">
              {religions.map((r) => (
                <label key={r.id} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" checked={form.target_religion_ids.includes(r.id)}
                    onChange={() => setForm({ ...form, target_religion_ids: toggleInList(form.target_religion_ids, r.id) })} />
                  {r.religion_name}
                </label>
              ))}
            </div>
          </div>
          <div className="col-span-2">
            <span className="label-tag block mb-1">Target Education Level (empty = all)</span>
            <div className="flex flex-wrap gap-3">
              {educationLevels.map((ed) => (
                <label key={ed.id} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" checked={form.target_education_level_ids.includes(ed.id)}
                    onChange={() => setForm({ ...form, target_education_level_ids: toggleInList(form.target_education_level_ids, ed.id) })} />
                  {ed.education_level_name}
                </label>
              ))}
            </div>
          </div>
          <div className="col-span-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.target_pwd_only}
                onChange={(e) => setForm({ ...form, target_pwd_only: e.target.checked })} />
              Target persons with disabilities (PWD) only
            </label>
          </div>
        </>
      )}
    </>
  );
}
