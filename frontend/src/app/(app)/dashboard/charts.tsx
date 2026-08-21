"use client";
import {
  Area, AreaChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

/**
 * Chart colours are VALIDATED, not chosen by eye — see the dataviz palette checker.
 * Re-run it before changing any of these:
 *   node scripts/validate_palette.js "#009E73,#E69F00,#D55E00,#0072B2" --mode light --pairs all
 *
 * Two things that are easy to get wrong here:
 *  - The brand green #2D5134 is NOT a usable data colour (chroma 0.064 — it reads grey).
 *    Brand chrome and chart marks are different palettes.
 *  - Muga gold carries a contrast WARN (2.19:1), so anything drawn in it must also show a
 *    direct value label. That obligation is discharged by the `labelled` bars below.
 */
export const SILK_COLORS: Record<string, string> = {
  Mulberry: "#009E73",
  Muga: "#E69F00",
  Eri: "#D55E00",
  Tasar: "#0072B2",
};
const SILK_FALLBACK = "#5C635B";
export const silkColor = (name?: string | null) => (name && SILK_COLORS[name]) || SILK_FALLBACK;

/** Non-silk two-series comparisons (Farmers vs FIGs). Validated: worst ΔE 24.4 normal / 9.6 protan. */
export const SERIES_A = "#0072B2";
export const SERIES_B = "#CC79A7";

const INK = "#1A1D1A";
const INK_MUTED = "#5C635B";
const GRID = "#E6E4DF";
const AXIS = { stroke: GRID, fontSize: 12, tickLine: false, axisLine: { stroke: GRID } };

/** Shared tooltip — text always wears ink colours; the swatch alone carries identity. */
function ChartTooltip({ active, payload, label, unit }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="card" style={{ padding: "8px 10px", boxShadow: "var(--elev-2)" }}>
      {label != null && (
        <div className="text-xs font-semibold mb-1" style={{ color: INK }}>{label}</div>
      )}
      {payload.map((p: any) => (
        <div key={p.dataKey ?? p.name} className="flex items-center gap-2 text-xs" style={{ color: INK_MUTED }}>
          <span style={{ width: 9, height: 9, borderRadius: 2, background: p.color || p.fill, flexShrink: 0 }} />
          <span>{p.name}</span>
          <span className="font-semibold ml-auto pl-3" style={{ color: INK }}>
            {typeof p.value === "number" ? p.value.toLocaleString("en-IN") : p.value}{unit ? ` ${unit}` : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Farmers + FIGs onboarding over 12 months. Two series, so a legend is mandatory. */
export function OnboardingTrendChart({ data }: { data: { label: string; Farmers: number; FIGs: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="fillFarmers" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={SERIES_A} stopOpacity={0.22} />
            <stop offset="100%" stopColor={SERIES_A} stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="fillFigs" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={SERIES_B} stopOpacity={0.22} />
            <stop offset="100%" stopColor={SERIES_B} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" {...AXIS} tick={{ fill: INK_MUTED, fontSize: 11 }} />
        <YAxis {...AXIS} tick={{ fill: INK_MUTED, fontSize: 11 }} allowDecimals={false} width={38} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: INK_MUTED, strokeDasharray: "3 3" }} />
        <Legend wrapperStyle={{ fontSize: 12, color: INK_MUTED }} iconType="circle" iconSize={8} />
        <Area type="monotone" dataKey="Farmers" stroke={SERIES_A} strokeWidth={2}
              fill="url(#fillFarmers)" dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "#fff" }} />
        <Area type="monotone" dataKey="FIGs" stroke={SERIES_B} strokeWidth={2}
              fill="url(#fillFigs)" dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "#fff" }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/**
 * Horizontal bars with the value printed at the end of each bar. The direct label is not
 * decoration — it is what makes the low-contrast Muga gold legible, so do not remove it.
 */
export function LabelledBarChart({ data, unit, height = 26 }: {
  data: { name: string; value: number; color: string; sub?: string }[];
  unit?: string; height?: number;
}) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="space-y-2">
      {data.map((d) => (
        <div key={d.name} className="flex items-center gap-3" title={`${d.name}: ${d.value.toLocaleString("en-IN")}${unit ? " " + unit : ""}`}>
          {/* Narrower on phones so the bar keeps more than half the row. */}
          <div className="text-xs truncate w-[104px] sm:w-[150px] shrink-0" style={{ color: INK }}>
            {d.name}
            {d.sub && <span className="ml-1" style={{ color: INK_MUTED }}>· {d.sub}</span>}
          </div>
          <div className="flex-1 rounded-full" style={{ background: "var(--bg)", height }}>
            <div
              className="rounded-full flex items-center justify-end pr-2"
              style={{
                width: `${Math.max((d.value / max) * 100, d.value > 0 ? 6 : 0)}%`,
                height, background: d.color, transition: "width 0.4s ease",
              }}
            >
              {d.value > 0 && (
                <span className="text-xs font-bold" style={{ color: "#fff" }}>
                  {d.value.toLocaleString("en-IN")}
                </span>
              )}
            </div>
          </div>
          {d.value === 0 && <span className="text-xs" style={{ color: INK_MUTED, width: 24 }}>0</span>}
        </div>
      ))}
      {data.length === 0 && (
        <div className="text-sm text-center py-6" style={{ color: INK_MUTED }}>No data yet</div>
      )}
    </div>
  );
}

/** Kept: still used by the Farmers and FIGs onboarding-trend cards. */
export function MultiSeriesTrendChart({ data, seriesKeys }: { data: Record<string, string | number>[]; seriesKeys: string[] }) {
  const colors = [SERIES_A, SERIES_B, "#009E73", "#E69F00", "#D55E00", "#5C635B"];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey="label" {...AXIS} tick={{ fill: INK_MUTED, fontSize: 11 }} />
        <YAxis {...AXIS} tick={{ fill: INK_MUTED, fontSize: 11 }} allowDecimals={false} width={38} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: INK_MUTED, strokeDasharray: "3 3" }} />
        {seriesKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />}
        {seriesKeys.map((k, i) => (
          <Line key={k} type="monotone" dataKey={k} stroke={colors[i % colors.length]} strokeWidth={2}
                dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "#fff" }} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
