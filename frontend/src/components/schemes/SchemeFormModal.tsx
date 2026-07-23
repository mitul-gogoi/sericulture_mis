"use client";
import { X } from "@phosphor-icons/react";
import { SchemeBasicFields } from "./SchemeBasicFields";
import { SchemeTargetingFields } from "./SchemeTargetingFields";
import type { SchemeFormState } from "./schemeForm";
import type { Scheme, SilkType, Activity, District, AssetType, Caste, Religion, EducationLevel } from "@/lib/types";

export function SchemeFormModal({
  editing, form, setForm, onCancel, onSubmit, submitPending,
  silkTypes, activityOptions, districts, assetTypes, castes, religions, educationLevels,
}: {
  editing: Scheme | null; form: SchemeFormState; setForm: (f: SchemeFormState) => void;
  onCancel: () => void; onSubmit: () => void; submitPending: boolean;
  silkTypes: SilkType[]; activityOptions: Activity[]; districts: District[]; assetTypes: AssetType[];
  castes: Caste[]; religions: Religion[]; educationLevels: EducationLevel[];
}) {
  return (
    <div className="card p-5 mb-4" data-testid="schemes-form">
      <div className="flex items-center justify-between mb-3">
        <div className="font-heading text-lg font-bold">{editing ? `Edit ${editing.scheme_name}` : "New scheme"}</div>
        <button onClick={onCancel}><X size={18} /></button>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }} className="grid grid-cols-2 gap-3">
        <SchemeBasicFields form={form} setForm={setForm} silkTypes={silkTypes} activityOptions={activityOptions} />
        <SchemeTargetingFields form={form} setForm={setForm} districts={districts} silkTypes={silkTypes}
          assetTypes={assetTypes} castes={castes} religions={religions} educationLevels={educationLevels} />
        <div className="col-span-2 flex justify-end gap-2 mt-2">
          <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
          <button type="submit" disabled={submitPending}
            data-testid="schemes-form-submit" className="btn-primary">{editing ? "Save changes" : "Create"}</button>
        </div>
      </form>
    </div>
  );
}
