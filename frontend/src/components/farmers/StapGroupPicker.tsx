"use client";
import { useMemo } from "react";
import type { SilkTypeActivityProduct } from "@/lib/types";

// Silk Type -> Activity/Product picker. Clicking a silk type's header checkbox
// bulk-selects/deselects every (OUTPUT-role) stap under that silk type in one click.
export function StapGroupPicker({ staps, selected, onChange }: {
  staps: SilkTypeActivityProduct[]; selected: string[]; onChange: (next: string[]) => void;
}) {
  const bySilkType = useMemo(() => {
    const out: Record<string, SilkTypeActivityProduct[]> = {};
    for (const s of staps) {
      const st = s.silk_type_name;
      out[st] = out[st] || [];
      out[st].push(s);
    }
    return out;
  }, [staps]);

  function toggleOne(id: string, checked: boolean) {
    onChange(checked ? [...selected, id] : selected.filter((x) => x !== id));
  }
  function toggleGroup(groupStaps: SilkTypeActivityProduct[], checked: boolean) {
    const ids = groupStaps.map((s) => s.id);
    onChange(checked ? Array.from(new Set([...selected, ...ids])) : selected.filter((x) => !ids.includes(x)));
  }

  return (
    <div className="max-h-64 overflow-y-auto p-3 border rounded space-y-3" style={{ borderColor: "var(--border)" }}>
      {Object.entries(bySilkType).sort(([a], [b]) => a.localeCompare(b)).map(([silkTypeName, silkTypeStaps]) => {
        const ids = silkTypeStaps.map((s) => s.id);
        const selCount = ids.filter((id) => selected.includes(id)).length;
        const allSelected = ids.length > 0 && selCount === ids.length;
        const someSelected = selCount > 0 && !allSelected;
        return (
          <div key={silkTypeName}>
            <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--text-muted)" }}>
              <input type="checkbox" checked={allSelected}
                     ref={(el) => { if (el) el.indeterminate = someSelected; }}
                     onChange={(e) => toggleGroup(silkTypeStaps, e.target.checked)} />
              {silkTypeName}
            </label>
            <div className="grid grid-cols-2 gap-1 pl-5">
              {silkTypeStaps.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={selected.includes(s.id)}
                         onChange={(e) => toggleOne(s.id, e.target.checked)} />
                  {s.activity_name} · {s.product_name}
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
