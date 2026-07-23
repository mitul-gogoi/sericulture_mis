"use client";
import { ActivityPicker } from "./ActivityPicker";
import type { SchemeFormState } from "./schemeForm";
import type { SilkType, Activity } from "@/lib/types";

export function SchemeBasicFields({
  form, setForm, silkTypes, activityOptions,
}: {
  form: SchemeFormState; setForm: (f: SchemeFormState) => void;
  silkTypes: SilkType[]; activityOptions: Activity[];
}) {
  return (
    <>
      <label className="col-span-2"><span className="label-tag block mb-1">Scheme Name *</span>
        <input required data-testid="schemes-input-name" className="input"
          value={form.scheme_name} onChange={(e) => setForm({ ...form, scheme_name: e.target.value })} /></label>
      <label className="col-span-2"><span className="label-tag block mb-1">Description</span>
        <textarea data-testid="schemes-input-desc" className="input" rows={2}
          value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
      <label><span className="label-tag block mb-1">Silk Type (for activity picker)</span>
        <select data-testid="schemes-input-silk-type" className="input" value={form.silk_type_id}
          onChange={(e) => setForm({ ...form, silk_type_id: e.target.value, activity_ids: [] })}>
          <option value="">Any</option>
          {silkTypes.map((s) => (<option key={s.id} value={s.id}>{s.silk_type_name}</option>))}
        </select></label>
      <label><span className="label-tag block mb-1">Support Type</span>
        <select data-testid="schemes-input-support" className="input"
          value={form.support_type} onChange={(e) => setForm({ ...form, support_type: e.target.value })}>
          <option>Cash</option><option>Kind</option><option>Training</option>
        </select>
        {form.support_type === "Training" && (
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Beneficiaries nominated under a Training scheme require State Admin approval
            (Schemes → Beneficiaries) before they're finalized.
          </p>
        )}</label>
      <div className="col-span-2">
        <span className="label-tag block mb-1">Applicable Activities</span>
        <ActivityPicker activities={activityOptions} selected={form.activity_ids}
          onChange={(next) => setForm({ ...form, activity_ids: next })} />
      </div>
      <label><span className="label-tag block mb-1">Total Budget (₹)</span>
        <input type="number" data-testid="schemes-input-budget" className="input"
          value={form.total_budget_rs} onChange={(e) => setForm({ ...form, total_budget_rs: parseFloat(e.target.value) || 0 })} /></label>
      <label><span className="label-tag block mb-1">Disbursement</span>
        <select data-testid="schemes-input-disb" className="input"
          value={form.disbursement_type} onChange={(e) => setForm({ ...form, disbursement_type: e.target.value })}>
          <option>DBT</option><option>Material</option><option>Both</option>
        </select></label>
    </>
  );
}
