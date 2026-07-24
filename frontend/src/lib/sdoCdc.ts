import type { SericultureCircle, SubdivisionCdc } from "@/lib/types";

export function sdoCdcName(
  circleId: string | null | undefined,
  circles: SericultureCircle[],
  subdivisionCdcs: SubdivisionCdc[]
): string {
  const circle = circles.find((c) => c.id === circleId);
  if (!circle?.subdivision_cdc_id) return "—";
  return subdivisionCdcs.find((s) => s.id === circle.subdivision_cdc_id)?.office_name || "—";
}
