"use client";
import { Fragment } from "react";
import { Info } from "@phosphor-icons/react";
import type { YieldMatrixItem, YieldMatrixResponse } from "@/lib/types";

function fmt(n: number): string {
  return Number.isFinite(n) ? (Math.round(n * 100) / 100).toString() : "0";
}

// Columns rendered *before* the entity column — only "meeting" uses this today, since Meeting
// ID/Month identify the row ahead of the Farmer name it's otherwise keyed by.
const LEADING_COLUMNS: Partial<Record<YieldMatrixResponse["level"], { key: keyof YieldMatrixItem; label: string }[]>> = {
  meeting: [
    { key: "meeting_id", label: "Meeting ID" },
    { key: "meeting_month", label: "Meeting Month" },
  ],
};

// Breadcrumb/code columns shown immediately after the entity column. Code columns sit right
// next to the name they identify (matching this app's existing Code-then-Name convention, e.g.
// figs/page.tsx's table); District/Sericulture Circle/FIG stay broad-to-narrow after that.
const CONTEXT_COLUMNS: Record<YieldMatrixResponse["level"], { key: keyof YieldMatrixItem; label: string }[]> = {
  state: [],
  district: [],
  sericulture_circle: [{ key: "district_name", label: "District" }],
  fig: [
    { key: "fig_code", label: "FIG Code" },
    { key: "district_name", label: "District" },
    { key: "seri_circle_name", label: "Sericulture Circle" },
  ],
  farmer: [
    { key: "farmer_code", label: "Farmer Code" },
    { key: "district_name", label: "District" },
    { key: "seri_circle_name", label: "Sericulture Circle" },
    { key: "fig_name", label: "FIG" },
    { key: "fig_code", label: "FIG Code" },
  ],
  meeting: [
    { key: "farmer_code", label: "Farmer Code" },
    { key: "district_name", label: "District" },
    { key: "seri_circle_name", label: "Sericulture Circle" },
    { key: "fig_name", label: "FIG" },
    { key: "fig_code", label: "FIG Code" },
  ],
};

function fmtOrDash(n: number | null): string {
  return n === null ? "—" : fmt(n);
}

// On-screen is deliberately a curated subset of what's available — the Excel export (see
// reports.py's yield-matrix export branch) always carries every possible column so power users
// can pivot/filter offline; the screen only shows what's "interesting to check at a glance."
// INPUT: Total only (per-source breakdown is Excel-only). OUTPUT: Planned/Actual/Expected/Loss
// Reason/Total Earned (Next Plan/Sold Qty/Sold Rate are Excel-only).
function outputColSpan(p: YieldMatrixResponse["output_products"][number]): number {
  return 4 + p.expected_ranges.length;
}

function inputColSpan(): number {
  return 1;
}

