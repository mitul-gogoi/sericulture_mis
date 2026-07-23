"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";

interface RatioRow {
  district_id: string; district_name: string;
  product_id: string; product_name: string; unit_of_measure: string;
  byproduct_qty: number; parent_actual_yield: number; parent_count: number; ratio_pct: number | null;
}
interface RatioResponse { months: string[] | null; rows: RatioRow[]; }

export default function ByproductRatioPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data } = useQuery<RatioResponse>({
    queryKey: ["byproduct-ratio", month, fy],
    queryFn: async () => (await api.get("/reports/analytics/byproduct-ratio", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
    enabled: user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN",
  });

  if (user?.role === "FIG_PRESIDENT") return <div>Not available for your role.</div>;
  const rows = data?.rows || [];

  return (
    <div>
      <div className="mb-5"><h1 className="font-heading text-3xl font-extrabold">Byproduct yield ratio</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Byproduct output (pupae, reel waste, gicha/ghicha yarn) as a percentage of the parent yield that produced it, by district.
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
        <ExportButtons report="byproduct-ratio" params={fy ? { fiscal_year: fy } : month ? { month } : {}} />
      </div>

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th>District</th><th>Byproduct</th><th>Unit</th><th>Byproduct Qty</th><th>Parent Actual Yield</th><th>Ratio %</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.district_id}-${r.product_id}`}>
                <td className="font-semibold">{r.district_name}</td>
                <td>{r.product_name}</td>
                <td>{r.unit_of_measure}</td>
                <td>{r.byproduct_qty.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                <td>{r.parent_actual_yield.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                <td>{r.ratio_pct != null ? `${r.ratio_pct}%` : "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={6} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data yet</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
