"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions, currentFY } from "@/lib/fiscal";
import { Users, UsersThree, ChartLineUp, Calendar } from "@phosphor-icons/react";
import type { DashboardStats } from "@/lib/types";
import { OnboardingSummary } from "./OnboardingSummary";
import { ProductionTiles, StockTiles, InputTiles } from "./ProductTiles";

const SilkTypeBarChart = dynamic(() => import("./charts").then((m) => m.SilkTypeBarChart), { ssr: false });
const YieldTrendChart = dynamic(() => import("./charts").then((m) => m.YieldTrendChart), { ssr: false });
const MultiSeriesTrendChart = dynamic(() => import("./charts").then((m) => m.MultiSeriesTrendChart), { ssr: false });

function Stat({ icon: Icon, label, value, tone = "primary", href }: { icon: React.ElementType; label: string; value: React.ReactNode; tone?: string; href?: string }) {
  const content = (
    <div className="stat-card">
      <div className="flex items-center justify-between">
        <span className="label-tag">{label}</span>
        <Icon size={22} weight="duotone" color={tone === "warning" ? "#C78622" : "#2D5134"} />
      </div>
      <div className="font-heading text-3xl font-extrabold mt-3">{value ?? "—"}</div>
    </div>
  );
  return href ? <Link href={href} className="block hover:shadow-sm transition">{content}</Link> : content;
}