export function YieldMatrixTable({ data, entityLabel }: { data: YieldMatrixResponse; entityLabel: string }) {
  const { input_products, output_products, stock_products, items } = data;
  const leadingColumns = LEADING_COLUMNS[data.level] ?? [];
  const contextColumns = CONTEXT_COLUMNS[data.level];
  const isMeeting = data.level === "meeting";
  const stockCaption = isMeeting
    ? "Stock (at submission) — the historical balance recorded on this exact submission, not a live snapshot"
    : "Stock is a current snapshot of declared balances — not filtered by the selected period";

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="seri-table">
          <thead>
            <tr>
              {leadingColumns.map((c) => (
                <th key={c.key} rowSpan={3} className="align-bottom whitespace-nowrap">{c.label}</th>
              ))}
              <th rowSpan={3} className="align-bottom">{entityLabel}</th>
              {contextColumns.map((c) => (
                <th key={c.key} rowSpan={3} className="align-bottom whitespace-nowrap">{c.label}</th>
              ))}
              {input_products.length > 0 && (
                <th colSpan={input_products.length * inputColSpan()} className="text-center">INPUT</th>
              )}
              {output_products.length > 0 && (
                <th colSpan={output_products.reduce((n, p) => n + outputColSpan(p), 0)} className="text-center">
                  <span className="inline-flex items-center gap-1" title="Actual values shown in bold red fall outside the calculated Expected conversion range — like an abnormal result on a lab report">
                    OUTPUT <Info size={13} weight="bold" />
                  </span>
                </th>
              )}
              {stock_products.length > 0 && (
                <th colSpan={stock_products.length} className="text-center">
                  <span className="inline-flex items-center gap-1" title={stockCaption}>
                    {isMeeting ? "STOCK (AT SUBMISSION)" : "STOCK"} <Info size={13} weight="bold" />
                  </span>
                </th>
              )}
              {input_products.length + output_products.length + stock_products.length === 0 && (
                <th rowSpan={3}>No products with data for this selection</th>
              )}
            </tr>
            <tr>
              {input_products.map((p) => (
                <th key={p.id} rowSpan={2} className="text-center whitespace-nowrap">{p.product_name}<br />({p.unit_of_measure})</th>
              ))}
              {output_products.map((p) => (
                <th key={p.id} colSpan={outputColSpan(p)} className="text-center whitespace-nowrap">{p.product_name} ({p.unit_of_measure})</th>
              ))}
              {stock_products.map((p) => (
                <th key={p.id} rowSpan={2} className="text-center whitespace-nowrap">
                  {p.product_name}{!isMeeting && <><br />({p.unit_of_measure})</>}
                </th>
              ))}
            </tr>
            <tr>
              {output_products.map((p) => (
                <Fragment key={p.id}>
                  <th className="text-center whitespace-nowrap">Planned</th>
                  <th className="text-center whitespace-nowrap">Actual</th>
                  {p.expected_ranges.map((er) => (
                    <th key={er.standard_id} className="text-center whitespace-nowrap">
                      Expected (via {er.input_product_name})
                    </th>
                  ))}
                  <th className="text-center whitespace-nowrap">Loss Reason</th>
                  <th className="text-center whitespace-nowrap">Total Earned</th>
                </Fragment>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id}>
                {leadingColumns.map((c) => (
                  <td key={c.key} className="whitespace-nowrap">
                    {(row[c.key] as string | null | undefined) || <span style={{ color: "var(--text-muted)" }}>—</span>}
                  </td>
                ))}
                <td className="font-semibold whitespace-nowrap">{row.name}</td>
                {contextColumns.map((c) => (
                  <td key={c.key} className="whitespace-nowrap">
                    {(row[c.key] as string | null | undefined) || <span style={{ color: "var(--text-muted)" }}>—</span>}
                  </td>
                ))}
                {input_products.map((p) => {
                  const cell = row.input[p.id] || { total: 0, by_source: {} };
                  return <td key={p.id} className="text-right">{fmt(cell.total)}</td>;
                })}
                {output_products.map((p) => {
                  const cell = row.output[p.id] || {
                    planned: 0, actual: 0, expected_ranges: {}, next_month_plan: 0,
                    sold_quantity: 0, earning: 0, sold_rate: null, loss_reason_name: null,
                  };
                  // Out-of-range check mirrors a lab report's reference interval: only flag
                  // when a range was actually computed (real input data exists for it) — an
                  // empty/no-data row has no rng at all and is never flagged.
                  const ranges = p.expected_ranges.map((er) => ({ er, rng: cell.expected_ranges[er.standard_id] }));
                  const anyAbnormal = ranges.some(({ rng }) => rng && (cell.actual < rng.min || cell.actual > rng.max));
                  const abnormalStyle = { fontWeight: 700, color: "var(--error)" } as const;
                  return (
                    <Fragment key={p.id}>
                      <td className="text-right">{fmt(cell.planned)}</td>
                      <td className="text-right" style={anyAbnormal ? abnormalStyle : undefined}>{fmt(cell.actual)}</td>
                      {ranges.map(({ er, rng }) => {
                        const rngAbnormal = !!rng && (cell.actual < rng.min || cell.actual > rng.max);
                        return (
                          <td key={er.standard_id} className="text-right whitespace-nowrap" style={rngAbnormal ? abnormalStyle : undefined}>
                            {rng ? `${fmt(rng.min)}–${fmt(rng.max)}` : <span style={{ color: "var(--text-muted)" }}>—</span>}
                          </td>
                        );
                      })}
                      <td className="text-center whitespace-nowrap">{cell.loss_reason_name || <span style={{ color: "var(--text-muted)" }}>—</span>}</td>
                      <td className="text-right">{fmt(cell.earning)}</td>
                    </Fragment>
                  );
                })}
                {stock_products.map((p) => (
                  <td key={p.id} className="text-right">{fmt(row.stock[p.id] ?? 0)}</td>
                ))}
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={leadingColumns.length + 1 + contextColumns.length + input_products.length * inputColSpan() + output_products.reduce((n, p) => n + outputColSpan(p), 0) + stock_products.length}
                    className="text-center py-8" style={{ color: "var(--text-muted)" }}>
                  No records for this selection
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
