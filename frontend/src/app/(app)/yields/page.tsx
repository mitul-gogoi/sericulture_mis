"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ExportButtons } from "@/components/ExportButtons";
import type { Product, YieldMatrixLevel, YieldMatrixResponse } from "@/lib/types";
import { YieldMatrixTable } from "./YieldMatrixTable";

const GRANULARITY_OPTIONS: { value: YieldMatrixLevel; label: string }[] = [
  { value: "state", label: "State-wise" },
  { value: "district", label: "District-wise" },
  { value: "sericulture_circle", label: "Sericulture Circle-wise" },
  { value: "fig", label: "FIG-wise" },
  { value: "farmer", label: "Farmer-wise" },
  { value: "meeting", label: "Meeting-submission-wise" },
];

const ENTITY_LABEL: Record<YieldMatrixLevel, string> = {
  state: "State",
  district: "District",
  sericulture_circle: "Sericulture Circle",
  fig: "FIG",
  farmer: "Farmer",
  meeting: "Farmer", // meeting-submission-wise rows are still keyed by farmer — Meeting ID/Month render as their own leading columns
};

function currentMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

export default function YieldsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  // Dashboard product tiles (Production/Stock/Input) deep-link here with ?product_id=X (and,
  // for State Admin, ?level=state) so the admin lands on exactly the number the tile showed —
  // seeded once into initial state so the "default to everything available" effect below never
  // overwrites it (that effect only fires when productIds is still null).
  const initialProductId = searchParams.get("product_id");
  const initialLevel = searchParams.get("level") as YieldMatrixLevel | null;
  const initialMonth = searchParams.get("month");
  const granularityOptions = GRANULARITY_OPTIONS.filter((opt) => opt.value !== "state" || user?.role === "STATE_ADMIN");
  const [granularity, setGranularity] = useState<YieldMatrixLevel>(initialLevel || "district");
  const [periodMode, setPeriodMode] = useState<"month" | "range">("month");
  const [month, setMonth] = useState(initialMonth || currentMonth());
  const [fromMonth, setFromMonth] = useState(currentMonth());
  const [toMonth, setToMonth] = useState(currentMonth());
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [productIds, setProductIds] = useState<Set<string> | null>(initialProductId ? new Set([initialProductId]) : null);
  const [showProductPicker, setShowProductPicker] = useState(false);

  const { data: allProducts = [] } = useQuery<Product[]>({
    queryKey: ["master-products-all"],
    queryFn: async () => (await api.get("/master/products?all=true")).data,
  });

  const periodParams: Record<string, string> = periodMode === "month" ? { month } : { from_month: fromMonth, to_month: toMonth };

  const queryParams: Record<string, string> = {
    level: granularity,
    ...periodParams,
    page: String(page),
    page_size: String(pageSize),
    ...(productIds ? { product_ids: Array.from(productIds).join(",") } : {}),
  };

  const { data, isLoading } = useQuery<YieldMatrixResponse>({
    queryKey: ["yield-matrix", queryParams],
    queryFn: async () => (await api.get("/reports/analytics/yield-matrix", { params: queryParams })).data,
  });

  // Default the Products-shown selection to "everything with data" whenever the
  // granularity/period changes and we don't yet have an explicit selection.
  useEffect(() => {
    if (data && productIds === null) {
      const all = new Set([...data.available_products.input, ...data.available_products.output, ...data.available_products.stock]);
      setProductIds(all);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  function resetSelection() {
    setPage(1);
    setProductIds(null);
  }

  function toggleProduct(id: string, checked: boolean) {
    setProductIds((prev) => {
      const next = new Set(prev ?? []);
      if (checked) next.add(id); else next.delete(id);
      return next;
    });
  }

  const availableProductList = data
    ? allProducts.filter((p) =>
        data.available_products.input.includes(p.id) ||
        data.available_products.output.includes(p.id) ||
        data.available_products.stock.includes(p.id))
    : [];

  const total = data?.total ?? 0;
  const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const showingTo = Math.min(page * pageSize, total);

  const exportParams: Record<string, string> = {
    level: granularity,
    ...periodParams,
    ...(productIds ? { product_ids: Array.from(productIds).join(",") } : {}),
  };

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">Yield View</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Aggregated input, output, and stock by district, circle, FIG, or farmer.
        </p>
      </div>

      <div className="card p-4 mb-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div role="radiogroup" aria-label="Granularity" className="flex flex-wrap items-center gap-3">
            {granularityOptions.map((opt) => (
              <label key={opt.value} className="flex items-center gap-1.5 text-sm">
                <input
                  type="radio" name="granularity" checked={granularity === opt.value}
                  onChange={() => { setGranularity(opt.value); resetSelection(); }}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select className="input max-w-xs" value={periodMode}
                  onChange={(e) => { setPeriodMode(e.target.value as "month" | "range"); resetSelection(); }}>
            <option value="month">Month-wise</option>
            <option value="range">Date Range</option>
          </select>
          {periodMode === "month" ? (
            <input type="month" className="input max-w-xs" value={month}
                   onChange={(e) => { setMonth(e.target.value); resetSelection(); }} />
          ) : (
            <>
              <label className="label-tag">From</label>
              <input type="month" className="input max-w-xs" value={fromMonth}
                     onChange={(e) => { setFromMonth(e.target.value); resetSelection(); }} />
              <label className="label-tag">To</label>
              <input type="month" className="input max-w-xs" value={toMonth}
                     onChange={(e) => { setToMonth(e.target.value); resetSelection(); }} />
            </>
          )}
        </div>

        <div className="relative">
          <button type="button" className="btn-secondary text-sm" onClick={() => setShowProductPicker((s) => !s)}>
            Products shown ({productIds?.size ?? 0})
          </button>
          {showProductPicker && (
            <div className="card p-3 mt-2 absolute z-10 max-h-64 overflow-y-auto" style={{ minWidth: 260 }}>
              {availableProductList.length === 0 && (
                <div className="text-sm" style={{ color: "var(--text-muted)" }}>No products with data for this selection.</div>
              )}
              {availableProductList.map((p) => (
                <label key={p.id} className="flex items-center gap-2 text-sm py-1">
                  <input type="checkbox" checked={productIds?.has(p.id) ?? false}
                         onChange={(e) => toggleProduct(p.id, e.target.checked)} />
                  {p.product_name}
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {isLoading && <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>}

      {data && <YieldMatrixTable data={data} entityLabel={ENTITY_LABEL[granularity]} />}

      {data && (
        <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            Showing {showingFrom}–{showingTo} of {total}
          </div>
          <div className="flex items-center gap-3">
            <select className="input" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              {[25, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}
            </select>
            <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
            <button className="btn-secondary" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
            <ExportButtons report="yield-matrix" params={exportParams} />
          </div>
        </div>
      )}
    </div>
  );
}
