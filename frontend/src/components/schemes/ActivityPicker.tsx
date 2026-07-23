"use client";
import { useMemo } from "react";
import type { Activity } from "@/lib/types";

export function ActivityPicker({ activities, selected, onChange }: {
  activities: Activity[]; selected: string[]; onChange: (next: string[]) => void;
}) {
  const sorted = useMemo(() => [...activities].sort((a, b) => a.step_no - b.step_no), [activities]);

  function toggleOne(id: string, checked: boolean) {
    onChange(checked ? [...selected, id] : selected.filter((x) => x !== id));
  }
  function toggleAll(checked: boolean) {
    const ids = sorted.map((a) => a.id);
    onChange(checked ? Array.from(new Set([...selected, ...ids])) : selected.filter((x) => !ids.includes(x)));
  }

  if (activities.length === 0) {
    return <p className="text-sm" style={{ color: "var(--text-muted)" }}>Select a silk type first.</p>;
  }

  const ids = sorted.map((a) => a.id);
  const selCount = ids.filter((id) => selected.includes(id)).length;
  const allSelected = ids.length > 0 && selCount === ids.length;
  const someSelected = selCount > 0 && !allSelected;

  return (
    <div className="max-h-56 overflow-y-auto p-3 border rounded space-y-2" style={{ borderColor: "var(--border)" }}>
      <label className="flex items-center gap-2 text-sm font-semibold mb-1">
        <input type="checkbox" checked={allSelected}
               ref={(el) => { if (el) el.indeterminate = someSelected; }}
               onChange={(e) => toggleAll(e.target.checked)} />
        Select all
      </label>
      <div className="grid grid-cols-2 gap-1 pl-5">
        {sorted.map((a) => (
          <label key={a.id} className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={selected.includes(a.id)}
                   onChange={(e) => toggleOne(a.id, e.target.checked)} />
            {a.activity_name}
          </label>
        ))}
      </div>
    </div>
  );
}
