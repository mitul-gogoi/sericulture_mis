"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { ChartLineUp, MapTrifold, Plant, UsersThree } from "@phosphor-icons/react";
import { LabelledBarChart, OnboardingTrendChart, silkColor } from "./charts";
import { AssamMap, type DistrictStat } from "./AssamMap";
import type { ActivityOnboardingResponse } from "@/lib/types";

const currentMonth = () => new Date().toISOString().slice(0, 7);

interface ProductSummaryRow {
  product_id: string; product_name: string; unit_of_measure: string; is_byproduct: boolean;
  planned: number; actual: number; byproduct_qty: number;
  silk_types?: { id: string; name: string }[];
}

function CardHead({ icon: Icon, title, note }: { icon: React.ElementType; title: string; note?: string }) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2">
        <Icon size={20} weight="duotone" color="#2D5134" />
        <h3 className="font-heading text-lg font-bold">{title}</h3>
      </div>
      {note && <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{note}</p>}
    </div>
  );
}

/** Farmers and FIGs added per month over the trailing year. */
export function OnboardingTrendCard() {
  const { data } = useQuery<{ months: string[]; farmers_monthly: number[]; figs_monthly: number[] }>({
    queryKey: ["onboarding-trend-dashboard"],
    queryFn: async () => (await api.get("/reports/onboarding-trend")).data,
  });
  const rows = (data?.months ?? []).map((m, i) => ({
    label: m, Farmers: data?.farmers_monthly[i] ?? 0, FIGs: data?.figs_monthly[i] ?? 0,
  }));
  const hasData = rows.some((r) => r.Farmers > 0 || r.FIGs > 0);
  return (
    <div className="card p-6 mb-6">
      <CardHead icon={ChartLineUp} title="Onboarding trend" note="Farmers and FIGs registered per month, trailing 12 months" />
      <div style={{ height: 260 }}>
        {hasData ? <OnboardingTrendChart data={rows} />
                 : <div className="h-full flex items-center justify-center text-sm" style={{ color: "var(--text-muted)" }}>No onboarding recorded yet</div>}
      </div>
    </div>
  );
}

/** Replaces the 35-rectangle grid. Hover carries the exact figures the grid used to print. */
export function DistrictMapCard({ month }: { month?: string }) {
  const { data: heatmap = [] } = useQuery<DistrictStat[]>({
    queryKey: ["district-heatmap"],
    queryFn: async () => (await api.get("/reports/district-heatmap")).data,
  });
  return (
    <div className="card p-6 mb-6">
      <CardHead icon={MapTrifold} title={`District submission rate${month ? ` (${month})` : ""}`}
                note="Share of each district's FIGs that have submitted this month — hover a district for exact figures" />
      {heatmap.length > 0
        ? <AssamMap stats={heatmap} />
        : <div className="text-sm text-center py-10" style={{ color: "var(--text-muted)" }}>No FIGs registered yet</div>}
    </div>
  );
}

/** Production by product, coloured by the product's silk type. */
export function ProductionChartCard() {
  const month = currentMonth();
  // Same query key as ProductionTiles, so React Query serves both from one request.
  const { data } = useQuery<{ rows: ProductSummaryRow[] }>({
    queryKey: ["product-summary", month],
    queryFn: async () => (await api.get("/reports/product-summary", { params: { month } })).data,
  });
  const rows = (data?.rows ?? [])
    .map((r) => ({
      name: r.product_name,
      value: Math.round((r.is_byproduct ? r.byproduct_qty : r.actual) * 100) / 100,
      color: silkColor(r.silk_types?.[0]?.name),
      sub: r.unit_of_measure,
    }))
    .filter((r) => r.value > 0)
    .sort((a, b) => b.value - a.value);

  return (
    <div className="card p-6 mb-6">
      <CardHead icon={Plant} title="Production this month" note="Coloured by silk type · value shown on each bar" />
      <LabelledBarChart data={rows} />
      <SilkLegend />
    </div>
  );
}

/** Where the registered workforce sits across the value chain. */
export function ActivityMixCard() {
  const { data } = useQuery<ActivityOnboardingResponse>({
    queryKey: ["activity-onboarding", {}],
    queryFn: async () => (await api.get("/reports/activity-onboarding")).data,
  });
  const rows = (data?.items ?? [])
    .filter((i) => i.farmers > 0)
    .map((i) => ({ name: i.activity_name, value: i.farmers, color: silkColor(i.silk_type_name), sub: i.silk_type_name }));

  return (
    <div className="card p-6 mb-6">
      <CardHead icon={UsersThree} title="Farmers by activity"
                note="A farmer registered for several activities is counted under each, so this totals more than the headcount" />
      <LabelledBarChart data={rows} />
      <SilkLegend />
    </div>
  );
}

/** Identity is never colour-alone — the legend is always present alongside silk-coloured marks. */
function SilkLegend() {
  return (
    <div className="flex items-center gap-4 mt-4 flex-wrap">
      {["Mulberry", "Muga", "Eri", "Tasar"].map((n) => (
        <span key={n} className="inline-flex items-center gap-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
          <span style={{ width: 10, height: 10, borderRadius: 3, background: silkColor(n), display: "inline-block" }} />
          {n}
        </span>
      ))}
    </div>
  );
}

/** Compact compliance meter — replaces the two oversized number boxes. */
export function SubmissionMeter({ submitted, total, month }: { submitted: number; total: number; month?: string }) {
  const pct = total > 0 ? Math.round((submitted / total) * 100) : 0;
  const pending = Math.max(total - submitted, 0);
  return (
    <div className="card p-6 mb-6">
      <CardHead icon={ChartLineUp} title={`Monthly submission${month ? ` (${month})` : ""}`} />
      <div className="flex items-center gap-6 flex-wrap">
        <div className="font-heading text-4xl font-extrabold" style={{ color: "var(--primary)" }}>{pct}%</div>
        <div className="flex-1 min-w-[180px]">
          <div className="rounded-full overflow-hidden" style={{ background: "var(--bg)", height: 14 }}>
            <div style={{ width: `${pct}%`, height: "100%", background: "var(--success)", transition: "width 0.4s ease" }} />
          </div>
          <div className="flex gap-4 mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
            <span><strong style={{ color: "var(--success)" }}>{submitted}</strong> submitted</span>
            <span><strong style={{ color: "var(--warning)" }}>{pending}</strong> pending</span>
            <span>{total} FIGs total</span>
          </div>
        </div>
      </div>
    </div>
  );
}
