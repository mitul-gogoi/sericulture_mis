"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { Plus, X, UserCircle, Pencil } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import type { User, District } from "@/lib/types";

interface EditForm { name: string; mobile_no: string; password: string; district_id: string }

export default function DistrictAdminsPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<EditForm>({ name: "", mobile_no: "", password: "", district_id: "" });

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ["users-da-all"],
    queryFn: async () => (await api.get("/users", { params: { role: "DISTRICT_ADMIN", all: true } })).data,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"],
    queryFn: async () => (await api.get("/master/districts")).data,
  });

  const createMut = useMutation({
    mutationFn: () => api.post("/users/district-admin", form),
    onSuccess: () => { toast.success("District Admin created"); reset(); qc.invalidateQueries({ queryKey: ["users-da-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const updateMut = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error("no target");
      const payload: Partial<EditForm> = { name: form.name, district_id: form.district_id };
      if (form.mobile_no && form.mobile_no !== editing.mobile_no) payload.mobile_no = form.mobile_no;
      if (form.password) payload.password = form.password;
      return api.patch(`/users/${editing.id}`, payload);
    },
    onSuccess: () => { toast.success("District Admin updated"); reset(); qc.invalidateQueries({ queryKey: ["users-da-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/users/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["users-da-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  function reset() {
    setCreateOpen(false);
    setEditing(null);
    setForm({ name: "", mobile_no: "", password: "", district_id: "" });
  }

  function openEdit(u: User) {
    setEditing(u);
    setForm({ name: u.name || "", mobile_no: u.mobile_no, password: "", district_id: u.district_id || "" });
    setCreateOpen(false);
  }

  const distName = (id?: string | null) => districts.find((d) => d.id === id)?.district_name || "—";

  if (me?.role !== "STATE_ADMIN") return <div className="card p-6">Only State Admins can manage DA accounts.</div>;
  const showForm = createOpen || !!editing;

  return (
    <div data-testid="users-da-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">District Admins</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>One active DA per district. Deactivate before reassigning a district.</p>
        </div>
        <button onClick={() => { setEditing(null); setForm({ name: "", mobile_no: "", password: "", district_id: "" }); setCreateOpen(true); }}
          data-testid="users-da-add"
          className="btn-primary inline-flex items-center gap-2"><Plus size={16} weight="bold" />New DA</button>
      </div>

      {showForm && (
        <div className="card p-5 mb-4" data-testid="users-da-form">
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading text-lg font-bold">{editing ? `Edit ${editing.name || editing.mobile_no}` : "Create District Admin"}</div>
            <button onClick={reset}><X size={18} /></button>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); if (editing) updateMut.mutate(); else createMut.mutate(); }}
                className="grid grid-cols-2 gap-3">
            <label className="col-span-2"><span className="label-tag block mb-1">Name *</span>
              <input required data-testid="users-da-input-name" className="input"
                value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
            <label><span className="label-tag block mb-1">Mobile *</span>
              <input required data-testid="users-da-input-mobile" className="input"
                value={form.mobile_no} onChange={(e) => setForm({ ...form, mobile_no: e.target.value })} /></label>
            <label><span className="label-tag block mb-1">{editing ? "New Password (leave blank to keep)" : "Password *"}</span>
              <input required={!editing} type="password" data-testid="users-da-input-password" className="input"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
            <label className="col-span-2"><span className="label-tag block mb-1">District *</span>
              <select required data-testid="users-da-input-district" className="input"
                value={form.district_id} onChange={(e) => setForm({ ...form, district_id: e.target.value })}>
                <option value="">Select…</option>
                {districts.map((d) => (<option key={d.id} value={d.id}>{d.district_name}</option>))}
              </select></label>
            <div className="col-span-2 flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={reset}>Cancel</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending}
                data-testid="users-da-form-submit" className="btn-primary">{editing ? "Save changes" : "Create"}</button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Name</th><th>Mobile</th><th>District</th><th>Status</th><th className="text-right">Actions</th></tr></thead>
          <tbody data-testid="users-da-tbody">
            {users.map((u) => (
              <tr key={u.id} data-testid={`users-da-row-${u.id}`}>
                <td><UserCircle size={16} weight="duotone" className="inline mr-2" />{u.name || "—"}</td>
                <td>{u.mobile_no}</td>
                <td>{distName(u.district_id)}</td>
                <td>{u.is_active !== false
                  ? <span className="badge badge-success">Active</span>
                  : <span className="badge badge-muted">Inactive</span>}</td>
                <td className="text-right">
                  <div className="inline-flex gap-2">
                    <button onClick={() => openEdit(u)} data-testid={`users-da-edit-${u.id}`}
                      className="btn-secondary btn-sm inline-flex items-center gap-1"><Pencil size={12} />Edit</button>
                    <button onClick={() => toggleMut.mutate({ id: u.id, is_active: !(u.is_active !== false) })}
                      disabled={toggleMut.isPending}
                      data-testid={`users-da-toggle-${u.id}`}
                      className={u.is_active !== false ? "btn-secondary btn-sm" : "btn-primary btn-sm"}>
                      {u.is_active !== false ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && <tr><td colSpan={5} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No DA accounts yet.</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
