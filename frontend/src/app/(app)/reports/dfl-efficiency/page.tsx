"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";

interface DflRow {
  silk_type_id: string; silk_type_name: string;
  cocoon_actual: number; dfl_actual: number; kg_per_dfl: number | null;
}
interface DflResponse { months: string[] | null; district_id: string | null; rows: DflRow[]; }

export default function DflEfficiencyPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data } = useQuery<DflResponse>({
    queryKey: ["dfl-efficiency", month, fy],
    queryFn: async () => (await api.get("/reports/analytics/dfl-efficiency", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
    enabled: user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN",
  });

  if (user?.role === "FIG_PRESIDENT") return <div>Not available for your role.</div>;
  const rows = data?.rows || [];

  return (
    <div>
      <div className="mb-5"><h1 className="font-heading text-3xl font-extrabold">DFL yield efficiency</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Cocoon output per DFL (disease-free laying) brushed, by silk type — a core sericulture productivity metric.
        </p></div>

      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="label-tag">Month</label>
          <input type="month" className="input max-w-xs" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
          <label className="label-tag">or fiscal year</label>
          <select className="input max-w-xs" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
            <option value="">Select</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <ExportButtons report="dfl-efficiency" params={fy ? { fiscal_year: fy } : month ? { month } : {}} />
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Silk Type</th><th>Cocoon (kg)</th><th>DFL brushed</th><th>kg cocoon / DFL</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.silk_type_id}>
                <td className="font-semibold">{r.silk_type_name}</td>
                <td>{r.cocoon_actual.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                <td>{r.dfl_actual.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                <td>{r.kg_per_dfl ?? "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={4} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data yet</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
