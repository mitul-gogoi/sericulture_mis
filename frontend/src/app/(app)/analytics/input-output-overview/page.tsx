"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Product, District, AnalyticsResponse, AnalyticsProductionRow, AnalyticsInputRow, ProductMonthlyTrendResponse } from "@/lib/types";
import { ProductionTiles, StockTiles, InputTiles } from "../../dashboard/ProductTiles";
import { YoyPanel } from "./YoyPanel";

const SingleTrendChart = dynamic(() => import("../../dashboard/charts").then((m) => m.SingleTrendChart), { ssr: false });
const DistrictCompareBarChart = dynamic(() => import("../../dashboard/charts").then((m) => m.DistrictCompareBarChart), { ssr: false });

type View = "month-on-month" | "year-on-year" | "district-comparison";

function ViewPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={active ? "btn-primary btn-sm" : "btn-secondary btn-sm"}>
      {children}
    </button>
  );
}

function MonthOnMonthPanel({ productId, districtId }: { productId: string; districtId?: string }) {
  const { data: outputData } = useQuery<ProductMonthlyTrendResponse>({
    queryKey: ["product-monthly-trend", "output", productId, districtId],
    queryFn: async () => (await api.get("/reports/product-monthly-trend", {
      params: { metric: "output", product_id: productId || undefined, district_id: districtId || undefined },
    })).data,
    enabled: !!productId,
  });
  const { data: inputData } = useQuery<ProductMonthlyTrendResponse>({
    queryKey: ["product-monthly-trend", "input", productId, districtId],
    queryFn: async () => (await api.get("/reports/product-monthly-trend", {
      params: { metric: "input", product_id: productId || undefined, district_id: districtId || undefined },
    })).data,
    enabled: !!productId,
  });

  if (!productId) {
    return <div className="card p-6 text-sm text-center py-10" style={{ color: "var(--text-muted)" }}>Pick a product to see its month-on-month trend.</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="card p-6">
        <h3 className="font-heading text-lg font-bold mb-4">Output — last 12 months</h3>
        <div style={{ height: 240 }}>
          <SingleTrendChart data={outputData?.data || []} colorVar="var(--success)" />
        </div>
      </div>
      <div className="card p-6">
        <h3 className="font-heading text-lg font-bold mb-4">Input — last 12 months</h3>
        <div style={{ height: 240 }}>
          <SingleTrendChart data={inputData?.data || []} colorVar="var(--info)" />
        </div>
      </div>
    </div>
  );
}

function DistrictComparisonPanel({ productId }: { productId: string }) {
  const { data: outputData } = useQuery<AnalyticsResponse<AnalyticsProductionRow>>({
    queryKey: ["analytics-products", "district", productId],
    queryFn: async () => (await api.get("/reports/analytics/products", { params: { level: "district", product_id: productId } })).data,
    enabled: !!productId,
  });
  const { data: inputData } = useQuery<AnalyticsResponse<AnalyticsInputRow>>({
    queryKey: ["analytics-inputs", "district", productId],
    queryFn: async () => (await api.get("/reports/analytics/inputs", { params: { level: "district", product_id: productId } })).data,
    enabled: !!productId,
  });

  if (!productId) {
    return <div className="card p-6 text-sm text-center py-10" style={{ color: "var(--text-muted)" }}>Pick a product to compare across districts.</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="card p-6">
        <h3 className="font-heading text-lg font-bold mb-4">Output by district (current month)</h3>
        <div style={{ height: 280 }}>
          <DistrictCompareBarChart data={(outputData?.rows || []).map((r) => ({ name: r.name, value: r.actual }))} colorVar="var(--success)" />
        </div>
        {(!outputData?.rows || outputData.rows.length === 0) && <div className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>No output recorded this month</div>}
      </div>
      <div className="card p-6">
        <h3 className="font-heading text-lg font-bold mb-4">Input by district (current month)</h3>
        <div style={{ height: 280 }}>
          <DistrictCompareBarChart data={(inputData?.rows || []).map((r) => ({ name: r.name, value: r.total_qty }))} colorVar="var(--info)" />
        </div>
        {(!inputData?.rows || inputData.rows.length === 0) && <div className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>No input recorded this month</div>}
      </div>
    </div>
  );
}

export default function InputOutputOverviewPage() {
  const { user } = useAuth();
  const isSA = user?.role === "STATE_ADMIN";
  const [view, setView] = useState<View>("month-on-month");
  const [productId, setProductId] = useState("");
  const [districtId, setDistrictId] = useState("");

  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ["products"], queryFn: async () => (await api.get("/master/products")).data,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data,
    enabled: isSA,
  });
  const visibleProducts = products.filter((p) => p.show_in_dashboard);

  if (!user) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Input &amp; Output Overview</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Products farmer members consume as inputs and produce as outputs, month-on-month, year-on-year, and across districts.
          </p>
        </div>
      </div>

      <div className="card p-4 mb-6 flex items-center gap-3 flex-wrap">
        <div>
          <label className="label-tag block mb-1">Product</label>
          <select className="input min-w-[220px]" value={productId} onChange={(e) => setProductId(e.target.value)}>
            <option value="">Select a product</option>
            {visibleProducts.map((p) => <option key={p.id} value={p.id}>{p.product_name} ({p.unit_of_measure})</option>)}
          </select>
        </div>
        {isSA && view !== "district-comparison" && (
          <div>
            <label className="label-tag block mb-1">District</label>
            <select className="input min-w-[180px]" value={districtId} onChange={(e) => setDistrictId(e.target.value)}>
              <option value="">All districts</option>
              {districts.map((d) => <option key={d.id} value={d.id}>{d.district_name}</option>)}
            </select>
          </div>
        )}
        <div className="ml-auto flex items-center gap-1">
          <ViewPill active={view === "month-on-month"} onClick={() => setView("month-on-month")}>Month-on-Month</ViewPill>
          <ViewPill active={view === "year-on-year"} onClick={() => setView("year-on-year")}>Year-on-Year</ViewPill>
          {isSA && <ViewPill active={view === "district-comparison"} onClick={() => setView("district-comparison")}>District Comparison</ViewPill>}
        </div>
      </div>

      <InputTiles />
      <ProductionTiles />
      <StockTiles />

      {view === "month-on-month" && <MonthOnMonthPanel productId={productId} districtId={isSA ? districtId : undefined} />}
      {view === "year-on-year" && <YoyPanel productId={productId} districtId={isSA ? districtId : undefined} />}
      {view === "district-comparison" && isSA && <DistrictComparisonPanel productId={productId} />}
    </div>
  );
}
