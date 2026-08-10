"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";

function currentMonth(): string {
  return new Date().toISOString().slice(0, 7);
}

interface ProductSummaryRow {
  product_id: string; product_name: string; unit_of_measure: string; is_byproduct: boolean;
  planned: number; actual: number; byproduct_qty: number;
}
interface StockSummaryRow {
  product_id: string; product_name: string; unit_of_measure: string; stock: number; is_perishable: boolean;
}
// Yield View (State/District Admin only) now supersedes the deleted Production/Stock/Input
// Explorer pages — a tile click deep-links there instead, pre-filtered to that one product.
// State Admin's tile numbers are state-wide (no district scoping), so "state" granularity is
// what makes the number the admin lands on match the tile exactly; District Admin's existing
// default granularity ("district") already shows exactly their one district. FIG_PRESIDENT has
// no Yield View access at all, so their tiles render as plain, non-clickable display instead.
function yieldViewHref(role: Role | undefined, productId: string, month?: string): string | null {
  if (role === "FIG_PRESIDENT" || role === "FARMER") return null;
  const params = new URLSearchParams({ product_id: productId });
  if (role === "STATE_ADMIN") params.set("level", "state");
  if (month) params.set("month", month);
  return `/yields?${params.toString()}`;
}

// Shared tile-card grid — colorVar/bgVar drive the Output(green)/Input(teal)/Stock(amber)
// visual families so input-vs-output-vs-stock is legible from color alone at a glance.
function TileGrid<T>({ rows, colorVar, bgVar, getKey, getLabel, getValue, getUnit, getHref, emptyText, renderBadge }: {
  rows: T[]; colorVar: string; bgVar: string;
  getKey: (r: T) => string; getLabel: (r: T) => string;
  getValue: (r: T) => number; getUnit: (r: T) => string;
  getHref: (r: T) => string | null; emptyText: string;
  renderBadge?: (r: T) => React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {rows.map((r) => {
        const href = getHref(r);
        const content = (
          <>
            <div className="text-xs font-semibold truncate flex items-center gap-1">
              <span className="truncate">{getLabel(r)}</span>
              {renderBadge?.(r)}
            </div>
            <div className="font-heading text-xl font-extrabold mt-1">{getValue(r).toLocaleString(undefined, { maximumFractionDigits: 1 })}</div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>{getUnit(r)}</div>
          </>
        );
        return href ? (
          <Link key={getKey(r)} href={href} className="card p-3 hover:shadow-sm transition"
                style={{ background: bgVar, borderLeft: `3px solid ${colorVar}` }}>
            {content}
          </Link>
        ) : (
          <div key={getKey(r)} className="card p-3" style={{ background: bgVar, borderLeft: `3px solid ${colorVar}` }}>
            {content}
          </div>
        );
      })}
      {rows.length === 0 && <div className="col-span-2 md:col-span-4 text-center text-sm py-4" style={{ color: "var(--text-muted)" }}>{emptyText}</div>}
    </div>
  );
}

export function ProductionTiles() {
  const { user } = useAuth();
  const month = currentMonth();
  const { data } = useQuery<{ rows: ProductSummaryRow[] }>({
    queryKey: ["product-summary", month],
    queryFn: async () => (await api.get("/reports/product-summary", { params: { month } })).data,
  });
  // Byproducts count as Output too — show byproduct_qty for byproduct-flagged products
  // instead of filtering them out, so e.g. Eri Pupa/Silk Waste appear alongside cocoon/yarn.
  const rows = (data?.rows || []).filter((r) => (r.is_byproduct ? r.byproduct_qty : r.actual) > 0);

  return (
    <div className="card p-6 mb-6">
      <h3 className="font-heading text-lg font-bold mb-4">Production (Current Month)</h3>
      <TileGrid<ProductSummaryRow>
        rows={rows} colorVar="var(--success)" bgVar="#E5EFE7"
        getKey={(r) => r.product_id} getLabel={(r) => r.product_name}
        getValue={(r) => (r.is_byproduct ? r.byproduct_qty : r.actual)} getUnit={(r) => r.unit_of_measure}
        getHref={(r) => yieldViewHref(user?.role, r.product_id, month)}
        emptyText="No production recorded yet"
      />
    </div>
  );
}

export function StockTiles() {
  const { user } = useAuth();
  const { data } = useQuery<{ rows: StockSummaryRow[] }>({
    queryKey: ["stock-summary"],
    queryFn: async () => (await api.get("/reports/stock-summary")).data,
  });
  const rows = (data?.rows || []).filter((r) => r.stock !== 0);

  return (
    <div className="card p-6 mb-6">
      <h3 className="font-heading text-lg font-bold mb-4">Current Stock</h3>
      <TileGrid<StockSummaryRow>
        rows={rows} colorVar="var(--secondary)" bgVar="#F8EFD9"
        getKey={(r) => r.product_id} getLabel={(r) => r.product_name}
        getValue={(r) => r.stock} getUnit={(r) => r.unit_of_measure}
        getHref={(r) => yieldViewHref(user?.role, r.product_id)}
        emptyText="No stock on hand yet"
        renderBadge={(r) => r.is_perishable && <span className="badge badge-warning" style={{ fontSize: "9px", padding: "1px 4px" }}>Perishable</span>}
      />
    </div>
  );
}
