"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, X, Check, CircleDashed, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export type FieldType = "text" | "number" | "select" | "checkbox";

export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  placeholder?: string;
  // For select fields — a plain list, or a function of the current form values (for cascading selects)
  options?: { value: string; label: string }[] | ((form: Record<string, string>) => { value: string; label: string }[]);
  // For select fields — adds an "Other…" option that reveals a free-text input for a custom value
  allowOther?: boolean;
}

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

export interface MasterCrudProps<T extends { id: string; is_active: boolean }> {
  title: string;
  description: string;
  endpoint: string; // e.g. "sectors" -> /master/sectors
  queryKey: string; // e.g. "master-sectors"
  columns: Column<T>[];
  fields: FormField[];
  buildPayload: (form: Record<string, string>) => Record<string, unknown>;
  toForm: (row: T) => Record<string, string>;
  emptyForm: Record<string, string>;
  searchOn?: (keyof T)[]; // fields to filter locally
  addLabel?: string;
}

export function MasterCrud<T extends { id: string; is_active: boolean }>(props: MasterCrudProps<T>) {
  const { title, description, endpoint, queryKey, columns, fields, buildPayload, toForm, emptyForm, searchOn = [], addLabel } = props;
  const { user } = useAuth();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [form, setForm] = useState<Record<string, string>>(emptyForm);
  const [otherMode, setOtherMode] = useState<Record<string, boolean>>({});
  const [search, setSearch] = useState("");

  const { data: rows = [], isLoading } = useQuery<T[]>({
    queryKey: [queryKey],
    queryFn: async () => (await api.get(`/master/${endpoint}?all=true`)).data,
  });

  const createMut = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.post(`/master/${endpoint}`, payload),
    onSuccess: () => { toast.success(`${title} created`); qc.invalidateQueries({ queryKey: [queryKey] }); resetForm(); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => api.patch(`/master/${endpoint}/${id}`, payload),
    onSuccess: () => { toast.success(`${title} updated`); qc.invalidateQueries({ queryKey: [queryKey] }); resetForm(); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/master/${endpoint}/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: [queryKey] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const deleteMut = useMutation({
    mutationFn: ({ id, cascade }: { id: string; cascade?: boolean }) =>
      api.delete(`/master/${endpoint}/${id}`, cascade ? { params: { cascade_inactive_mappings: true } } : undefined),
    onSuccess: () => { toast.success(`${title.replace(/s$/, "")} deleted`); qc.invalidateQueries({ queryKey: [queryKey] }); },
    onError: (e: unknown, vars) => {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg = fmtErr(detail);
      // Product deletes may offer a narrow cascade for inactive Map Activity to Product
      // mappings only — this string check is a no-op for every other master entity, since
      // their error messages never contain this phrase.
      if (typeof detail === "string" && detail.includes("cascade_inactive_mappings=true")) {
        if (window.confirm(`${msg}\n\nDelete the inactive mapping(s) too and proceed?`)) {
          deleteMut.mutate({ id: vars.id, cascade: true });
          return;
        }
      }
      toast.error(msg);
    },
  });

  function onDelete(row: T) {
    const name = searchOn.length > 0 ? String(row[searchOn[0]] ?? row.id) : row.id;
    if (!window.confirm(`Delete "${name}" permanently? This cannot be undone.`)) return;
    deleteMut.mutate({ id: row.id });
  }

  function deriveOtherMode(nextForm: Record<string, string>): Record<string, boolean> {
    const next: Record<string, boolean> = {};
    for (const f of fields) {
      if (!f.allowOther) continue;
      const opts = typeof f.options === "function" ? f.options(nextForm) : f.options ?? [];
      const value = nextForm[f.name] ?? "";
      next[f.name] = value !== "" && !opts.some((o) => o.value === value);
    }
    return next;
  }

  function resetForm() {
    setShowForm(false);
    setEditing(null);
    setForm(emptyForm);
    setOtherMode({});
  }

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setOtherMode({});
    setShowForm(true);
  }

  function openEdit(row: T) {
    setEditing(row);
    const nextForm = { ...emptyForm, ...toForm(row) };
    setForm(nextForm);
    setOtherMode(deriveOtherMode(nextForm));
    setShowForm(true);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = buildPayload(form);
    if (editing) updateMut.mutate({ id: editing.id, payload });
    else createMut.mutate(payload);
  }

  const filtered = useMemo(() => {
    if (!search.trim()) return rows;
    const s = search.trim().toLowerCase();
    return rows.filter((r) =>
      searchOn.some((k) => {
        const v = r[k];
        return typeof v === "string" && v.toLowerCase().includes(s);
      })
    );
  }, [rows, search, searchOn]);

  if (user?.role !== "STATE_ADMIN") {
    return <div className="card p-6" data-testid={`master-forbidden-${endpoint}`}>Only State Admins can access master data.</div>;
  }

  return (
    <div data-testid={`master-page-${endpoint}`}>
      <div className="mb-5 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-extrabold" data-testid={`master-title-${endpoint}`}>{title}</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{description}</p>
        </div>
        <button onClick={openCreate} data-testid={`master-add-${endpoint}`} className="btn-primary flex items-center gap-2">
          <Plus size={16} weight="bold" /> {addLabel || `Add ${title.replace(/s$/, "")}`}
        </button>
      </div>

      {searchOn.length > 0 && (
        <div className="mb-3">
          <input
            type="text"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid={`master-search-${endpoint}`}
            className="input w-full max-w-xs"
          />
        </div>
      )}

      {showForm && (
        <div className="card p-5 mb-4" data-testid={`master-form-${endpoint}`}>
          <div className="flex items-center justify-between mb-3">
            <div className="font-heading font-bold text-lg">{editing ? `Edit ${title.replace(/s$/, "")}` : `Add ${title.replace(/s$/, "")}`}</div>
            <button onClick={resetForm} className="text-sm" data-testid={`master-form-close-${endpoint}`}>
              <X size={18} />
            </button>
          </div>
          <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2">
            {fields.map((f) => (
              <label key={f.name} className={f.type === "checkbox" ? "flex items-center gap-2" : "block"}>
                {f.type === "checkbox" ? (
                  <>
                    <input
                      type="checkbox"
                      checked={form[f.name] === "true"}
                      onChange={(e) => setForm((s) => ({ ...s, [f.name]: e.target.checked ? "true" : "false" }))}
                      data-testid={`master-input-${endpoint}-${f.name}`}
                    />
                    <span className="label-tag">{f.label}{f.required && " *"}</span>
                  </>
                ) : (
                  <>
                    <span className="label-tag block mb-1">{f.label}{f.required && " *"}</span>
                    {f.type === "text" || f.type === "number" ? (
                      <input
                        type={f.type}
                        value={form[f.name] ?? ""}
                        onChange={(e) => setForm((s) => ({ ...s, [f.name]: e.target.value }))}
                        placeholder={f.placeholder}
                        required={f.required}
                        className="input w-full"
                        data-testid={`master-input-${endpoint}-${f.name}`}
                      />
                    ) : f.allowOther ? (
                      <div className="space-y-1.5">
                        <select
                          value={otherMode[f.name] ? "__other__" : form[f.name] ?? ""}
                          onChange={(e) => {
                            if (e.target.value === "__other__") {
                              setOtherMode((s) => ({ ...s, [f.name]: true }));
                              setForm((s) => ({ ...s, [f.name]: "" }));
                            } else {
                              setOtherMode((s) => ({ ...s, [f.name]: false }));
                              setForm((s) => ({ ...s, [f.name]: e.target.value }));
                            }
                          }}
                          required={f.required && !otherMode[f.name]}
                          className="input w-full"
                          data-testid={`master-input-${endpoint}-${f.name}`}
                        >
                          <option value="">Select…</option>
                          {(typeof f.options === "function" ? f.options(form) : f.options ?? []).map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                          <option value="__other__">Other…</option>
                        </select>
                        {otherMode[f.name] && (
                          <input
                            type="text"
                            value={form[f.name] ?? ""}
                            onChange={(e) => setForm((s) => ({ ...s, [f.name]: e.target.value }))}
                            placeholder={f.placeholder || "Enter custom value"}
                            required={f.required}
                            className="input w-full"
                            data-testid={`master-input-${endpoint}-${f.name}-other`}
                          />
                        )}
                      </div>
                    ) : (
                      <select
                        value={form[f.name] ?? ""}
                        onChange={(e) => setForm((s) => ({ ...s, [f.name]: e.target.value }))}
                        required={f.required}
                        className="input w-full"
                        data-testid={`master-input-${endpoint}-${f.name}`}
                      >
                        <option value="">Select…</option>
                        {(typeof f.options === "function" ? f.options(form) : f.options ?? []).map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    )}
                  </>
                )}
              </label>
            ))}
            <div className="sm:col-span-2 flex gap-2 justify-end mt-1">
              <button type="button" onClick={resetForm} className="btn-secondary" data-testid={`master-form-cancel-${endpoint}`}>Cancel</button>
              <button type="submit" disabled={createMut.isPending || updateMut.isPending}
                className="btn-primary flex items-center gap-2" data-testid={`master-form-submit-${endpoint}`}>
                <Check size={16} weight="bold" /> {editing ? "Save Changes" : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="p-6 flex items-center gap-2 text-sm" style={{ color: "var(--text-muted)" }}>
            <CircleDashed size={16} className="animate-spin" /> Loading…
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-6 text-sm" style={{ color: "var(--text-muted)" }} data-testid={`master-empty-${endpoint}`}>No records yet.</div>
        ) : (
          <table className="seri-table">
            <thead>
              <tr>
                {columns.map((c) => (<th key={c.key} className={c.className}>{c.label}</th>))}
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody data-testid={`master-tbody-${endpoint}`}>
              {filtered.map((row) => (
                <tr key={row.id} data-testid={`master-row-${endpoint}-${row.id}`}>
                  {columns.map((c) => (
                    <td key={c.key} className={c.className}>
                      {c.render ? c.render(row) : String((row as unknown as Record<string, unknown>)[c.key] ?? "—")}
                    </td>
                  ))}
                  <td>
                    {row.is_active
                      ? <span className="badge badge-success">Active</span>
                      : <span className="badge badge-muted">Inactive</span>}
                  </td>
                  <td className="text-right">
                    <div className="inline-flex gap-2">
                      <button onClick={() => openEdit(row)} className="btn-secondary btn-sm inline-flex items-center gap-1"
                        data-testid={`master-edit-${endpoint}-${row.id}`}>
                        <Pencil size={14} weight="bold" /> Edit
                      </button>
                      <button
                        onClick={() => toggleMut.mutate({ id: row.id, is_active: !row.is_active })}
                        disabled={toggleMut.isPending}
                        className={row.is_active ? "btn-secondary btn-sm" : "btn-primary btn-sm"}
                        data-testid={`master-toggle-${endpoint}-${row.id}`}
                      >
                        {row.is_active ? "Deactivate" : "Activate"}
                      </button>
                      {!row.is_active && (
                        <button
                          onClick={() => onDelete(row)}
                          disabled={deleteMut.isPending}
                          className="btn-secondary btn-sm inline-flex items-center gap-1"
                          style={{ color: "var(--error)" }}
                          data-testid={`master-delete-${endpoint}-${row.id}`}
                        >
                          <Trash size={14} weight="bold" /> Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
