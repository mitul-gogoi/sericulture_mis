"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface OnboardingResponse {
  months: string[]; farmers_monthly: number[]; farmers_total_to_date: number;
  figs_monthly: number[]; figs_total_to_date: number;
}
interface BreakdownRow { id: string; name: string; count: number }

export function OnboardingSummary() {
  const { user } = useAuth();
  const isDA = user?.role === "DISTRICT_ADMIN";
  const breakdownLevel = isDA ? "sericulture_circle" : "district";

  const { data: onboarding } = useQuery<OnboardingResponse>({
    queryKey: ["onboarding-trend"], queryFn: async () => (await api.get("/reports/onboarding-trend")).data,
  });
  const { data: farmersBreakdown } = useQuery<{ rows: BreakdownRow[] }>({
    queryKey: ["analytics-farmers-breakdown", breakdownLevel],
    queryFn: async () => (await api.get("/reports/analytics/farmers", { params: { level: breakdownLevel } })).data,
  });
  const { data: figsBreakdown } = useQuery<{ rows: BreakdownRow[] }>({
    queryKey: ["analytics-figs-breakdown", breakdownLevel],
    queryFn: async () => (await api.get("/reports/analytics/figs", { params: { level: breakdownLevel } })).data,
  });

  const farmersThisMonth = onboarding?.farmers_monthly?.[onboarding.farmers_monthly.length - 1] ?? 0;
  const figsThisMonth = onboarding?.figs_monthly?.[onboarding.figs_monthly.length - 1] ?? 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading text-lg font-bold">Farmer onboarding</h3>
          <Link href="/farmers?focus=onboarding-trend" className="text-xs font-semibold" style={{ color: "var(--primary)" }}>View trend →</Link>
        </div>
        <div className="flex items-baseline gap-3 mb-3">
          <div className="font-heading text-3xl font-extrabold">{(onboarding?.farmers_total_to_date ?? 0).toLocaleString()}</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>total · +{farmersThisMonth} this month</div>
        </div>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {(farmersBreakdown?.rows || []).map((r) => (
            <div key={r.id}
                 className="flex items-center justify-between text-sm px-2 py-1 rounded" style={{ background: "var(--bg)" }}>
              <span>{r.name}</span><span className="font-semibold">{r.count}</span>
            </div>
          ))}
          {(!farmersBreakdown || farmersBreakdown.rows.length === 0) && (
            <div className="text-xs text-center py-2" style={{ color: "var(--text-muted)" }}>No farmers registered yet</div>
          )}
        </div>
      </div>

      <div className="card p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading text-lg font-bold">FIG onboarding</h3>
          <Link href="/figs?focus=onboarding-trend" className="text-xs font-semibold" style={{ color: "var(--primary)" }}>View trend →</Link>
        </div>
        <div className="flex items-baseline gap-3 mb-3">
          <div className="font-heading text-3xl font-extrabold">{(onboarding?.figs_total_to_date ?? 0).toLocaleString()}</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>total · +{figsThisMonth} this month</div>
        </div>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {(figsBreakdown?.rows || []).map((r) => (
            <div key={r.id}
                 className="flex items-center justify-between text-sm px-2 py-1 rounded" style={{ background: "var(--bg)" }}>
              <span>{r.name}</span><span className="font-semibold">{r.count}</span>
            </div>
          ))}
          {(!figsBreakdown || figsBreakdown.rows.length === 0) && (
            <div className="text-xs text-center py-2" style={{ color: "var(--text-muted)" }}>No FIGs formed yet</div>
          )}
        </div>
      </div>
    </div>
  );
}
