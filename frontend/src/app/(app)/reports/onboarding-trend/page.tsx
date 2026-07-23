"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";

interface OnboardingResponse {
  months: string[];
  farmers_monthly: number[]; farmers_total_to_date: number;
  figs_monthly: number[]; figs_total_to_date: number;
}

export default function OnboardingTrendPage() {
  const { user } = useAuth();
  const [fy, setFy] = useState("");
  const { data } = useQuery<OnboardingResponse>({
    queryKey: ["onboarding-trend", fy],
    queryFn: async () => (await api.get("/reports/onboarding-trend", { params: fy ? { fiscal_year: fy } : {} })).data,
    enabled: user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN",
  });

  if (user?.role === "FIG_PRESIDENT") return <div>Not available for your role.</div>;
  const months = data?.months || [];

  return (
    <div>
      <div className="mb-5"><h1 className="font-heading text-3xl font-extrabold">Farmer &amp; FIG onboarding trend</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          New registrations per month — defaults to the trailing 12 months if no fiscal year is selected.
        </p></div>

      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="label-tag">Fiscal year</label>
          <select className="input max-w-xs" value={fy} onChange={(e) => setFy(e.target.value)}>
            <option value="">Trailing 12 months</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <ExportButtons report="onboarding-trend" params={fy ? { fiscal_year: fy } : {}} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="stat-card"><span className="label-tag">Total Farmers (to date)</span>
          <div className="font-heading text-2xl font-extrabold mt-2">{(data?.farmers_total_to_date ?? 0).toLocaleString()}</div></div>
        <div className="stat-card"><span className="label-tag">Total FIGs (to date)</span>
          <div className="font-heading text-2xl font-extrabold mt-2">{(data?.figs_total_to_date ?? 0).toLocaleString()}</div></div>
      </div>

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th>Month</th><th>Farmers Registered</th><th>FIGs Formed</th></tr></thead>
          <tbody>
            {months.map((m, i) => (
              <tr key={m}>
                <td className="font-semibold">{m}</td>
                <td>{data?.farmers_monthly[i] ?? 0}</td>
                <td>{data?.figs_monthly[i] ?? 0}</td>
              </tr>
            ))}
            {months.length === 0 && <tr><td colSpan={3} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data yet</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
