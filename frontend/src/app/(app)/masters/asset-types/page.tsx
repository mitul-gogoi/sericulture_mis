"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, X, Check, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AssetType, AssetCategory, AssetOwnershipLevel, SilkType } from "@/lib/types";
import { ASSET_CATEGORIES } from "@/lib/types";

const CATEGORY_LABELS: Record<AssetCategory, string> = {
  STRUCTURE: "Structure", SHARED_INFRASTRUCTURE: "Shared Infrastructure", EQUIPMENT: "Equipment",
};
const OWNERSHIP_LABELS: Record<AssetOwnershipLevel, string> = {
  INDIVIDUAL: "Individual farmer", FIG: "FIG (shared)", EITHER: "Individual or FIG",
};

const EMPTY = {
  name: "", category: "EQUIPMENT" as AssetCategory, silk_types: [] as string[],
  ownership_level: "INDIVIDUAL" as AssetOwnershipLevel, useful_life_years: "5", typically_scheme_funded: true,
};

function errMsg(e: unknown) {
  return fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail);
}

export default function AssetTypesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<AssetType | null>(null);
  const [form, setForm] = useState(EMPTY);

  const { data: silkTypes = [] } = useQuery<SilkType[]>({
    queryKey: ["master-silk-types-all"],
    queryFn: async () => (await api.get("/master/silk-types?all=true")).data,
  });
  const { data: assetTypes = [], isLoading } = useQuery<AssetType[]>({
    queryKey: ["master-asset-types"],
    queryFn: async () => (await api.get("/master/asset-types?all=true")).data,
  });

  function resetForm() { setShowForm(false); setEditing(null); setForm(EMPTY); }
  function openCreate() { setEditing(null); setForm(EMPTY); setShowForm(true); }
  function openEdit(a: AssetType) {
    setEditing(a);
    setForm({
      name: a.name, category: a.category, silk_types: a.silk_types,
      ownership_level: a.ownership_level, useful_life_years: String(a.useful_life_years),
      typically_scheme_funded: a.typically_scheme_funded,
    });
    setShowForm(true);
  }

  function toggleSilkType(name: string) {
    setForm((s) => ({
      ...s,
      silk_types: s.silk_types.includes(name) ? s.silk_types.filter((t) => t !== name) : [...s.silk_types, name],
    }));
  }

  function payload() {
    return {
      name: form.name.trim(), category: form.category, silk_types: form.silk_types,
      ownership_level: form.ownership_level, useful_life_years: Number(form.useful_life_years) || 0,
      typically_scheme_funded: form.typically_scheme_funded,
    };
  }

  const createMut = useMutation({
    mutationFn: () => api.post("/master/asset-types", payload()),
    onSuccess: () => { toast.success("Asset type created"); qc.invalidateQueries({ queryKey: ["master-asset-types"] }); resetForm(); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });
  const updateMut = useMutation({
    mutationFn: (id: string) => api.patch(`/master/asset-types/${id}`, payload()),
    onSuccess: () => { toast.success("Asset type updated"); qc.invalidateQueries({ queryKey: ["master-asset-types"] }); resetForm(); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });
  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/master/asset-types/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["master-asset-types"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/master/asset-types/${id}`),
    onSuccess: () => { toast.success("Asset type deleted"); qc.invalidateQueries({ queryKey: ["master-asset-types"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  function onDelete(a: AssetType) {
    if (!window.confirm(`Delete "${a.name}" permanently? This cannot be undone.`)) return;
    deleteMut.mutate(a.id);
  }
  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editing) updateMut.mutate(editing.id);
    else createMut.mutate();
  }

  const grouped = useMemo(() => {
    const g: Record<string, AssetType[]> = {};
    for (const a of assetTypes) {
      g[a.category] = g[a.category] || [];
      g[a.category].push(a);
    }
    return g;
  }, [assetTypes]);

  if (user?.role !== "STATE_ADMIN") {
    return <div className="card p-6" data-testid="master-forbidden-asset-types">Only State Admins can access master data.</div>;
  }

  return (
    <div data-testid="master-page-asset-types">
      <div className="mb-5 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-extrabold" data-testid="master-title-asset-types">Asset Types</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Durable assets tracked for scheme useful-life cooldown (rearing houses, mountages, reeling/spinning
            machines, looms, CFC/CRC, etc.). Host-plant plantations are land, not assets, and low-value consumables
            are deliberately excluded.
          </p>
        </div>
        <button onClick={openCreate} data-testid="master-add-asset-types" className="btn-primary flex items-center gap-2">
          <Plus size={16} weight="bold" /> Add Asset Type
        </button>
      </div>

      {showForm && (
        <div className="card p-5 mb-4" data-testid="master-form-asset-types">
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading font-bold text-lg">{editing ? "Edit Asset Type" : "Add Asset Type"}</div>
            <button onClick={resetForm} className="text-sm"><X size={18} /></button>
          </div>
          <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="label-tag block mb-1">Name *</span>
              <input required className="input w-full" value={form.name} placeholder="e.g. Rearing House"
                     onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))}
                     data-testid="master-input-asset-types-name" />
            </label>
            <label className="block">
              <span className="label-tag block mb-1">Category *</span>
              <select required className="input w-full" value={form.category}
                      onChange={(e) => setForm((s) => ({ ...s, category: e.target.value as AssetCategory }))}
                      data-testid="master-input-asset-types-category">
                {ASSET_CATEGORIES.map((c) => (<option key={c} value={c}>{CATEGORY_LABELS[c]}</option>))}
              </select>
            </label>
            <label className="block">
              <span className="label-tag block mb-1">Ownership *</span>
              <select required className="input w-full" value={form.ownership_level}
                      onChange={(e) => setForm((s) => ({ ...s, ownership_level: e.target.value as AssetOwnershipLevel }))}
                      data-testid="master-input-asset-types-ownership_level">
                {(Object.keys(OWNERSHIP_LABELS) as AssetOwnershipLevel[]).map((o) => (
                  <option key={o} value={o}>{OWNERSHIP_LABELS[o]}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="label-tag block mb-1">Useful Life (years) *</span>
              <input required type="number" min={0} className="input w-full" value={form.useful_life_years}
                     onChange={(e) => setForm((s) => ({ ...s, useful_life_years: e.target.value }))}
                     data-testid="master-input-asset-types-useful_life_years" />
            </label>
            <label className="flex items-center gap-2 mt-6">
              <input type="checkbox" checked={form.typically_scheme_funded}
                     onChange={(e) => setForm((s) => ({ ...s, typically_scheme_funded: e.target.checked }))}
                     data-testid="master-input-asset-types-typically_scheme_funded" />
              <span className="text-sm">Typically scheme-funded</span>
            </label>
            <div className="sm:col-span-2">
              <span className="label-tag block mb-1">Silk Types (leave all unchecked to apply to every silk type)</span>
              <div className="flex flex-wrap gap-3 mt-1">
                {silkTypes.map((st) => (
                  <label key={st.id} className="flex items-center gap-1.5 text-sm">
                    <input type="checkbox" checked={form.silk_types.includes(st.silk_type_name)}
                           onChange={() => toggleSilkType(st.silk_type_name)}
                           data-testid={`master-input-asset-types-silk-type-${st.silk_type_name}`} />
                    {st.silk_type_name}
                  </label>
                ))}
              </div>
            </div>
            <div className="sm:col-span-2 flex gap-2 justify-end mt-1">
              <button type="button" onClick={resetForm} className="btn-secondary">Cancel</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending}
                      className="btn-primary flex items-center gap-2" data-testid="master-form-submit-asset-types">
                <Check size={16} weight="bold" /> {editing ? "Save Changes" : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="card p-6 text-sm" data-testid="master-empty-asset-types" style={{ color: "var(--text-muted)" }}>No asset types yet.</div>
      ) : (
        ASSET_CATEGORIES.filter((c) => grouped[c]?.length).map((category) => (
          <div key={category} className="card p-5 mb-4">
            <div className="font-heading font-bold text-lg mb-3">{CATEGORY_LABELS[category]}</div>
            <table className="seri-table">
              <thead>
                <tr>
                  <th>Name</th><th>Silk Types</th><th>Ownership</th><th>Useful Life</th>
                  <th>Scheme-funded</th><th>Status</th><th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody data-testid={`master-tbody-asset-types-${category}`}>
                {grouped[category].sort((a, b) => a.name.localeCompare(b.name)).map((a) => (
                  <tr key={a.id} data-testid={`master-row-asset-types-${a.id}`}>
                    <td className="font-semibold">{a.name}</td>
                    <td className="text-sm" style={{ color: "var(--text-muted)" }}>
                      {a.silk_types.length ? a.silk_types.join(", ") : "All"}
                    </td>
                    <td>{OWNERSHIP_LABELS[a.ownership_level]}</td>
                    <td>{a.useful_life_years} yrs</td>
                    <td>{a.typically_scheme_funded ? "Yes" : "No"}</td>
                    <td>{a.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>}</td>
                    <td className="text-right">
                      <div className="inline-flex gap-2">
                        <button onClick={() => openEdit(a)} className="btn-secondary btn-sm inline-flex items-center gap-1"
                                data-testid={`master-edit-asset-types-${a.id}`}>
                          <Pencil size={14} weight="bold" /> Edit
                        </button>
                        <button
                          onClick={() => toggleMut.mutate({ id: a.id, is_active: !a.is_active })}
                          disabled={toggleMut.isPending}
                          className={a.is_active ? "btn-secondary btn-sm" : "btn-primary btn-sm"}
                          data-testid={`master-toggle-asset-types-${a.id}`}
                        >
                          {a.is_active ? "Deactivate" : "Activate"}
                        </button>
                        {!a.is_active && (
                          <button onClick={() => onDelete(a)} disabled={deleteMut.isPending}
                                  className="btn-secondary btn-sm inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                                  data-testid={`master-delete-asset-types-${a.id}`}>
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
