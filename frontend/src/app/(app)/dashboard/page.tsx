"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Users, UsersThree, Calendar, MapTrifold, Wrench } from "@phosphor-icons/react";
import type { DashboardStats } from "@/lib/types";
import { OnboardingSummary } from "./OnboardingSummary";
import { ProductionTiles, StockTiles } from "./ProductTiles";

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

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: stats = {} as DashboardStats } = useQuery({
    queryKey: ["dashboard"], queryFn: async () => (await api.get("/reports/dashboard")).data,
    enabled: user?.role !== "FARMER",
  });
  const { data: heatmap = [] } = useQuery({
    queryKey: ["district-heatmap"], queryFn: async () => (await api.get("/reports/district-heatmap")).data,
    enabled: user?.role === "STATE_ADMIN",
  });
  const { data: farmerSummary = {} as any } = useQuery({
    queryKey: ["farmer-summary"], queryFn: async () => (await api.get("/farmers/me/summary")).data,
    enabled: user?.role === "FARMER",
  });

  if (!user) return null;
  const s: any = user.role === "FARMER" ? farmerSummary : stats;

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
            {user.role === "FARMER" && "Your production and submission overview"}
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
          <div className="card p-6 mb-6">
            <h3 className="font-heading text-lg font-bold mb-4">Action queue</h3>
            <div className="space-y-3">
              <Link href="/meetings?focus=resubmission-requests" className="flex items-center justify-between p-3 rounded border" style={{ borderColor: "var(--border)" }}>
                <span className="text-sm font-semibold">Pending Resubmission Requests</span>
                <span className={`badge ${s.pending_corrections > 0 ? "badge-error" : "badge-muted"}`}>{s.pending_corrections ?? 0}</span>
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Stat icon={Users} label="Total Farmers" value={s.farmers} href="/farmers?autoSearch=1" />
            <Stat icon={UsersThree} label="Active FIGs" value={s.figs} href="/figs?autoSearch=1" />
          </div>

          <OnboardingSummary />
          <ProductionTiles />
          <StockTiles />

          <div className="card p-6 mb-6">
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
          <div className="card p-6 mb-6">
            <h3 className="font-heading text-lg font-bold mb-4">Action queue</h3>
            <div className="space-y-3">
              <Link href="/lands?status=Pending" className="flex items-center justify-between p-3 rounded border" style={{ borderColor: "var(--border)" }}>
                <span className="text-sm font-semibold">GPS Verification Pending (Land)</span>
                <span className={`badge ${s.lands_pending > 0 ? "badge-error" : "badge-muted"}`}>{s.lands_pending ?? 0}</span>
              </Link>
              <Link href="/assets?gps_status=Pending" className="flex items-center justify-between p-3 rounded border" style={{ borderColor: "var(--border)" }}>
                <span className="text-sm font-semibold">GPS Verification Pending (Assets)</span>
                <span className={`badge ${s.assets_gps_pending > 0 ? "badge-error" : "badge-muted"}`}>{s.assets_gps_pending ?? 0}</span>
              </Link>
              <Link href="/trainings?status=Pending" className="flex items-center justify-between p-3 rounded border" style={{ borderColor: "var(--border)" }}>
                <span className="text-sm font-semibold">Training Requests</span>
                <span className={`badge ${s.pending_trainings > 0 ? "badge-warning" : "badge-muted"}`}>{s.pending_trainings ?? 0} Pending</span>
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <Stat icon={Users} label="Farmers in District" value={s.farmers} href="/farmers?autoSearch=1" />
            <Stat icon={UsersThree} label="Active FIGs" value={s.figs} href="/figs?autoSearch=1" />
          </div>

          <OnboardingSummary />
          <ProductionTiles />
          <StockTiles />

          <div className="card p-6 mb-6">
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
        </>
      )}
      {user.role === "FIG_PRESIDENT" && (
        <>
          <div className="rounded-lg p-4 mb-6" style={{ background: "#EAF3EC" }}>
            <h3 className="font-heading text-sm font-bold mb-3">Quick Actions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <Link href="/submission" className="card p-4 hover:shadow-sm transition">
                <div className="label-tag">Quick action</div>
                <div className="font-semibold text-sm mt-2">Submit Monthly Meeting Data</div>
              </Link>
              {(s.lands_needing_gps ?? 0) > 0 && (
                <Link href="/lands" className="card p-4 hover:shadow-sm transition">
                  <div className="label-tag">Land</div>
                  <div className="font-semibold text-sm mt-2">Submit GPS Coordinates</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{s.lands_needing_gps} parcel(s) need GPS</div>
                </Link>
              )}
              {(s.assets_needing_gps ?? 0) > 0 && (
                <Link href="/assets" className="card p-4 hover:shadow-sm transition">
                  <div className="label-tag">Assets</div>
                  <div className="font-semibold text-sm mt-2">Capture Asset GPS</div>
                  <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{s.assets_needing_gps} asset(s) need GPS</div>
                </Link>
              )}
            </div>
          </div>

          <div className="card p-5 mb-4" style={{ background: "linear-gradient(135deg, #2D5134 0%, #213D26 100%)", color: "#fff" }}>
            <div className="label-tag" style={{ color: "rgba(255,255,255,0.7)" }}>Your FIG</div>
            <div className="font-heading text-2xl font-extrabold mt-1">{s.fig_name || "FIG President"}</div>
            <div className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.85)" }}>{s.fig_code ?? "—"} · {s.district_name ?? "—"}</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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

          <ProductionTiles />
          <StockTiles />
        </>
      )}
      {user.role === "FARMER" && (
        <>
          <div className="card p-5 mb-4" style={{ background: "linear-gradient(135deg, #2D5134 0%, #213D26 100%)", color: "#fff" }}>
            <div className="label-tag" style={{ color: "rgba(255,255,255,0.7)" }}>Your FIG</div>
            <div className="font-heading text-2xl font-extrabold mt-1">{s.fig_name || "Not yet assigned to a FIG"}</div>
            {s.fig_name && <div className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.85)" }}>{s.fig_code ?? "—"}</div>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Stat icon={MapTrifold} label="Land Parcels" value={s.land_count} href="/lands" />
            <Stat icon={Wrench} label="Assets" value={s.asset_count} href="/assets" />
            <div className="stat-card">
              <span className="label-tag">This month ({s.current_month})</span>
              <div className="font-heading text-xl font-bold mt-3">
                {s.submitted_this_month
                  ? <span className="badge badge-success">Submitted</span>
                  : s.fig_id && s.has_draft_this_month
                    ? <span className="badge badge-warning">Draft saved</span>
                    : <span className="badge badge-warning">Not yet submitted</span>}
              </div>
              {!s.submitted_this_month && (
                <Link href={s.fig_id ? "/farmer/draft" : "/farmer/submit"} className="btn-primary mt-3 inline-flex items-center gap-2 text-sm">
                  <Calendar size={14} weight="bold" /> {s.fig_id ? (s.has_draft_this_month ? "Edit draft" : "Start draft") : "Submit this month"}
                </Link>
              )}
            </div>
          </div>

          <ProductionTiles />
          <StockTiles />

          <div className="card p-6 mb-6">
            <Link href={s.fig_id ? "/farmer/meetings" : "/farmer/submissions"} className="btn-secondary inline-flex items-center gap-2">
              <Calendar size={16} weight="bold" /> View Submission History
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
