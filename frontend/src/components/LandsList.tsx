"use client";
import { Trash } from "@phosphor-icons/react";
import type { Land } from "@/lib/types";

interface LandsListProps {
  lands: Land[];
  onDelete?: (id: string) => void;
}

function statusBadge(status: string) {
  if (status === "Verified") return <span className="badge badge-success">Verified</span>;
  if (status === "Pending") return <span className="badge badge-warning">Pending</span>;
  if (status === "Failed") return <span className="badge badge-error">Failed</span>;
  return <span className="badge badge-muted">Not submitted</span>;
}

export function LandsList({ lands, onDelete }: LandsListProps) {
  if (lands.length === 0) {
    return <p className="text-sm" style={{ color: "var(--text-muted)" }}>No land parcels recorded yet.</p>;
  }
  return (
    <table className="seri-table">
      <thead><tr><th>Dag No</th><th>Patta No</th><th>Type</th><th>Area (bigha)</th><th>GPS Status</th>{onDelete && <th></th>}</tr></thead>
      <tbody>
        {lands.map((l) => (
          <tr key={l.id}>
            <td>{l.dag_no || "—"}</td>
            <td>{l.patta_no || "—"}</td>
            <td>{l.land_type}</td>
            <td>{l.land_area_bigha ? l.land_area_bigha.toFixed(2) : "—"}</td>
            <td>{statusBadge(l.gps_verified)}</td>
            {onDelete && (
              <td>
                {l.gps_verified === "Not Submitted" && (
                  <button type="button" className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                    onClick={() => { if (window.confirm(`Delete land parcel ${l.dag_no || l.id}?`)) onDelete(l.id); }}>
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
