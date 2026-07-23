"use client";
import { useMemo, useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { SilkType, Activity, Product, SilkTypeActivityProduct, StapRole, InputSourceType, InputSourceCategory } from "@/lib/types";

export default function MapActivityToProductPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [silkTypeId, setSilkTypeId] = useState("");
  const [activityId, setActivityId] = useState("");
  const [inputSelected, setInputSelected] = useState<Set<string>>(new Set());
  const [outputSelected, setOutputSelected] = useState<Set<string>>(new Set());
  const [inputGroups, setInputGroups] = useState<Record<string, string>>({});
  const [inputSourceTypes, setInputSourceTypes] = useState<Record<string, Set<string>>>({});
  const [inputCategories, setInputCategories] = useState<Record<string, string>>({});

  const { data: silkTypes = [] } = useQuery<SilkType[]>({
    queryKey: ["master-silk-types-all"],
    queryFn: async () => (await api.get("/master/silk-types?all=true")).data,
  });
  const { data: activities = [] } = useQuery<Activity[]>({
    queryKey: ["master-activities-all"],
    queryFn: async () => (await api.get("/master/activities?all=true")).data,
  });
  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ["master-products-all"],
    queryFn: async () => (await api.get("/master/products?all=true")).data,
  });
  const { data: mappings = [], isLoading } = useQuery<SilkTypeActivityProduct[]>({
    queryKey: ["master-stap"],
    queryFn: async () => (await api.get("/master/silk-type-activity-products?all=true")).data,
  });
  const { data: sourceTypes = [] } = useQuery<InputSourceType[]>({
    queryKey: ["master-input-source-types"],
    queryFn: async () => (await api.get("/master/input-source-types")).data,
  });
  const { data: sourceCategories = [] } = useQuery<InputSourceCategory[]>({
    queryKey: ["master-input-source-categories-all"],
    queryFn: async () => (await api.get("/master/input-source-categories?all=true")).data,
  });

  const activityOptions = useMemo(
    () => activities.filter((a) => a.silk_type_id === silkTypeId).sort((a, b) => a.step_no - b.step_no),
    [activities, silkTypeId]
  );
  // A product is eligible for this silk type's activity if it's generic (no silk type) or matches.
  const productOptions = useMemo(
    () => products.filter((p) => !p.silk_type_id || p.silk_type_id === silkTypeId)
                   .sort((a, b) => a.product_name.localeCompare(b.product_name)),
    [products, silkTypeId]
  );

  const currentMappings = useMemo(
    () => mappings.filter((m) => m.silk_type_id === silkTypeId && m.activity_id === activityId),
    [mappings, silkTypeId, activityId]
  );

  useEffect(() => {
    const inputRows = currentMappings.filter((m) => m.role === "INPUT");
    setInputSelected(new Set(inputRows.map((m) => m.product_id)));
    setOutputSelected(new Set(currentMappings.filter((m) => m.role === "OUTPUT").map((m) => m.product_id)));
    setInputGroups(Object.fromEntries(inputRows.map((m) => [m.product_id, m.input_group || ""])));
    setInputSourceTypes(Object.fromEntries(inputRows.map((m) => [m.product_id, new Set(m.source_type_ids || [])])));
    setInputCategories(Object.fromEntries(inputRows.map((m) => [m.product_id, m.input_source_category_id || ""])));
  }, [silkTypeId, activityId]); // eslint-disable-line react-hooks/exhaustive-deps

  const saveMut = useMutation({
    mutationFn: async () => {
      // Only skip re-sending an output that's already an ACTIVE mapping — an inactive one must
      // still be sent so the backend's upsert can reactivate it (see create_stap_batch).
      const existingActiveOutputIds = new Set(currentMappings.filter((m) => m.role === "OUTPUT" && m.is_active).map((m) => m.product_id));
      const items: { product_id: string; role: StapRole; input_group?: string | null; input_source_category_id?: string | null; source_type_ids?: string[] }[] = [];
      // Every currently-checked input is (re)sent — this covers brand-new mappings AND edits
      // (group label / category / source types) to already-saved ones, which the backend upserts.
      for (const pid of inputSelected) {
        items.push({
          product_id: pid, role: "INPUT",
          input_group: inputGroups[pid]?.trim() || null,
          input_source_category_id: inputCategories[pid] || null,
          source_type_ids: Array.from(inputSourceTypes[pid] || []),
        });
      }
      for (const pid of outputSelected) if (!existingActiveOutputIds.has(pid)) items.push({ product_id: pid, role: "OUTPUT" });

      // Any previously-active mapping whose checkbox is no longer ticked must be explicitly
      // deactivated — the batch endpoint only upserts what's present, it never infers removals
      // from absence, so unchecking a box was previously a silent no-op.
      const toDeactivate = currentMappings.filter((m) => m.is_active && (
        m.role === "INPUT" ? !inputSelected.has(m.product_id) : !outputSelected.has(m.product_id)
      ));

      if (items.length === 0 && toDeactivate.length === 0) return null;

      let created = 0, updated = 0;
      if (items.length > 0) {
        const res = await api.post("/master/silk-type-activity-products/batch", { silk_type_id: silkTypeId, activity_id: activityId, items });
        created = res.data.created; updated = res.data.updated;
      }
      if (toDeactivate.length > 0) {
        await Promise.all(toDeactivate.map((m) => api.patch(`/master/silk-type-activity-products/${m.id}/active`, { is_active: false })));
      }
      return { created, updated, deactivated: toDeactivate.length };
    },
    onSuccess: (result) => {
      if (!result) { toast.info("Nothing to save"); return; }
      const { created, updated, deactivated } = result;
      const parts: string[] = [];
      if (created) parts.push(`${created} new`);
      if (updated) parts.push(`${updated} updated`);
      if (deactivated) parts.push(`${deactivated} removed`);
      toast.success(parts.length ? parts.join(", ") : "Saved");
      qc.invalidateQueries({ queryKey: ["master-stap"] });
    },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      api.patch(`/master/silk-type-activity-products/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["master-stap"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/master/silk-type-activity-products/${id}`),
    onSuccess: () => { toast.success("Mapping deleted"); qc.invalidateQueries({ queryKey: ["master-stap"] }); },
    onError: (e: unknown) => toast.error(fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)),
  });

  function onDelete(m: SilkTypeActivityProduct) {
    if (!window.confirm(`Delete "${m.silk_type_name} → ${m.activity_name} → ${m.product_name} (${m.role})" permanently? This cannot be undone.`)) return;
    deleteMut.mutate(m.id);
  }

  function toggle(set: Set<string>, setFn: (s: Set<string>) => void, id: string, checked: boolean) {
    const next = new Set(set);
    if (checked) next.add(id); else next.delete(id);
    setFn(next);
  }

  function toggleSourceType(productId: string, sourceTypeId: string, checked: boolean) {
    setInputSourceTypes((s) => {
      const next = new Set(s[productId] || []);
      if (checked) next.add(sourceTypeId); else next.delete(sourceTypeId);
      return { ...s, [productId]: next };
    });
  }

  function toggleInputProduct(p: Product, checked: boolean) {
    toggle(inputSelected, setInputSelected, p.id, checked);
    if (checked && !(p.id in inputCategories)) {
      setInputCategories((s) => ({ ...s, [p.id]: p.default_source_category_id || "" }));
    }
  }

  function changeInputCategory(productId: string, categoryId: string) {
    setInputCategories((s) => ({ ...s, [productId]: categoryId }));
    // Drop any already-checked source types that no longer match the new category.
    setInputSourceTypes((s) => {
      const current = s[productId];
      if (!current || !categoryId) return s;
      const validIds = new Set(sourceTypes.filter((st) => st.category_id === categoryId).map((st) => st.id));
      const next = new Set(Array.from(current).filter((id) => validIds.has(id)));
      return { ...s, [productId]: next };
    });
  }

  function onSave() {
    saveMut.mutate();
  }

  const grouped = useMemo(() => {
    const g: Record<string, SilkTypeActivityProduct[]> = {};
    for (const m of mappings) {
      const st = m.silk_type_name;
      g[st] = g[st] || [];
      g[st].push(m);
    }
    return g;
  }, [mappings]);

  if (user?.role !== "STATE_ADMIN") {
    return <div className="card p-6" data-testid="master-forbidden-stap">Only State Admins can access master data.</div>;
  }

  return (
    <div data-testid="master-page-stap">
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">Map Activity to Product</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Pick an activity, then select one or many products as its Inputs and one or many products as its Outputs (including by-products/wastes).
        </p>
      </div>

      <div className="card p-5 mb-4">
        <label className="block mb-4 max-w-xs">
          <span className="label-tag block mb-1">Silk Type *</span>
          <select value={silkTypeId} onChange={(e) => { setSilkTypeId(e.target.value); setActivityId(""); }}
                  className="input w-full" data-testid="stap-input-silk-type">
            <option value="">Select…</option>
            {silkTypes.map((s) => (<option key={s.id} value={s.id}>{s.silk_type_name}</option>))}
          </select>
        </label>

        {silkTypeId && (
          <div className="grid gap-4" style={{ gridTemplateColumns: "260px 1fr 1fr" }}>
            {/* Activity list, left */}
            <div>
              <div className="label-tag mb-1">Activity</div>
              <div className="max-h-96 overflow-y-auto border rounded" style={{ borderColor: "var(--border)" }} data-testid="stap-activity-list">
                {activityOptions.map((a) => (
                  <button
                    key={a.id}
                    type="button"
                    onClick={() => setActivityId(a.id)}
                    className="block w-full text-left px-3 py-2 text-sm border-b last:border-b-0"
                    style={{
                      borderColor: "var(--border)",
                      background: a.id === activityId ? "var(--primary)" : "transparent",
                      color: a.id === activityId ? "white" : "inherit",
                    }}
                    data-testid={`stap-activity-option-${a.id}`}
                  >
                    Step {a.step_no}: {a.activity_name}
                  </button>
                ))}
              </div>
            </div>

            {/* Input products, middle */}
            <div>
              <div className="label-tag mb-1">Input Products</div>
              <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                Give alternative inputs (e.g. Castor Leaf / Kesseru Leaf) the same group label to cluster them for the FIG President.
              </p>
              <div className="max-h-96 overflow-y-auto border rounded p-2 space-y-1" style={{ borderColor: "var(--border)" }} data-testid="stap-input-list">
                {!activityId ? (
                  <p className="text-sm p-2" style={{ color: "var(--text-muted)" }}>Select an activity first.</p>
                ) : productOptions.map((p) => (
                  <div key={p.id} className="text-sm">
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2 flex-1">
                        <input type="checkbox" checked={inputSelected.has(p.id)}
                               onChange={(e) => toggleInputProduct(p, e.target.checked)} />
                        {p.product_name} <span style={{ color: "var(--text-muted)" }}>({p.unit_of_measure})</span>
                      </label>
                      {inputSelected.has(p.id) && (
                        <input
                          type="text"
                          value={inputGroups[p.id] ?? ""}
                          onChange={(e) => setInputGroups((s) => ({ ...s, [p.id]: e.target.value }))}
                          placeholder="Group label (optional)"
                          className="input text-xs"
                          style={{ maxWidth: 140 }}
                          data-testid={`stap-input-group-${p.id}`}
                        />
                      )}
                    </div>
                    {inputSelected.has(p.id) && (
                      <div className="ml-6 mt-1">
                        <select
                          value={inputCategories[p.id] ?? ""}
                          onChange={(e) => changeInputCategory(p.id, e.target.value)}
                          className="input text-xs"
                          style={{ maxWidth: 200 }}
                          data-testid={`stap-input-category-${p.id}`}
                        >
                          <option value="">No category (show all source types)</option>
                          {sourceCategories.map((c) => (<option key={c.id} value={c.id}>{c.category_name}</option>))}
                        </select>
                        <div className="flex flex-wrap gap-2 mt-1" data-testid={`stap-input-sources-${p.id}`}>
                          {sourceTypes
                            .filter((st) => !inputCategories[p.id] || st.category_id === inputCategories[p.id])
                            .map((st) => (
                              <label key={st.id} className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                                <input type="checkbox" checked={inputSourceTypes[p.id]?.has(st.id) || false}
                                       onChange={(e) => toggleSourceType(p.id, st.id, e.target.checked)} />
                                {st.source_name}
                              </label>
                            ))}
                          {sourceTypes.length === 0 && <span className="text-xs" style={{ color: "var(--text-muted)" }}>No source types configured yet.</span>}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Output products, right */}
            <div>
              <div className="label-tag mb-1">Output Products</div>
              <div className="max-h-96 overflow-y-auto border rounded p-2 space-y-1" style={{ borderColor: "var(--border)" }} data-testid="stap-output-list">
                {!activityId ? (
                  <p className="text-sm p-2" style={{ color: "var(--text-muted)" }}>Select an activity first.</p>
                ) : productOptions.map((p) => (
                  <label key={p.id} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={outputSelected.has(p.id)}
                           onChange={(e) => toggle(outputSelected, setOutputSelected, p.id, e.target.checked)} />
                    {p.product_name} <span style={{ color: "var(--text-muted)" }}>({p.unit_of_measure})</span>
                    {p.is_byproduct && <span className="badge badge-muted" style={{ fontSize: 10 }}>byproduct</span>}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {activityId && (
          <div className="flex justify-end mt-4">
            <button onClick={onSave} disabled={saveMut.isPending}
                    className="btn-primary flex items-center gap-2" data-testid="stap-save-checklist">
              <Check size={16} weight="bold" /> Save Mappings
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>
      ) : Object.keys(grouped).length === 0 ? (
        <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>No mappings yet.</div>
      ) : (
        Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([silkTypeName, rows]) => (
          <div key={silkTypeName} className="card p-5 mb-4" data-testid={`stap-group-${silkTypeName}`}>
            <div className="font-heading font-bold text-lg mb-3">{silkTypeName}</div>
            <table className="seri-table">
              <thead>
                <tr>
                  <th>Activity</th><th>Role</th><th>Product</th><th>Unit</th><th>Group</th><th>Category</th><th>Source Types</th><th>Byproduct</th><th>Status</th><th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((m) => (
                  <tr key={m.id} data-testid={`stap-row-${m.id}`}>
                    <td>{m.activity_name}</td>
                    <td>
                      <span className={m.role === "INPUT" ? "badge badge-muted" : "badge badge-success"}>{m.role}</span>
                    </td>
                    <td>{m.product_name}</td>
                    <td>{m.unit_of_measure}</td>
                    <td>{m.input_group || <span style={{ color: "var(--text-muted)" }}>—</span>}</td>
                    <td>
                      {m.role === "INPUT"
                        ? (m.input_source_category_name || <span style={{ color: "var(--text-muted)" }}>—</span>)
                        : <span style={{ color: "var(--text-muted)" }}>—</span>}
                    </td>
                    <td>
                      {m.role === "INPUT"
                        ? (m.source_type_names?.length ? m.source_type_names.join(", ") : <span style={{ color: "var(--text-muted)" }}>Any (unconfigured)</span>)
                        : <span style={{ color: "var(--text-muted)" }}>—</span>}
                    </td>
                    <td>{m.is_byproduct ? "Yes" : "No"}</td>
                    <td>{m.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>}</td>
                    <td className="text-right">
                      <div className="inline-flex gap-2">
                        <button
                          onClick={() => toggleMut.mutate({ id: m.id, is_active: !m.is_active })}
                          disabled={toggleMut.isPending}
                          className={m.is_active ? "btn-secondary btn-sm" : "btn-primary btn-sm"}
                          data-testid={`stap-toggle-${m.id}`}
                        >
                          {m.is_active ? "Deactivate" : "Activate"}
                        </button>
                        {!m.is_active && (
                          <button
                            onClick={() => onDelete(m)}
                            disabled={deleteMut.isPending}
                            className="btn-secondary btn-sm inline-flex items-center gap-1"
                            style={{ color: "var(--error)" }}
                            data-testid={`stap-delete-${m.id}`}
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
          </div>
        ))
      )}
    </div>
  );
}
