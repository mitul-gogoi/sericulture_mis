"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import api from "@/lib/api";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";

const ProductProductionChart = dynamic(() => import("./charts").then((m) => m.ProductProductionChart), { ssr: false });

interface YieldRow { product_id: string; product: { product_name: string }; planned: number; actual: number; earning: number; count: number; }

export default function ReportsPage() {
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data: ys = [] } = useQuery<YieldRow[]>({
    queryKey: ["yield-summary", month, fy],
    queryFn: async () => (await api.get("/reports/yield-summary", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
  });

  const total = ys.reduce((s, y) => ({
    planned: s.planned + y.planned, actual: s.actual + y.actual, earning: s.earning + y.earning,
  }), { planned: 0, actual: 0, earning: 0 });

  return (
    <div>
      <div className="mb-5"><h1 className="font-heading text-3xl font-extrabold">Reports & analytics</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Aggregated production and earnings — see the Analytics section for current stock (a point-in-time balance, not tied to a period).
        </p></div>
      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <label className="label-tag">Filter month</label>
          <input type="month" className="input max-w-xs" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
          <label className="label-tag">or fiscal year</label>
          <select className="input max-w-xs" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
            <option value="">Select</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
          <button onClick={() => { setMonth(""); setFy(""); }} className="btn-secondary text-sm">Clear</button>
        </div>
        <ExportButtons report="yield-summary" params={fy ? { fiscal_year: fy } : month ? { month } : {}} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="stat-card"><span className="label-tag">Planned</span><div className="font-heading text-2xl font-extrabold mt-2">{total.planned.toFixed(1)}</div></div>
        <div className="stat-card"><span className="label-tag">Actual</span><div className="font-heading text-2xl font-extrabold mt-2">{total.actual.toFixed(1)}</div></div>
        <div className="stat-card"><span className="label-tag">Earnings (₹)</span><div className="font-heading text-2xl font-extrabold mt-2">{total.earning.toLocaleString()}</div></div>
      </div>

      <div className="card p-6 mb-6">
        <h3 className="font-heading text-lg font-bold mb-4">Product-wise production</h3>
        <div style={{ height: 320 }}>
          <ProductProductionChart data={ys.map((y) => ({ product: y.product?.product_name, planned: y.planned, actual: y.actual }))} />
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th>Product</th><th>Planned</th><th>Actual</th><th>Earning</th><th>Records</th></tr></thead>
          <tbody>
            {ys.map((y) => (
              <tr key={y.product_id}>
                <td className="font-semibold">{y.product?.product_name}</td>
                <td>{y.planned.toFixed(1)}</td>
                <td>{y.actual.toFixed(1)}</td>
                <td>{y.earning.toLocaleString()}</td>
                <td>{y.count}</td>
              </tr>
            ))}
            {ys.length === 0 && <tr><td colSpan={5} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data yet</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
