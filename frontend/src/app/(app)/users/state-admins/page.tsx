"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { Plus, X, ShieldStar, Pencil } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

interface Form { name: string; mobile_no: string; password: string }
const EMPTY: Form = { name: "", mobile_no: "", password: "" };

export default function StateAdminsPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<Form>(EMPTY);

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ["users-sa-all"],
    queryFn: async () => (await api.get("/users", { params: { role: "STATE_ADMIN", all: true } })).data,
  });

  const createMut = useMutation({
    mutationFn: () => api.post("/users/state-admin", form),
    onSuccess: () => { toast.success("State Admin created"); reset(); qc.invalidateQueries({ queryKey: ["users-sa-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const updateMut = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error("no target");
      const payload: Partial<Form> = { name: form.name };
      if (form.mobile_no && form.mobile_no !== editing.mobile_no) payload.mobile_no = form.mobile_no;
      if (form.password) payload.password = form.password;
      return api.patch(`/users/${editing.id}`, payload);
    },
    onSuccess: () => { toast.success("State Admin updated"); reset(); qc.invalidateQueries({ queryKey: ["users-sa-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/users/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["users-sa-all"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  function reset() { setCreating(false); setEditing(null); setForm(EMPTY); }
  function openCreate() { setEditing(null); setForm(EMPTY); setCreating(true); }
  function openEdit(u: User) { setCreating(false); setEditing(u); setForm({ name: u.name || "", mobile_no: u.mobile_no, password: "" }); }

  if (me?.role !== "STATE_ADMIN") return <div className="card p-6">Only State Admins can manage SA accounts.</div>;
  const showForm = creating || !!editing;

  return (
    <div data-testid="users-sa-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">State Admins</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Top-level administrators with statewide access. At least one active State Admin must always exist.
          </p>
        </div>
        <button onClick={openCreate} data-testid="users-sa-add"
          className="btn-primary inline-flex items-center gap-2"><Plus size={16} weight="bold" />New State Admin</button>
      </div>

      {showForm && (
        <div className="card p-5 mb-4" data-testid="users-sa-form">
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading text-lg font-bold">{editing ? `Edit ${editing.name || editing.mobile_no}` : "Create State Admin"}</div>
            <button onClick={reset}><X size={18} /></button>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); if (editing) updateMut.mutate(); else createMut.mutate(); }}
                className="grid grid-cols-2 gap-3">
            <label className="col-span-2"><span className="label-tag block mb-1">Name *</span>
              <input required data-testid="users-sa-input-name" className="input"
                value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
            <label><span className="label-tag block mb-1">Mobile *</span>
              <input required data-testid="users-sa-input-mobile" className="input"
                value={form.mobile_no} onChange={(e) => setForm({ ...form, mobile_no: e.target.value })} /></label>
            <label><span className="label-tag block mb-1">{editing ? "New Password (leave blank to keep)" : "Password *"}</span>
              <input required={!editing} type="password" data-testid="users-sa-input-password" className="input"
                value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
            <div className="col-span-2 flex justify-end gap-2">
              <button type="button" className="btn-secondary" onClick={reset}>Cancel</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending}
                data-testid="users-sa-form-submit" className="btn-primary">{editing ? "Save changes" : "Create"}</button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Name</th><th>Mobile</th><th>Status</th><th className="text-right">Actions</th></tr></thead>
          <tbody data-testid="users-sa-tbody">
            {users.map((u) => {
              const isMe = u.id === me?.id;
              const active = u.is_active !== false;
              return (
                <tr key={u.id} data-testid={`users-sa-row-${u.id}`}>
                  <td><ShieldStar size={16} weight="duotone" className="inline mr-2" />{u.name || "—"}
                    {isMe && <span className="badge badge-muted ml-2">You</span>}</td>
                  <td>{u.mobile_no}</td>
                  <td>{active
                    ? <span className="badge badge-success">Active</span>
                    : <span className="badge badge-muted">Inactive</span>}</td>
                  <td className="text-right">
                    <div className="inline-flex gap-2">
                      <button onClick={() => openEdit(u)} data-testid={`users-sa-edit-${u.id}`}
                        className="btn-secondary btn-sm inline-flex items-center gap-1"><Pencil size={12} />Edit</button>
                      <button onClick={() => toggleMut.mutate({ id: u.id, is_active: !active })}
                        disabled={toggleMut.isPending || isMe}
                        title={isMe ? "You cannot deactivate your own account" : ""}
                        data-testid={`users-sa-toggle-${u.id}`}
                        className={active ? "btn-secondary btn-sm" : "btn-primary btn-sm"}>
                        {active ? "Deactivate" : "Activate"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {users.length === 0 && <tr><td colSpan={4} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No State Admin accounts yet.</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
