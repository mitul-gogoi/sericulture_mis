"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api";
import { fyOptions } from "@/lib/fiscal";

interface ProductSummaryRow {
  product_id: string; product_name: string; unit_of_measure: string; is_byproduct: boolean;
  planned: number; actual: number; byproduct_qty: number;
}
interface StockSummaryRow {
  product_id: string; product_name: string; unit_of_measure: string; stock: number; is_perishable: boolean;
}
interface InputSummaryRow {
  product_id: string; product_name: string; unit_of_measure: string; total_qty: number;
}

// Shared tile-card grid — colorVar/bgVar drive the Output(green)/Input(teal)/Stock(amber)
// visual families so input-vs-output-vs-stock is legible from color alone at a glance.
function TileGrid<T>({ rows, colorVar, bgVar, getKey, getLabel, getValue, getUnit, getHref, emptyText, renderBadge }: {
  rows: T[]; colorVar: string; bgVar: string;
  getKey: (r: T) => string; getLabel: (r: T) => string;
  getValue: (r: T) => number; getUnit: (r: T) => string;
  getHref: (r: T) => string; emptyText: string;
  renderBadge?: (r: T) => React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {rows.map((r) => (
        <Link key={getKey(r)} href={getHref(r)} className="card p-3 hover:shadow-sm transition"
              style={{ background: bgVar, borderLeft: `3px solid ${colorVar}` }}>
          <div className="text-xs font-semibold truncate flex items-center gap-1">
            <span className="truncate">{getLabel(r)}</span>
            {renderBadge?.(r)}
          </div>
          <div className="font-heading text-xl font-extrabold mt-1">{getValue(r).toLocaleString(undefined, { maximumFractionDigits: 1 })}</div>
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>{getUnit(r)}</div>
        </Link>
      ))}
      {rows.length === 0 && <div className="col-span-2 md:col-span-4 text-center text-sm py-4" style={{ color: "var(--text-muted)" }}>{emptyText}</div>}
    </div>
  );
}

export function ProductionTiles() {
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data } = useQuery<{ rows: ProductSummaryRow[] }>({
    queryKey: ["product-summary", month, fy],
    queryFn: async () => (await api.get("/reports/product-summary", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
  });
  // Byproducts count as Output too — show byproduct_qty for byproduct-flagged products
  // instead of filtering them out, so e.g. Eri Pupa/Silk Waste appear alongside cocoon/yarn.
  const rows = (data?.rows || []).filter((r) => (r.is_byproduct ? r.byproduct_qty : r.actual) > 0);

  return (
    <div className="card p-6 mb-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h3 className="font-heading text-lg font-bold">Production by product</h3>
        <div className="flex items-center gap-2">
          <input type="month" className="input max-w-[140px] text-sm" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>or</span>
          <select className="input max-w-[120px] text-sm" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
            <option value="">Fiscal year</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>
      <TileGrid<ProductSummaryRow>
        rows={rows} colorVar="var(--success)" bgVar="#E5EFE7"
        getKey={(r) => r.product_id} getLabel={(r) => r.product_name}
        getValue={(r) => (r.is_byproduct ? r.byproduct_qty : r.actual)} getUnit={(r) => r.unit_of_measure}
        getHref={(r) => `/analytics/products?product_id=${r.product_id}`}
        emptyText="No production recorded yet"
      />
    </div>
  );
}

export function StockTiles() {
  const { data } = useQuery<{ rows: StockSummaryRow[] }>({
    queryKey: ["stock-summary"],
    queryFn: async () => (await api.get("/reports/stock-summary")).data,
  });
  const rows = (data?.rows || []).filter((r) => r.stock !== 0);

  return (
    <div className="card p-6 mb-6">
      <h3 className="font-heading text-lg font-bold mb-4">Current stock by product</h3>
      <TileGrid<StockSummaryRow>
        rows={rows} colorVar="var(--secondary)" bgVar="#F8EFD9"
        getKey={(r) => r.product_id} getLabel={(r) => r.product_name}
        getValue={(r) => r.stock} getUnit={(r) => r.unit_of_measure}
        getHref={(r) => `/analytics/stock?product_id=${r.product_id}`}
        emptyText="No stock on hand yet"
        renderBadge={(r) => r.is_perishable && <span className="badge badge-warning" style={{ fontSize: "9px", padding: "1px 4px" }}>Perishable</span>}
      />
    </div>
  );
}

export function InputTiles() {
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data } = useQuery<{ rows: InputSummaryRow[] }>({
    queryKey: ["input-summary", month, fy],
    queryFn: async () => (await api.get("/reports/input-summary", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
  });
  const rows = (data?.rows || []).filter((r) => r.total_qty > 0);

  return (
    <div className="card p-6 mb-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h3 className="font-heading text-lg font-bold">Input consumption by product</h3>
        <div className="flex items-center gap-2">
          <input type="month" className="input max-w-[140px] text-sm" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>or</span>
          <select className="input max-w-[120px] text-sm" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
            <option value="">Fiscal year</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>
      <TileGrid<InputSummaryRow>
        rows={rows} colorVar="var(--info)" bgVar="#DEEBF1"
        getKey={(r) => r.product_id} getLabel={(r) => r.product_name}
        getValue={(r) => r.total_qty} getUnit={(r) => r.unit_of_measure}
        getHref={(r) => `/analytics/inputs?product_id=${r.product_id}`}
        emptyText="No inputs recorded yet"
      />
    </div>
  );
}
