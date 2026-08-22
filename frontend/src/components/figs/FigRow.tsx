"use client";
import { Eye } from "@phosphor-icons/react";
import { figDocumentsPending } from "@/components/figs/FigDocumentsStep";
import { figActivityLabel } from "./figActivities";
import type { Fig, District, SericultureCircle, SilkTypeActivityProduct } from "@/lib/types";

export function FigRow({ f, staps, districts, allCircles, onView }: {
  f: Fig; staps: SilkTypeActivityProduct[]; districts: District[]; allCircles: SericultureCircle[]; onView: () => void;
}) {
  const district = districts.find((d) => d.id === f.district_id);
  const circle = allCircles.find((c) => c.id === f.seri_circle_id);
  const names = f.member_names || [];
  const shown = names.slice(0, 3).join(", ");
  const extra = names.length > 3 ? ` +${names.length - 3} more` : "";
  return (
    <tr>
      <td className="font-mono text-xs">{f.fig_code}</td>
      <td className="font-semibold">{f.fig_name}</td>
      <td>{figActivityLabel(f.silk_type_id, f.activity_ids, staps)}</td>
      <td>{district?.district_name || "—"}</td>
      <td>{circle?.circle_name || "—"}</td>
      <td>{f.total_members}</td>
      <td className="text-xs">{names.length ? `${shown}${extra}` : "—"}</td>
      <td className="whitespace-nowrap">
        {f.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>}
        {figDocumentsPending(f) && <span className="badge badge-warning ml-1" title="Founding minutes and/or group photo not yet uploaded">Documents pending</span>}
      </td>
      <td>
        <button onClick={onView} className="btn-secondary px-2 py-1 text-xs inline-flex items-center gap-1" data-testid={`view-fig-${f.id}`}>
          <Eye size={14} weight="bold" /> View
        </button>
      </td>
    </tr>
  );
}
