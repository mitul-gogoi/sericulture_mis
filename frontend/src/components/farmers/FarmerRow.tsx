"use client";
import { useMemo } from "react";
import { Eye, PencilSimple, Power } from "@phosphor-icons/react";
import type { Farmer } from "@/lib/types";

export function FarmerRow({ f, canView, canEdit, canToggle, onView, onEdit, onToggle }: {
  f: Farmer; canView: boolean; canEdit: boolean; canToggle: boolean;
  onView: () => void; onEdit: () => void; onToggle: () => void;
}) {
  const fullName = useMemo(
    () => [f.first_name, f.middle_name, f.last_name].filter(Boolean).join(" "),
    [f.first_name, f.middle_name, f.last_name],
  );
  return (
    <tr>
      <td className="font-mono text-xs">{f.farmer_code}</td>
      <td className="font-semibold">{fullName}</td>
      <td>{f.mobile_no}</td>
      <td>{f.village_name}</td>
      <td>{f.gender}</td>
      <td>{f.fig_name ? f.fig_name : <span className="badge badge-muted">Solo</span>}</td>
      <td>{f.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>}</td>
      {(canView || canEdit || canToggle) && (
        <td>
          <div className="flex items-center gap-2">
            {canView && (
              <button onClick={onView} className="btn-secondary px-2 py-1 text-xs inline-flex items-center gap-1" data-testid={`view-farmer-${f.id}`}>
                <Eye size={14} weight="bold" /> View
              </button>
            )}
            {canEdit && (
              <button onClick={onEdit} className="btn-secondary px-2 py-1 text-xs inline-flex items-center gap-1" data-testid={`edit-farmer-${f.id}`}>
                <PencilSimple size={14} weight="bold" /> Edit
              </button>
            )}
            {canToggle && (
              <button onClick={onToggle} className="btn-secondary px-2 py-1 text-xs inline-flex items-center gap-1" data-testid={`toggle-farmer-${f.id}`}>
                <Power size={14} weight="bold" /> {f.is_active ? "Deactivate" : "Activate"}
              </button>
            )}
          </div>
        </td>
      )}
    </tr>
  );
}
