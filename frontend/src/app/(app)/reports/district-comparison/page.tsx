"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";

interface DistrictComp {
  district_id: string; district_name: string; total_figs: number;
  submission_pct: number; yield_achievement_pct: number; gps_verified_pct: number; scheme_utilization_pct: number;
}
interface ComparisonResponse { months: string[]; districts: DistrictComp[]; }

export default function DistrictComparisonPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data } = useQuery<ComparisonResponse>({
    queryKey: ["district-comparison", month, fy],
    queryFn: async () => (await api.get("/reports/district-comparison", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
    enabled: user?.role === "STATE_ADMIN",
  });
  if (user?.role !== "STATE_ADMIN") return <div>Only State Admins can access district comparison.</div>;
  const rows = data?.districts || [];
  const periodLabel = data?.months?.length
    ? (data.months.length > 1 ? `${data.months[0]} – ${data.months[data.months.length - 1]}` : data.months[0])
    : "the current month";

  return (
    <div>
      <div className="mb-5"><h1 className="font-heading text-3xl font-extrabold">District comparison</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Submission rate and yield achievement are for {periodLabel}; GPS verification and scheme utilization are all-time snapshots.
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
        <ExportButtons report="district-comparison" params={fy ? { fiscal_year: fy } : month ? { month } : {}} />
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>District</th><th>FIGs</th><th>Submission %</th><th>Yield achievement %</th><th>GPS verified %</th><th>Scheme utilization %</th></tr></thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.district_id}>
                <td className="font-semibold">{d.district_name}</td>
                <td>{d.total_figs}</td>
                <td>{d.submission_pct}%</td>
                <td>{d.yield_achievement_pct}%</td>
                <td>{d.gps_verified_pct}%</td>
                <td>{d.scheme_utilization_pct}%</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={6} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data yet</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
