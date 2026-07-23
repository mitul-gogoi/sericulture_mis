"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { fyOptions } from "@/lib/fiscal";
import type { Yield, Farmer, Product, LossReason } from "@/lib/types";

export default function YieldsPage() {
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");
  const { data: yields = [] } = useQuery<Yield[]>({
    queryKey: ["yields", month, fy],
    queryFn: async () => (await api.get("/yields", { params: fy ? { fiscal_year: fy } : month ? { month } : {} })).data,
  });
  const { data: farmers = [] } = useQuery<Farmer[]>({ queryKey: ["farmers-all"], queryFn: async () => (await api.get("/farmers")).data });
  const { data: products = [] } = useQuery<Product[]>({ queryKey: ["products"], queryFn: async () => (await api.get("/master/products")).data });
  const { data: lossReasons = [] } = useQuery<LossReason[]>({ queryKey: ["loss-reasons"], queryFn: async () => (await api.get("/master/loss-reasons")).data });

  const fname = (id: string) => { const f = farmers.find((x) => x.id === id); return f ? `${f.first_name} ${f.last_name}` : id.slice(0, 8); };
  const pname = (id?: string | null) => (id && products.find((p) => p.id === id)?.product_name) || "—";
  const lrname = (id?: string | null) => (id && lossReasons.find((l) => l.id === id)?.reason_name) || "—";

  return (
    <div>
      <div className="mb-5"><h1 className="font-heading text-3xl font-extrabold">Yield records</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Farmer-level monthly yield submissions</p></div>
      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap">
        <label className="label-tag">Month</label>
        <input type="month" className="input max-w-xs" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
        <label className="label-tag">or fiscal year</label>
        <select className="input max-w-xs" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
          <option value="">Select</option>
          {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
      </div>
      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th>Month</th><th>Farmer</th><th>Product</th><th>Type</th><th>Planned</th><th>Actual</th><th>Stock</th><th>Earning</th><th>Loss reason</th></tr></thead>
          <tbody>
            {yields.map((y) => (
              <tr key={y.id}>
                <td>{y.yield_month}</td>
                <td>{fname(y.farmer_id)}</td>
                <td>{pname(y.product_id)}</td>
                <td>{y.is_primary_stage ? <span className="badge badge-success">Primary</span> : <span className="badge badge-muted">Non-primary</span>}</td>
                <td>{y.planned_yield}</td>
                <td>{y.actual_yield}</td>
                <td>{y.stock_balance}</td>
                <td>{(y.earning || 0).toLocaleString()}</td>
                <td>{lrname(y.loss_reason_id)}</td>
              </tr>
            ))}
            {yields.length === 0 && <tr><td colSpan={9} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No yield data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
