"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";
import type { Activity } from "@/lib/types";

interface ActivityEfficiencyRow {
  district_id: string; district_name: string;
  output_qty: number; input_qty: number; efficiency_ratio: number | null;
}
interface ActivityEfficiencyResponse {
  months: string[]; activity: { id: string; activity_name: string }; rows: ActivityEfficiencyRow[];
}

export default function ActivityEfficiencyPage() {
  const { user } = useAuth();
  const [activityId, setActivityId] = useState("");
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");

  const { data: activities = [] } = useQuery<Activity[]>({
    queryKey: ["master-activities-all"],
    queryFn: async () => (await api.get("/master/activities?all=true")).data,
  });

  const params = { activity_id: activityId, ...(fy ? { fiscal_year: fy } : month ? { month } : {}) };
  const { data } = useQuery<ActivityEfficiencyResponse>({
    queryKey: ["activity-efficiency", activityId, month, fy],
    queryFn: async () => (await api.get("/reports/analytics/activity-efficiency", { params })).data,
    enabled: !!activityId && (user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN"),
  });

  if (user?.role === "FIG_PRESIDENT") return <div>Not available for your role.</div>;
  const rows = data?.rows || [];

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">Activity Efficiency</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Output quantity produced per unit of input consumed for any activity, by district — a generalized conversion-efficiency view.
        </p>
      </div>

      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="label-tag">Activity</label>
          <select className="input max-w-xs" value={activityId} onChange={(e) => setActivityId(e.target.value)}>
            <option value="">Select an activity…</option>
            {activities.map((a) => (
              <option key={a.id} value={a.id}>{a.silk_type_name ? `${a.silk_type_name}: ` : ""}{a.activity_name}</option>
            ))}
          </select>
          <label className="label-tag">Month</label>
          <input type="month" className="input max-w-xs" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
          <label className="label-tag">or fiscal year</label>
          <select className="input max-w-xs" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
            <option value="">Select</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <ExportButtons report="activity-efficiency" params={params} />
      </div>

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th>District</th><th>Output Qty</th><th>Input Qty</th><th>Efficiency Ratio</th></tr></thead>
          <tbody>
            {!activityId ? (
              <tr><td colSpan={4} className="text-center py-8" style={{ color: "var(--text-muted)" }}>Select an activity to view its efficiency</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={4} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data yet</td></tr>
            ) : rows.map((r) => (
              <tr key={r.district_id}>
                <td className="font-semibold">{r.district_name}</td>
                <td>{r.output_qty.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                <td>{r.input_qty.toLocaleString(undefined, { maximumFractionDigits: 1 })}</td>
                <td>{r.efficiency_ratio ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
