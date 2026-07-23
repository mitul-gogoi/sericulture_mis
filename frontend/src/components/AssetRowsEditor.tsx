"use client";
import { Plus, X } from "@phosphor-icons/react";
import type { AssetType } from "@/lib/types";

export interface AssetRow {
  asset_type_id: string;
  quantity: string;
  acquisition_year: string;
}

export function emptyAssetRow(): AssetRow {
  return { asset_type_id: "", quantity: "1", acquisition_year: "" };
}

interface AssetRowsEditorProps {
  value: AssetRow[];
  onChange: (next: AssetRow[]) => void;
  assetTypes: AssetType[];
}

// Farmer self-declaration only supports asset types a lone individual can own —
// FIG-level shared assets (Chawki Rearing Centres, CFCs) are recorded against the FIG instead.
export function AssetRowsEditor({ value, onChange, assetTypes }: AssetRowsEditorProps) {
  const eligible = assetTypes.filter((t) => t.is_active && t.ownership_level !== "FIG");

  const updateRow = (idx: number, field: keyof AssetRow, val: string) => {
    onChange(value.map((row, i) => (i === idx ? { ...row, [field]: val } : row)));
  };
  const removeRow = (idx: number) => onChange(value.filter((_, i) => i !== idx));
  const addRow = () => onChange([...value, emptyAssetRow()]);

  return (
    <div className="space-y-2">
      {value.map((row, idx) => (
        <div key={idx} className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-end p-3 border rounded" style={{ borderColor: "var(--border)" }}>
          <div className="sm:col-span-2"><label className="label-tag">Asset Type</label>
            <select className="input mt-1" value={row.asset_type_id} onChange={(e) => updateRow(idx, "asset_type_id", e.target.value)}>
              <option value="">Select…</option>
              {eligible.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select></div>
          <div><label className="label-tag">Quantity</label>
            <input type="number" min={1} className="input mt-1" value={row.quantity}
                   onChange={(e) => updateRow(idx, "quantity", e.target.value)} /></div>
          <div><label className="label-tag">Year Acquired</label>
            <input type="number" min={1950} max={2100} className="input mt-1" value={row.acquisition_year}
                   placeholder="e.g. 2022"
                   onChange={(e) => updateRow(idx, "acquisition_year", e.target.value)} /></div>
          <button type="button" className="btn-secondary inline-flex items-center gap-1 justify-center sm:col-span-4" onClick={() => removeRow(idx)}>
            <X size={14} weight="bold" />Remove
          </button>
        </div>
      ))}
      <button type="button" className="btn-secondary inline-flex items-center gap-2" onClick={addRow}>
        <Plus size={14} weight="bold" />Add existing asset
      </button>
    </div>
  );
}
