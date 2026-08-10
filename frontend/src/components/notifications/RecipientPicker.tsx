"use client";
import { useMemo, useState } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { NotificationCandidate } from "@/lib/types";

// Searchable, optionally district-grouped multi-select for the notifications
// recipient picker. Grouping (with a per-district "select all" indeterminate
// checkbox) mirrors StapGroupPicker's exact mechanic; ungrouped mode is a flat
// searchable list, used for the District Admin picker (already bounded to ~35).
export function RecipientPicker({ candidates, selected, onChange, groupByDistrict }: {
  candidates: NotificationCandidate[]; selected: string[]; onChange: (next: string[]) => void;
  groupByDistrict?: boolean;
}) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return candidates;
    return candidates.filter((c) =>
      (c.name || "").toLowerCase().includes(needle) ||
      c.mobile_no.toLowerCase().includes(needle) ||
      (c.district_name || "").toLowerCase().includes(needle) ||
      (c.fig_name || "").toLowerCase().includes(needle));
  }, [candidates, q]);

  const byDistrict = useMemo(() => {
    const out: Record<string, NotificationCandidate[]> = {};
    for (const c of filtered) {
      const key = c.district_name || "—";
      out[key] = out[key] || [];
      out[key].push(c);
    }
    return out;
  }, [filtered]);

  function toggleOne(id: string, checked: boolean) {
    onChange(checked ? [...selected, id] : selected.filter((x) => x !== id));
  }
  function toggleMany(ids: string[], checked: boolean) {
    onChange(checked ? Array.from(new Set([...selected, ...ids])) : selected.filter((x) => !ids.includes(x)));
  }

  const filteredIds = filtered.map((c) => c.id);
  const allVisibleSelected = filteredIds.length > 0 && filteredIds.every((id) => selected.includes(id));

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <MagnifyingGlass size={16} color="#5C635B" />
        <input className="input flex-1 text-sm" placeholder="Search by name, mobile or district"
               value={q} onChange={(e) => setQ(e.target.value)} data-testid="recipient-search" />
      </div>
      <div className="flex items-center gap-3 mb-2">
        <button type="button" className="text-xs font-semibold" style={{ color: "var(--primary)" }}
                onClick={() => toggleMany(filteredIds, !allVisibleSelected)}>
          {allVisibleSelected ? "Clear visible" : "Select all visible"}
        </button>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>{selected.length} selected</span>
      </div>
      <div className="max-h-64 overflow-y-auto p-3 border rounded space-y-3" style={{ borderColor: "var(--border)" }}>
        {groupByDistrict ? (
          Object.entries(byDistrict).sort(([a], [b]) => a.localeCompare(b)).map(([districtName, group]) => {
            const ids = group.map((c) => c.id);
            const selCount = ids.filter((id) => selected.includes(id)).length;
            const allSelected = ids.length > 0 && selCount === ids.length;
            const someSelected = selCount > 0 && !allSelected;
            return (
              <div key={districtName}>
                <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide mb-1" style={{ color: "var(--text-muted)" }}>
                  <input type="checkbox" checked={allSelected}
                         ref={(el) => { if (el) el.indeterminate = someSelected; }}
                         onChange={(e) => toggleMany(ids, e.target.checked)} />
                  {districtName} ({ids.length})
                </label>
                <div className="space-y-0.5 pl-5">
                  {group.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 py-1 text-sm">
                      <input type="checkbox" checked={selected.includes(c.id)}
                             onChange={(e) => toggleOne(c.id, e.target.checked)}
                             data-testid={`pick-${c.id}`} />
                      <span>{c.name || c.mobile_no}</span>
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>· {c.fig_name || c.mobile_no}</span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          filtered.map((c) => (
            <label key={c.id} className="flex items-center gap-2 py-1 text-sm">
              <input type="checkbox" checked={selected.includes(c.id)} onChange={(e) => toggleOne(c.id, e.target.checked)}
                     data-testid={`pick-${c.id}`} />
              <span>{c.name || c.mobile_no}</span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>· {c.district_name || "—"}</span>
            </label>
          ))
        )}
        {filtered.length === 0 && (
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>
            {q ? `No matches for "${q}"` : "No users available"}
          </div>
        )}
      </div>
    </div>
  );
}
