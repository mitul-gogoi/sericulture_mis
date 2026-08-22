"use client";
import { useMemo } from "react";
import type { SilkTypeActivityProduct } from "@/lib/types";

/**
 * Silk type -> ACTIVITY picker.
 *
 * Products are deliberately not shown. Which inputs and outputs an activity involves is
 * already implied by the activity, and the actual product is chosen later at submission --
 * asking the District Admin for it at registration only duplicated rows (five activities
 * have two outputs each, so 20 rows collapse to 15).
 *
 * The value is still a list of STAP ids, so nothing downstream changes: ticking an activity
 * selects EVERY output row beneath it. A farmer doing Eri Rearing is associated with both
 * Eri Cocoon and Eri Pupa, exactly as if both boxes had been ticked before.
 */
interface ActivityGroup {
  activityId: string;
  activityName: string;
  stapIds: string[];
}

export function StapGroupPicker({ staps, selected, onChange }: {
  staps: SilkTypeActivityProduct[]; selected: string[]; onChange: (next: string[]) => void;
}) {
  const bySilkType = useMemo(() => {
    const out: Record<string, ActivityGroup[]> = {};
    for (const s of staps) {
      const st = s.silk_type_name || "—";
      out[st] = out[st] || [];
      let g = out[st].find((x) => x.activityId === s.activity_id);
      if (!g) {
        g = { activityId: s.activity_id, activityName: s.activity_name || "—", stapIds: [] };
        out[st].push(g);
      }
      g.stapIds.push(s.id);
    }
    return out;
  }, [staps]);

  const setIds = (ids: string[], checked: boolean) =>
    onChange(checked
      ? Array.from(new Set([...selected, ...ids]))
      : selected.filter((x) => !ids.includes(x)));

  return (
    <div className="max-h-64 overflow-y-auto p-3 border rounded space-y-3" style={{ borderColor: "var(--border)" }}>
      {Object.entries(bySilkType).sort(([a], [b]) => a.localeCompare(b)).map(([silkTypeName, groups]) => {
        const allIds = groups.flatMap((g) => g.stapIds);
        const selCount = allIds.filter((id) => selected.includes(id)).length;
        const allSelected = allIds.length > 0 && selCount === allIds.length;
        const someSelected = selCount > 0 && !allSelected;
        return (
          <div key={silkTypeName}>
            <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--text-muted)" }}>
              <input type="checkbox" checked={allSelected}
                     ref={(el) => { if (el) el.indeterminate = someSelected; }}
                     onChange={(e) => setIds(allIds, e.target.checked)} />
              {silkTypeName}
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 pl-5">
              {groups
                .sort((a, b) => a.activityName.localeCompare(b.activityName))
                .map((g) => {
                  // An activity counts as selected once any of its output rows is, so a
                  // farmer saved before this change still shows their activities ticked.
                  const on = g.stapIds.some((id) => selected.includes(id));
                  return (
                    <label key={g.activityId} className="flex items-center gap-2 text-sm py-0.5">
                      <input type="checkbox" checked={on}
                             data-testid={`stap-activity-${g.activityId}`}
                             onChange={(e) => setIds(g.stapIds, e.target.checked)} />
                      <span>{g.activityName}</span>
                    </label>
                  );
                })}
            </div>
          </div>
        );
      })}
      {Object.keys(bySilkType).length === 0 && (
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>
          No activities configured yet — add them under Master Data.
        </div>
      )}
    </div>
  );
}
