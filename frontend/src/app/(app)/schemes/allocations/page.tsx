"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, X, Stack } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { District } from "@/lib/types";

interface Scheme { id: string; scheme_name: string; total_budget_rs: number; is_active: boolean }
interface Allocation {
  id: string;
  scheme_id: string;
  district_id: string;
  allocated_amount_rs: number;
  utilised: number;
  remaining: number;
}

export default function SchemeAllocationsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ scheme_id: "", district_id: "", allocated_amount_rs: 0 });

  const { data: schemes = [] } = useQuery<Scheme[]>({
    queryKey: ["schemes-alloc"],
    queryFn: async () => (await api.get("/schemes")).data,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"],
    queryFn: async () => (await api.get("/master/districts")).data,
  });
  const { data: allocations = [] } = useQuery<Allocation[]>({
    queryKey: ["allocations"],
    queryFn: async () => (await api.get("/schemes/allocations")).data,
  });

  const createMut = useMutation({
    mutationFn: () => api.post("/schemes/allocations", form),
    onSuccess: (res) => {
      toast.success("Allocation created");
      if (res.data?.warning) toast.warning(res.data.warning);
      setOpen(false); setForm({ scheme_id: "", district_id: "", allocated_amount_rs: 0 }); qc.invalidateQueries({ queryKey: ["allocations"] });
    },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const isSA = user?.role === "STATE_ADMIN";
  const schemeName = (id: string) => schemes.find((s) => s.id === id)?.scheme_name || "—";
  const distName = (id: string) => districts.find((d) => d.id === id)?.district_name || "—";

  return (
    <div data-testid="schemes-alloc-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Scheme Allocations</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {isSA ? "Allocate scheme budgets to districts. Utilisation and remaining amounts update as beneficiaries are registered." : "District-wise allocations for schemes."}
          </p>
        </div>
        {isSA && <button onClick={() => setOpen(true)} data-testid="schemes-alloc-add"
          className="btn-primary inline-flex items-center gap-2"><Plus size={16} weight="bold" />New allocation</button>}
      </div>

      {open && (
        <div className="card p-5 mb-4" data-testid="schemes-alloc-form">
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading text-lg font-bold">Create Allocation</div>
            <button onClick={() => setOpen(false)}><X size={18} /></button>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(); }} className="grid grid-cols-2 gap-3">
            <label className="col-span-2"><span className="label-tag block mb-1">Scheme *</span>
              <select required data-testid="schemes-alloc-input-scheme" className="input"
                value={form.scheme_id} onChange={(e) => setForm({ ...form, scheme_id: e.target.value })}>
                <option value="">Select…</option>
                {schemes.filter((s) => s.is_active).map((s) => (<option key={s.id} value={s.id}>{s.scheme_name}</option>))}
              </select></label>
            <label><span className="label-tag block mb-1">District *</span>
              <select required data-testid="schemes-alloc-input-district" className="input"
                value={form.district_id} onChange={(e) => setForm({ ...form, district_id: e.target.value })}>
                <option value="">Select…</option>
                {districts.map((d) => (<option key={d.id} value={d.id}>{d.district_name}</option>))}
              </select></label>
            <label><span className="label-tag block mb-1">Amount (₹) *</span>
              <input required type="number" data-testid="schemes-alloc-input-amount" className="input"
                value={form.allocated_amount_rs}
                onChange={(e) => setForm({ ...form, allocated_amount_rs: parseFloat(e.target.value) || 0 })} /></label>
            <div className="col-span-2 flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
              <button type="submit" disabled={createMut.isPending}
                data-testid="schemes-alloc-form-submit" className="btn-primary">Create</button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th><Stack size={14} weight="bold" className="inline mr-1" />Scheme</th><th>District</th><th className="text-right">Allocated (₹)</th><th className="text-right">Utilised (₹)</th><th className="text-right">Remaining (₹)</th></tr></thead>
          <tbody>
            {allocations.map((a) => (
              <tr key={a.id}>
                <td className="font-semibold">{schemeName(a.scheme_id)}</td>
                <td>{distName(a.district_id)}</td>
                <td className="text-right">{(a.allocated_amount_rs || 0).toLocaleString()}</td>
                <td className="text-right">{(a.utilised || 0).toLocaleString()}</td>
                <td className="text-right">{(a.remaining || 0).toLocaleString()}</td>
              </tr>
            ))}
            {allocations.length === 0 && <tr><td colSpan={5} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No allocations yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
