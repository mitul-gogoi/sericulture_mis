"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { UsersThree, Pencil, X } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import type { User, District } from "@/lib/types";

interface Fig { id: string; fig_code: string; fig_name: string; district_id: string }

export default function FigPresidentsPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState({ name: "", mobile_no: "", password: "" });

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ["users-fp-all"],
    queryFn: async () => (await api.get("/users", { params: { role: "FIG_PRESIDENT", all: true } })).data,
  });
  const { data: figs = [] } = useQuery<Fig[]>({
    queryKey: ["figs-all"],
    queryFn: async () => (await api.get("/figs")).data,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"],
    queryFn: async () => (await api.get("/master/districts")).data,
  });

  const updateMut = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error("no target");
      const payload: Record<string, string> = { name: form.name };
      if (form.mobile_no && form.mobile_no !== editing.mobile_no) payload.mobile_no = form.mobile_no;
      if (form.password) payload.password = form.password;
      return api.patch(`/users/${editing.id}`, payload);
    },
    onSuccess: () => { toast.success("Updated"); setEditing(null); qc.invalidateQueries({ queryKey: ["users-fp-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/users/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["users-fp-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const figName = (id?: string | null) => figs.find((f) => f.id === id)?.fig_name || "—";
  const distName = (id?: string | null) => districts.find((d) => d.id === id)?.district_name || "—";

  if (me?.role !== "STATE_ADMIN") return <div className="card p-6">Only State Admins can manage FP accounts.</div>;

  return (
    <div data-testid="users-fp-page">
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">FIG Presidents</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          FIG President accounts are created automatically when a president is assigned in <b>FIG Management</b>.
          You can rename them, reset passwords, or deactivate here.
        </p>
      </div>

      {editing && (
        <div className="card p-5 mb-4" data-testid="users-fp-form">
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading text-lg font-bold">Edit {editing.name || editing.mobile_no}</div>
            <button onClick={() => setEditing(null)}><X size={18} /></button>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); updateMut.mutate(); }} className="grid grid-cols-2 gap-3">
            <label className="col-span-2"><span className="label-tag block mb-1">Name</span>
              <input data-testid="users-fp-input-name" className="input"
                value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
            <label><span className="label-tag block mb-1">Mobile</span>
              <input data-testid="users-fp-input-mobile" className="input"
                value={form.mobile_no} onChange={(e) => setForm({ ...form, mobile_no: e.target.value })} /></label>
            <label><span className="label-tag block mb-1">New Password (leave blank to keep)</span>
              <input type="password" data-testid="users-fp-input-password" className="input"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
            <div className="col-span-2 flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
              <button type="submit" disabled={updateMut.isPending}
                data-testid="users-fp-form-submit" className="btn-primary">Save changes</button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Name</th><th>Mobile</th><th>FIG</th><th>District</th><th>Status</th><th className="text-right">Actions</th></tr></thead>
          <tbody data-testid="users-fp-tbody">
            {users.map((u) => (
              <tr key={u.id} data-testid={`users-fp-row-${u.id}`}>
                <td><UsersThree size={16} weight="duotone" className="inline mr-2" />{u.name || "—"}</td>
                <td>{u.mobile_no}</td>
                <td>{figName(u.fig_id)}</td>
                <td>{distName(u.district_id)}</td>
                <td>{u.is_active !== false
                  ? <span className="badge badge-success">Active</span>
                  : <span className="badge badge-muted">Inactive</span>}</td>
                <td className="text-right">
                  <div className="inline-flex gap-2">
                    <button onClick={() => { setEditing(u); setForm({ name: u.name || "", mobile_no: u.mobile_no, password: "" }); }}
                      data-testid={`users-fp-edit-${u.id}`}
                      className="btn-secondary btn-sm inline-flex items-center gap-1"><Pencil size={12} />Edit</button>
                    <button onClick={() => toggleMut.mutate({ id: u.id, is_active: !(u.is_active !== false) })}
                      disabled={toggleMut.isPending}
                      data-testid={`users-fp-toggle-${u.id}`}
                      className={u.is_active !== false ? "btn-secondary btn-sm" : "btn-primary btn-sm"}>
                      {u.is_active !== false ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && <tr><td colSpan={6} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No FIG President accounts yet. Assign a president under FIG Management.</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
