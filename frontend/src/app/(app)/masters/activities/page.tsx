"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, X, Check, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { SilkType, Activity } from "@/lib/types";

const EMPTY = { silk_type_id: "", step_no: "", activity_name: "", description: "" };

export default function ActivitiesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Activity | null>(null);
  const [form, setForm] = useState(EMPTY);

  const { data: silkTypes = [] } = useQuery<SilkType[]>({
    queryKey: ["master-silk-types-all"],
    queryFn: async () => (await api.get("/master/silk-types?all=true")).data,
  });
  const { data: activities = [], isLoading } = useQuery<Activity[]>({
    queryKey: ["master-activities"],
    queryFn: async () => (await api.get("/master/activities?all=true")).data,
  });

  function resetForm() { setShowForm(false); setEditing(null); setForm(EMPTY); }
  function openCreate() { setEditing(null); setForm(EMPTY); setShowForm(true); }
  function openEdit(a: Activity) {
    setEditing(a);
    setForm({
      silk_type_id: a.silk_type_id,
      step_no: String(a.step_no), activity_name: a.activity_name, description: a.description || "",
    });
    setShowForm(true);
  }

  function payload() {
    return {
      activity_name: form.activity_name.trim(), silk_type_id: form.silk_type_id,
      step_no: Number(form.step_no),
      description: form.description.trim() || null,
    };
  }

  const createMut = useMutation({
    mutationFn: () => api.post("/master/activities", payload()),
    onSuccess: () => { toast.success("Activity created"); qc.invalidateQueries({ queryKey: ["master-activities"] }); resetForm(); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });
  const updateMut = useMutation({
    mutationFn: (id: string) => api.patch(`/master/activities/${id}`, payload()),
    onSuccess: () => { toast.success("Activity updated"); qc.invalidateQueries({ queryKey: ["master-activities"] }); resetForm(); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });
  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/master/activities/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["master-activities"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/master/activities/${id}`),
    onSuccess: () => { toast.success("Activity deleted"); qc.invalidateQueries({ queryKey: ["master-activities"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  function onDelete(a: Activity) {
    if (!window.confirm(`Delete "${a.activity_name}" permanently? This cannot be undone.`)) return;
    deleteMut.mutate(a.id);
  }
  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editing) updateMut.mutate(editing.id);
    else createMut.mutate();
  }

  const grouped = useMemo(() => {
    const g: Record<string, Activity[]> = {};
    for (const a of activities) {
      const st = a.silk_type_name || "—";
      g[st] = g[st] || [];
      g[st].push(a);
    }
    return g;
  }, [activities]);

  if (user?.role !== "STATE_ADMIN") {
    return <div className="card p-6" data-testid="master-forbidden-activities">Only State Admins can access master data.</div>;
  }

  return (
    <div data-testid="master-page-activities">
      <div className="mb-5 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-extrabold" data-testid="master-title-activities">Activities</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Granular per-silk-type process steps (e.g. Host Plant Cultivation, Degumming, Weaving), ordered by step number.
          </p>
        </div>
        <button onClick={openCreate} data-testid="master-add-activities" className="btn-primary flex items-center gap-2">
          <Plus size={16} weight="bold" /> Add Activity
        </button>
      </div>

      {showForm && (
        <div className="card p-5 mb-4" data-testid="master-form-activities">
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading font-bold text-lg">{editing ? "Edit Activity" : "Add Activity"}</div>
            <button onClick={resetForm} className="text-sm"><X size={18} /></button>
          </div>
          <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="label-tag block mb-1">Silk Type *</span>
              <select required className="input w-full" value={form.silk_type_id}
                      onChange={(e) => setForm((s) => ({ ...s, silk_type_id: e.target.value }))}
                      data-testid="master-input-activities-silk_type_id">
                <option value="">Select…</option>
                {silkTypes.map((s) => (<option key={s.id} value={s.id}>{s.silk_type_name}</option>))}
              </select>
            </label>
            <label className="block">
              <span className="label-tag block mb-1">Step No. *</span>
              <input required type="number" min={1} className="input w-full" value={form.step_no}
                     onChange={(e) => setForm((s) => ({ ...s, step_no: e.target.value }))}
                     data-testid="master-input-activities-step_no" />
            </label>
            <label className="block">
              <span className="label-tag block mb-1">Activity Name *</span>
              <input required className="input w-full" value={form.activity_name} placeholder="e.g. Host Plant Cultivation"
                     onChange={(e) => setForm((s) => ({ ...s, activity_name: e.target.value }))}
                     data-testid="master-input-activities-activity_name" />
            </label>
            <label className="block sm:col-span-2">
              <span className="label-tag block mb-1">Description</span>
              <textarea className="input w-full" rows={2} value={form.description}
                        onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))}
                        data-testid="master-input-activities-description" />
            </label>
            <div className="sm:col-span-2 flex gap-2 justify-end mt-1">
              <button type="button" onClick={resetForm} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending}
                      className="btn-primary flex items-center gap-2" data-testid="master-form-submit-activities">
                <Check size={16} weight="bold" /> {editing ? "Save Changes" : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="card p-6 text-sm" data-testid="master-empty-activities" style={{ color: "var(--text-muted)" }}>No activities yet.</div>
      ) : (
        Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([silkTypeName, rows]) => (
          <div key={silkTypeName} className="card p-5 mb-4">
            <div className="font-heading font-bold text-lg mb-3">{silkTypeName}</div>
            <table className="seri-table">
              <thead>
                <tr>
                  <th>Step</th><th>Activity</th><th>Description</th><th>Status</th><th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody data-testid={`master-tbody-activities-${silkTypeName}`}>
                {rows.sort((a, b) => a.step_no - b.step_no).map((a) => (
                  <tr key={a.id} data-testid={`master-row-activities-${a.id}`}>
                    <td>{a.step_no}</td>
                    <td className="font-semibold">{a.activity_name}</td>
                    <td className="text-sm" style={{ color: "var(--text-muted)" }}>{a.description || "—"}</td>
                    <td>{a.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>}</td>
                    <td className="text-right">
                      <div className="inline-flex gap-2">
                        <button onClick={() => openEdit(a)} className="btn-secondary btn-sm inline-flex items-center gap-1"
                                data-testid={`master-edit-activities-${a.id}`}>
                          <Pencil size={14} weight="bold" /> Edit
                        </button>
                        <button
                          onClick={() => toggleMut.mutate({ id: a.id, is_active: !a.is_active })}
                          disabled={toggleMut.isPending}
                          className={a.is_active ? "btn-secondary btn-sm" : "btn-primary btn-sm"}
                          data-testid={`master-toggle-activities-${a.id}`}
                        >
                          {a.is_active ? "Deactivate" : "Activate"}
                        </button>
                        {!a.is_active && (
                          <button onClick={() => onDelete(a)} disabled={deleteMut.isPending}
                                  className="btn-secondary btn-sm inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                                  data-testid={`master-delete-activities-${a.id}`}>
                            <Trash size={14} weight="bold" /> Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
}
