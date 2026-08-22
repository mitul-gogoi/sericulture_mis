import type { SericultureCircle, Lac } from "@/lib/types";

/** A Sericulture Circle's Legislative Assembly Constituency. Derived, never stored on the
 *  farmer or FIG — the circle is the single place the mapping lives. */
export function lacName(
  circleId: string | null | undefined,
  circles: SericultureCircle[],
  lacs: Lac[]
): string {
  const circle = circles.find((c) => c.id === circleId);
  if (!circle?.lac_id) return "—";
  return lacs.find((l) => l.id === circle.lac_id)?.lac_name || "—";
}
