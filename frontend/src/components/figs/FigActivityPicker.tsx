"use client";
import { useMemo } from "react";
import type { SilkTypeActivityProduct, Farmer } from "@/lib/types";

/**
 * Picks the activities a FIG runs.
 *
 * Two rules, both also enforced by the server so they cannot be bypassed through the API:
 *
 *  - Only activities the SELECTED MEMBERS actually perform are offered. A FIG's activities
 *    should describe its real membership, so the list is derived rather than free.
 *  - A FIG is built around exactly ONE silk type. Once an activity is ticked, the other
 *    silk types grey out; clearing the selection unlocks them again.
 *
 * No products. Which inputs and outputs an activity involves follows from the activity, and
 * the actual product is chosen per submission.
 */
export function FigActivityPicker({
  staps, members, silkTypeId, activityIds, onChange,
}: {
  staps: SilkTypeActivityProduct[];
  members: Farmer[];
  silkTypeId: string;
  activityIds: string[];
  onChange: (silkTypeId: string, activityIds: string[]) => void;
}) {
  // Union of the members' STAP assignments, resolved to distinct (silk type, activity) pairs.
  const available = useMemo(() => {
    const memberStapIds = new Set<string>();
    for (const m of members) for (const id of m.stap_ids || []) memberStapIds.add(id);

    const bySilk: Record<string, {
      silkTypeId: string; activities: { id: string; name: string }[];
    }> = {};
    for (const s of staps) {
      if (!memberStapIds.has(s.id)) continue;
      const key = s.silk_type_name || "—";
      bySilk[key] = bySilk[key] || { silkTypeId: s.silk_type_id, activities: [] };
      if (!bySilk[key].activities.some((a) => a.id === s.activity_id)) {
        bySilk[key].activities.push({ id: s.activity_id, name: s.activity_name || "—" });
      }
    }
    return bySilk;
  }, [staps, members]);

  const names = Object.keys(available).sort((a, b) => a.localeCompare(b));

  if (members.length === 0) {
    return (
      <div className="p-3 border rounded text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
        Pick the members above first — the activities offered here are the ones they actually perform.
      </div>
    );
  }
  if (names.length === 0) {
    return (
      <div className="p-3 border rounded text-sm" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
        None of the selected members has any sericulture activity recorded. Add one to their
        farmer record first.
      </div>
    );
  }

  function toggle(stId: string, activityId: string, checked: boolean) {
    // Switching silk type is only possible from a clean slate, which is what keeps a FIG to
    // exactly one — see the disabled state below.
    const base = stId === silkTypeId ? activityIds : [];
    const next = checked ? [...base, activityId] : base.filter((x) => x !== activityId);
    onChange(next.length ? stId : "", next);
  }

  return (
    <div className="max-h-56 overflow-y-auto p-3 border rounded space-y-3" style={{ borderColor: "var(--border)" }}>
      {names.map((silkTypeName) => {
        const group = available[silkTypeName];
        const locked = silkTypeId !== "" && group.silkTypeId !== silkTypeId;
        return (
          <div key={silkTypeName} style={locked ? { opacity: 0.45 } : undefined}>
            <div className="text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--text-muted)" }}>
              {silkTypeName}
              {locked && <span className="ml-2 normal-case font-normal">— a FIG runs one silk type only</span>}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 pl-1">
              {group.activities.sort((a, b) => a.name.localeCompare(b.name)).map((a) => (
                <label key={a.id}
                       className={`flex items-center gap-2 text-sm py-0.5 ${locked ? "cursor-not-allowed" : ""}`}>
                  <input type="checkbox" disabled={locked}
                         data-testid={`fig-activity-${a.id}`}
                         checked={group.silkTypeId === silkTypeId && activityIds.includes(a.id)}
                         onChange={(e) => toggle(group.silkTypeId, a.id, e.target.checked)} />
                  <span>{a.name}</span>
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
