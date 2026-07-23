"use client";
import { Gift, Pencil, Archive, PaperPlaneTilt, Eye } from "@phosphor-icons/react";
import type { Scheme } from "@/lib/types";

export function SchemeCard({
  scheme, isSA, onView, onEdit, onToggleActive, togglePending, onPublish, publishPending, onArchive, archivePending,
}: {
  scheme: Scheme; isSA: boolean; onView: () => void; onEdit: () => void;
  onToggleActive: () => void; togglePending: boolean;
  onPublish: () => void; publishPending: boolean;
  onArchive: () => void; archivePending: boolean;
}) {
  const s = scheme;
  return (
    <div className="card p-5" data-testid={`schemes-card-${s.id}`}>
      <div className="flex items-start justify-between">
        <Gift size={22} weight="duotone" color="#D9A036" />
        <div className="flex gap-1 flex-wrap justify-end">
          {s.is_archived && <span className="badge badge-muted">Archived</span>}
          {s.is_active
            ? <span className="badge badge-success">Active</span>
            : <span className="badge badge-muted">Inactive</span>}
        </div>
      </div>
      <div className="font-heading text-lg font-bold mt-2">{s.scheme_name}</div>
      <div className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{s.description || "—"}</div>
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="badge badge-muted">{s.beneficiary_kind}</span>
        <span className="badge badge-muted">{s.disbursement_type}</span>
        <span className="badge badge-success">{s.support_type}</span>
        <span className="badge badge-warning">₹{(s.total_budget_rs || 0).toLocaleString()}</span>
        {s.target_all_districts
          ? <span className="badge badge-muted">All districts</span>
          : <span className="badge badge-muted">{(s.target_district_ids || []).length} district(s)</span>}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={onView} className="btn-secondary btn-sm inline-flex items-center gap-1">
          <Eye size={12} />View</button>
        {isSA && (
          <>
            <button onClick={onEdit} data-testid={`schemes-edit-${s.id}`}
              className="btn-secondary btn-sm inline-flex items-center gap-1"><Pencil size={12} />Edit</button>
            <button onClick={onToggleActive} disabled={togglePending}
              data-testid={`schemes-toggle-${s.id}`}
              className={s.is_active ? "btn-secondary btn-sm" : "btn-primary btn-sm"}>
              {s.is_active ? "Deactivate" : "Activate"}
            </button>
            {s.is_active && (
              <button onClick={onPublish} disabled={publishPending}
                className="btn-secondary btn-sm inline-flex items-center gap-1">
                <PaperPlaneTilt size={12} />Publish
              </button>
            )}
            {!s.is_active && !s.is_archived && (
              <button onClick={() => { if (window.confirm(`Archive "${s.scheme_name}"? It will be hidden by default.`)) onArchive(); }}
                disabled={archivePending}
                className="btn-secondary btn-sm inline-flex items-center gap-1" style={{ color: "var(--error)" }}>
                <Archive size={12} />Archive
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