function YoyTrendCard() {
  const defaultFys = useMemo(() => [currentFY(), fyOptions(2)[1]].filter(Boolean), []);
  const [selected, setSelected] = useState<string[]>(defaultFys);
  const options = fyOptions();

  const { data } = useQuery({
    queryKey: ["yoy-trend", selected],
    queryFn: async () => {
      const params = new URLSearchParams();
      selected.forEach((fy) => params.append("fiscal_years", fy));
      return (await api.get(`/reports/yoy-trend?${params.toString()}`)).data;
    },
    enabled: selected.length > 0,
  });

  const chartData = useMemo(() => {
    if (!data?.labels) return [];
    return data.labels.map((label: string, i: number) => {
      const row: Record<string, string | number> = { label };
      data.series.forEach((s: { fiscal_year: string; data: { actual: number }[] }) => {
        row[s.fiscal_year] = s.data[i]?.actual ?? 0;
      });
      return row;
    });
  }, [data]);

  function toggleFy(fy: string) {
    setSelected((prev) => (prev.includes(fy) ? prev.filter((f) => f !== fy) : prev.length < 4 ? [...prev, fy] : prev));
  }

  return (
    <div className="mt-6 card p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h3 className="font-heading text-lg font-bold">Year-on-year production trend</h3>
        <div className="flex items-center gap-1 flex-wrap">
          {options.map((fy) => (
            <button key={fy} onClick={() => toggleFy(fy)}
                    className={selected.includes(fy) ? "btn-primary btn-sm" : "btn-secondary btn-sm"}>
              {fy}
            </button>
          ))}
        </div>
      </div>
      <div style={{ height: 260 }}>
        <MultiSeriesTrendChart data={chartData} seriesKeys={selected} />
      </div>
      {chartData.length === 0 && (
        <div className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>Select at least one fiscal year.</div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: stats = {} as DashboardStats } = useQuery({ queryKey: ["dashboard"], queryFn: async () => (await api.get("/reports/dashboard")).data });
  const { data: trend = [] } = useQuery({ queryKey: ["monthly-trend"], queryFn: async () => (await api.get("/reports/monthly-trend")).data });
  const { data: silkTypeDist = [] } = useQuery({
    queryKey: ["silk-type-dist"], queryFn: async () => (await api.get("/reports/silk-type-distribution")).data,
    enabled: user?.role === "STATE_ADMIN",
  });
  const { data: heatmap = [] } = useQuery({
    queryKey: ["district-heatmap"], queryFn: async () => (await api.get("/reports/district-heatmap")).data,
    enabled: user?.role === "STATE_ADMIN",
  });

  if (!user) return null;
  const s: any = stats;

  return (
    <div>
      <div className="flex items-end justify-between mb-6">
        <div>
          <div className="label-tag">Welcome back</div>
          <h1 className="font-heading text-3xl font-extrabold mt-1">{user.name || user.mobile_no}</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {user.role === "STATE_ADMIN" && "State-wide sericulture overview"}
            {user.role === "DISTRICT_ADMIN" && "Your district at a glance"}
            {user.role === "FIG_PRESIDENT" && "Your FIG operations"}
          </p>
        </div>
        {user.role === "FIG_PRESIDENT" && (
          <Link href="/submission" className="btn-primary inline-flex items-center gap-2" data-testid="cta-submission">
            <Calendar size={16} weight="bold" /> Submit Monthly Meeting Data
          </Link>
        )}
      </div>

      {user.role === "STATE_ADMIN" && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Stat icon={Users} label="Total Farmers" value={s.farmers} href="/farmers?autoSearch=1" />
            <Stat icon={UsersThree} label="Active FIGs" value={s.figs} href="/figs?autoSearch=1" />
          </div>

          <OnboardingSummary />
          <ProductionTiles />
          <StockTiles />
          <InputTiles />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card p-6">
              <h3 className="font-heading text-lg font-bold mb-4">Monthly submission ({s.current_month})</h3>
              <div className="flex gap-3">
                <div className="flex-1 rounded p-4 text-center" style={{ background: "#E5EFE7" }}>
                  <div className="font-heading text-3xl font-extrabold" style={{ color: "var(--success)" }}>{s.monthly_submitted_count ?? 0}</div>
                  <div className="label-tag mt-1">Submitted</div>
                </div>
                <div className="flex-1 rounded p-4 text-center" style={{ background: "#FBEFD6" }}>
                  <div className="font-heading text-3xl font-extrabold" style={{ color: "var(--warning)" }}>{Math.max((s.figs || 0) - (s.monthly_submitted_count || 0), 0)}</div>
                  <div className="label-tag mt-1">Pending</div>
                </div>
              </div>
            </div>
            <div className="card p-6">
              <h3 className="font-heading text-lg font-bold mb-4">Silk type-wise FIG distribution</h3>
              <div style={{ height: 200 }}>
                <SilkTypeBarChart data={silkTypeDist} />
              </div>
            </div>
          </div>

          <div className="card p-6 mb-6">
            <h3 className="font-heading text-lg font-bold mb-4">District submission heatmap ({s.current_month})</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {heatmap.map((d: any) => {
                const color = d.pct >= 80 ? "var(--success)" : d.pct >= 50 ? "var(--warning)" : "var(--error)";
                const bg = d.pct >= 80 ? "#E5EFE7" : d.pct >= 50 ? "#FBEFD6" : "#F5DDDB";
                return (
                  <div key={d.district_id} className="rounded px-3 py-2 flex justify-between items-center" style={{ background: bg }}>
                    <div>
                      <div className="text-sm font-semibold">{d.district_name}</div>
                      <div className="text-xs" style={{ color: "var(--text-muted)" }}>{d.submitted} / {d.total} FIGs</div>
                    </div>
                    <div className="font-heading font-extrabold" style={{ color }}>{d.pct}%</div>
                  </div>
                );
              })}
              {heatmap.length === 0 && <div className="col-span-3 text-center py-4 text-sm" style={{ color: "var(--text-muted)" }}>No FIGs registered yet</div>}
            </div>
          </div>
        </>
      )}

      {user.role === "DISTRICT_ADMIN" && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Stat icon={Users} label="Farmers in District" value={s.farmers} href="/farmers?autoSearch=1" />
            <Stat icon={UsersThree} label="Active FIGs" value={s.figs} href="/figs?autoSearch=1" />
          </div>

          <OnboardingSummary />
          <ProductionTiles />
          <StockTiles />
          <InputTiles />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card p-6">
              <h3 className="font-heading text-lg font-bold mb-4">Monthly submission ({s.current_month})</h3>
              <div className="flex gap-3">
                <div className="flex-1 rounded p-4 text-center" style={{ background: "#E5EFE7" }}>
                  <div className="font-heading text-3xl font-extrabold" style={{ color: "var(--success)" }}>{s.monthly_submitted_count ?? 0}</div>
                  <div className="label-tag mt-1">Submitted</div>
                </div>
                <div className="flex-1 rounded p-4 text-center" style={{ background: "#FBEFD6" }}>
                  <div className="font-heading text-3xl font-extrabold" style={{ color: "var(--warning)" }}>{Math.max((s.figs || 0) - (s.monthly_submitted_count || 0), 0)}</div>
                  <div className="label-tag mt-1">Pending</div>
                </div>
              </div>
            </div>
            <div className="card p-6">
              <h3 className="font-heading text-lg font-bold mb-4">Action queue</h3>
              <div className="space-y-3">
                <Link href="/lands" className="flex items-center justify-between p-3 rounded border" style={{ borderColor: "var(--border)" }}>
                  <span className="text-sm font-semibold">GPS Verification Pending</span>
                  <span className={`badge ${s.lands_pending > 0 ? "badge-error" : "badge-muted"}`}>{s.lands_pending ?? 0}</span>
                </Link>
                <Link href="/trainings" className="flex items-center justify-between p-3 rounded border" style={{ borderColor: "var(--border)" }}>
                  <span className="text-sm font-semibold">Training Requests</span>
                  <span className={`badge ${s.pending_trainings > 0 ? "badge-warning" : "badge-muted"}`}>{s.pending_trainings ?? 0} Pending</span>
                </Link>
              </div>
            </div>
          </div>
        </>
      )}
      {user.role === "FIG_PRESIDENT" && (
        <>
          <div className="card p-5 mb-4" style={{ background: "linear-gradient(135deg, #2D5134 0%, #213D26 100%)", color: "#fff" }}>
            <div className="label-tag" style={{ color: "rgba(255,255,255,0.7)" }}>Your FIG</div>
            <div className="font-heading text-2xl font-extrabold mt-1">{s.fig_name || "FIG President"}</div>
            <div className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.85)" }}>{s.fig_code ?? "—"} · {s.district_name ?? "—"}</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <Stat icon={Users} label="Active Members" value={s.members} />
            <Stat icon={Calendar} label="Meetings Logged" value={s.meetings} />
            <div className="stat-card">
              <span className="label-tag">This month ({s.current_month})</span>
              <div className="font-heading text-xl font-bold mt-3">
                {s.submitted_this_month
                  ? <span className="badge badge-success">Submitted</span>
                  : <span className="badge badge-warning">Not yet submitted</span>}
              </div>
              {!s.submitted_this_month && (
                <Link href="/submission" data-testid="cta-start-submission" className="btn-primary mt-3 inline-flex items-center gap-2 text-sm">
                  <Calendar size={14} weight="bold" /> Start submission
                </Link>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
            <Link href="/submission" className="card p-4 hover:shadow-sm transition">
              <div className="label-tag">Quick action</div>
              <div className="font-semibold text-sm mt-2">Submit Monthly Meeting Data</div>
            </Link>
            <Link href="/lands" className="card p-4 hover:shadow-sm transition">
              <div className="label-tag">Land</div>
              <div className="font-semibold text-sm mt-2">Submit GPS Coordinates</div>
            </Link>
            <Link href="/figs" className="card p-4 hover:shadow-sm transition">
              <div className="label-tag">Team</div>
              <div className="font-semibold text-sm mt-2">View Members</div>
            </Link>
          </div>

          <ProductionTiles />
          <StockTiles />
          <InputTiles />
        </>
      )}

      <div className="mt-8 card p-6">
        <div className="flex items-center gap-2 mb-4">
          <ChartLineUp size={20} weight="duotone" color="#2D5134" />
          <h3 className="font-heading text-lg font-bold">Planned vs Actual yield · trend</h3>
        </div>
        <div style={{ height: 280 }}>
          <YieldTrendChart data={trend} />
        </div>
        {trend.length === 0 && (
          <div className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>
            No yield data yet.
          </div>
        )}
      </div>

      <YoyTrendCard />
    </div>
  );
}
