"use client";
import { Plus, X } from "@phosphor-icons/react";
import { LAND_TYPES } from "@/lib/types";

export interface LandRow {
  dag_no: string;
  patta_no: string;
  land_type: string;
}

export function emptyLandRow(): LandRow {
  return { dag_no: "", patta_no: "", land_type: "Owned" };
}

interface LandRowsEditorProps {
  value: LandRow[];
  onChange: (next: LandRow[]) => void;
}

export function LandRowsEditor({ value, onChange }: LandRowsEditorProps) {
  const updateRow = (idx: number, field: keyof LandRow, val: string) => {
    onChange(value.map((row, i) => (i === idx ? { ...row, [field]: val } : row)));
  };
  const removeRow = (idx: number) => onChange(value.filter((_, i) => i !== idx));
  const addRow = () => onChange([...value, emptyLandRow()]);

  return (
    <div className="space-y-2">
      {value.map((row, idx) => (
        <div key={idx} className="grid grid-cols-1 sm:grid-cols-4 gap-2 items-end p-3 border rounded" style={{ borderColor: "var(--border)" }}>
          <div><label className="label-tag">Dag No</label>
            <input className="input mt-1" value={row.dag_no} onChange={(e) => updateRow(idx, "dag_no", e.target.value)} /></div>
          <div><label className="label-tag">Patta No</label>
            <input className="input mt-1" value={row.patta_no} onChange={(e) => updateRow(idx, "patta_no", e.target.value)} /></div>
          <div><label className="label-tag">Land Type</label>
            <select className="input mt-1" value={row.land_type} onChange={(e) => updateRow(idx, "land_type", e.target.value)}>
              {LAND_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select></div>
          <button type="button" className="btn-secondary inline-flex items-center gap-1 justify-center" onClick={() => removeRow(idx)}>
            <X size={14} weight="bold" />Remove
          </button>
        </div>
      ))}
      <button type="button" className="btn-secondary inline-flex items-center gap-2" onClick={addRow}>
        <Plus size={14} weight="bold" />Add land
      </button>
    </div>
  );
}
