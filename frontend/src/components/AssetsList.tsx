"use client";
import { Trash } from "@phosphor-icons/react";
import type { AssetInstance } from "@/lib/types";

interface AssetsListProps {
  assets: AssetInstance[];
  onDelete?: (id: string) => void;
}

function statusBadge(status: AssetInstance["status"]) {
  if (status === "FUNCTIONAL") return <span className="badge badge-success">Functional</span>;
  if (status === "UNDER_REPAIR") return <span className="badge badge-warning">Under Repair</span>;
  if (status === "NON_FUNCTIONAL") return <span className="badge badge-error">Non-Functional</span>;
  return <span className="badge badge-muted">Decommissioned</span>;
}

function verificationBadge(status: AssetInstance["verification_status"]) {
  if (status === "CIRCLE_VERIFIED") return <span className="badge badge-success">Verified</span>;
  if (status === "DISPUTED") return <span className="badge badge-error">Disputed</span>;
  return <span className="badge badge-muted">Unverified</span>;
}

export function AssetsList({ assets, onDelete }: AssetsListProps) {
  if (assets.length === 0) {
    return <p className="text-sm" style={{ color: "var(--text-muted)" }}>No assets recorded yet.</p>;
  }
  return (
    <table className="seri-table">
      <thead><tr><th>Asset Type</th><th>Qty</th><th>Acquired</th><th>Status</th><th>Verification</th>{onDelete && <th></th>}</tr></thead>
      <tbody>
        {assets.map((a) => (
          <tr key={a.id}>
            <td>{a.asset_type_name || "—"}</td>
            <td>{a.quantity}</td>
            <td>{a.acquisition_date || "—"}</td>
            <td>{statusBadge(a.status)}</td>
            <td>{verificationBadge(a.verification_status)}</td>
            {onDelete && (
              <td>
                {a.acquisition_mode !== "SCHEME_DISBURSEMENT" && (
                  <button type="button" className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                    onClick={() => { if (window.confirm(`Delete ${a.asset_type_name || "this asset"}?`)) onDelete(a.id); }}>
                    <Trash size={14} weight="bold" />Delete
                  </button>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
