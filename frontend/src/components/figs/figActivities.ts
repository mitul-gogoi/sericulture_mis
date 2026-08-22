import type { SilkTypeActivityProduct } from "@/lib/types";

/**
 * A FIG is described by one silk type plus one or more activities — never a product.
 * These helpers collapse the STAP catalogue (20 OUTPUT rows) down to the 15 distinct
 * (silk type, activity) pairs the FIG screens actually speak in.
 */
export interface ActivityOption {
  activityId: string;
  activityName: string;
  /** A representative STAP row for this pair — the FIG list filter is still keyed on a
   *  STAP id server-side, where it matches on that row's activity + silk type. */
  stapId: string;
}

export function activityOptgroups(staps: SilkTypeActivityProduct[]): [string, ActivityOption[]][] {
  const groups: Record<string, ActivityOption[]> = {};
  for (const s of staps) {
    const key = s.silk_type_name || "—";
    groups[key] = groups[key] || [];
    if (!groups[key].some((a) => a.activityId === s.activity_id)) {
      groups[key].push({ activityId: s.activity_id, activityName: s.activity_name || "—", stapId: s.id });
    }
  }
  for (const list of Object.values(groups)) list.sort((a, b) => a.activityName.localeCompare(b.activityName));
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
}

/** "Muga · Muga Rearing, Muga Reeling" — the FIG's silk type and everything it runs. */
export function figActivityLabel(
  silkTypeId: string | null | undefined,
  activityIds: string[] | undefined,
  staps: SilkTypeActivityProduct[],
): string {
  const silkTypeName = staps.find((s) => s.silk_type_id === silkTypeId)?.silk_type_name;
  if (!silkTypeName) return "—";
  const names = (activityIds || [])
    .map((id) => staps.find((s) => s.activity_id === id)?.activity_name)
    .filter((n): n is string => !!n)
    .sort((a, b) => a.localeCompare(b));
  return names.length ? `${silkTypeName} · ${names.join(", ")}` : silkTypeName;
}
