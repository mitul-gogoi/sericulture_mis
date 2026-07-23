"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, MagnifyingGlass } from "@phosphor-icons/react";
import { toast } from "sonner";
import { SchemeCard } from "@/components/schemes/SchemeCard";
import { SchemeViewModal } from "@/components/schemes/SchemeViewModal";
import { SchemeFormModal } from "@/components/schemes/SchemeFormModal";
import { EMPTY_SCHEME_FORM, type SchemeFormState } from "@/components/schemes/schemeForm";
import type {
  Scheme, SilkType, Activity, District, AssetType, Caste, Religion, EducationLevel,
} from "@/lib/types";

function errMsg(e: unknown) {
  return fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail);
}

export default function SchemesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Scheme | null>(null);
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<Scheme | null>(null);
  const [form, setForm] = useState<SchemeFormState>(EMPTY_SCHEME_FORM);
  const [q, setQ] = useState("");
  const [showArchived, setShowArchived] = useState(false);

  const { data: schemes = [] } = useQuery<Scheme[]>({
    queryKey: ["schemes-all", showArchived],
    queryFn: async () => (await api.get("/schemes", { params: { all: true, include_archived: showArchived } })).data,
  });
  const { data: silkTypes = [] } = useQuery<SilkType[]>({
    queryKey: ["master-silk-types-all"],
    queryFn: async () => (await api.get("/master/silk-types?all=true")).data,
  });
  const { data: activities = [] } = useQuery<Activity[]>({
    queryKey: ["master-activities-all"],
    queryFn: async () => (await api.get("/master/activities?all=true")).data,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data,
  });
  const { data: assetTypes = [] } = useQuery<AssetType[]>({
    queryKey: ["master-asset-types-all"],
    queryFn: async () => (await api.get("/master/asset-types?all=true")).data,
  });
  const { data: castes = [] } = useQuery<Caste[]>({
    queryKey: ["master-castes-all"],
    queryFn: async () => (await api.get("/master/castes?all=true")).data,
  });
  const { data: religions = [] } = useQuery<Religion[]>({
    queryKey: ["master-religions-all"],
    queryFn: async () => (await api.get("/master/religions?all=true")).data,
  });
  const { data: educationLevels = [] } = useQuery<EducationLevel[]>({
    queryKey: ["master-education-levels-all"],
    queryFn: async () => (await api.get("/master/education-levels?all=true")).data,
  });

  const activityOptions = useMemo(
    () => activities.filter((a) => a.silk_type_id === form.silk_type_id),
    [activities, form.silk_type_id]
  );
  const activityName = (id: string) => activities.find((a) => a.id === id)?.activity_name || id;
  const districtName = (id: string) => districts.find((d) => d.id === id)?.district_name || id;
  const silkTypeName = (id: string) => silkTypes.find((s) => s.id === id)?.silk_type_name || id;
  const assetTypeName = (id?: string | null) => assetTypes.find((t) => t.id === id)?.name || null;
  const casteName = (id: string) => castes.find((c) => c.id === id)?.caste_name || id;
  const religionName = (id: string) => religions.find((r) => r.id === id)?.religion_name || id;
  const educationLevelName = (id: string) => educationLevels.find((e) => e.id === id)?.education_level_name || id;

  const filteredSchemes = useMemo(
    () => q ? schemes.filter((s) => s.scheme_name.toLowerCase().includes(q.toLowerCase())) : schemes,
    [schemes, q]
  );

  const payload = () => ({
    scheme_name: form.scheme_name, description: form.description,
    silk_type_id: form.silk_type_id || null, activity_ids: form.activity_ids,
    total_budget_rs: form.total_budget_rs, disbursement_type: form.disbursement_type,
    support_type: form.support_type, eligible_farmer_type: form.eligible_farmer_type,
    beneficiary_kind: form.beneficiary_kind,
    target_all_districts: form.target_all_districts,
    target_district_ids: form.target_all_districts ? [] : form.target_district_ids,
    target_silk_type_ids: form.target_silk_type_ids,
    target_genders: form.target_genders,
    target_farmer_types: form.target_farmer_types,
    target_caste_ids: form.target_caste_ids,
    target_religion_ids: form.target_religion_ids,
    target_education_level_ids: form.target_education_level_ids,
    target_pwd_only: form.target_pwd_only,
    grants_asset_type_id: form.grants_asset_type_id || null,
  });

  const createMut = useMutation({
    mutationFn: () => api.post("/schemes", payload()),
    onSuccess: () => { toast.success("Scheme created"); reset(); qc.invalidateQueries({ queryKey: ["schemes-all"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const updateMut = useMutation({
    mutationFn: () => { if (!editing) throw new Error("no target"); return api.patch(`/schemes/${editing.id}`, payload()); },
    onSuccess: () => { toast.success("Scheme updated"); reset(); qc.invalidateQueries({ queryKey: ["schemes-all"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/schemes/${id}/active`, { is_active }),
    onSuccess: (_r, v) => { toast.success(`Marked ${v.is_active ? "active" : "inactive"}`); qc.invalidateQueries({ queryKey: ["schemes-all"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => api.patch(`/schemes/${id}/archive`),
    onSuccess: () => { toast.success("Scheme archived"); qc.invalidateQueries({ queryKey: ["schemes-all"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const publishMut = useMutation({
    mutationFn: (id: string) => api.post(`/schemes/${id}/publish`),
    onSuccess: (r) => { toast.success(`Notified ${r.data.notified} recipient(s)`); qc.invalidateQueries({ queryKey: ["schemes-all"] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  function reset() { setEditing(null); setCreating(false); setForm(EMPTY_SCHEME_FORM); }
  function openCreate() { setEditing(null); setForm(EMPTY_SCHEME_FORM); setCreating(true); }
  function openEdit(s: Scheme) {
    setCreating(false);
    setEditing(s);
    setForm({
      scheme_name: s.scheme_name,
      description: s.description || "",
      silk_type_id: s.silk_type_id || "",
      activity_ids: s.activity_ids || [],
      total_budget_rs: s.total_budget_rs || 0,
      disbursement_type: s.disbursement_type || "DBT",
      support_type: s.support_type || "Cash",
      eligible_farmer_type: s.eligible_farmer_type || "All",
      beneficiary_kind: s.beneficiary_kind || "FARMER",
      target_all_districts: s.target_all_districts ?? true,
      target_district_ids: s.target_district_ids || [],
      target_silk_type_ids: s.target_silk_type_ids || [],
      target_genders: s.target_genders || [],
      target_farmer_types: s.target_farmer_types || [],
      target_caste_ids: s.target_caste_ids || [],
      target_religion_ids: s.target_religion_ids || [],
      target_education_level_ids: s.target_education_level_ids || [],
      target_pwd_only: s.target_pwd_only ?? false,
      grants_asset_type_id: s.grants_asset_type_id || "",
    });
  }

  const isSA = user?.role === "STATE_ADMIN";
  const showForm = isSA && (creating || !!editing);

  return (
    <div data-testid="schemes-page">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Schemes</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Government scheme catalogue. {isSA ? "Create, target, publish and archive schemes." : "Read-only view for your district."}
          </p>
        </div>
        {isSA && <button onClick={openCreate} data-testid="schemes-add" className="btn-primary inline-flex items-center gap-2">
          <Plus size={16} weight="bold" />New scheme</button>}
      </div>

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[220px]">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
          <input className="input pl-9 w-full" placeholder="Search schemes by name…" value={q}
                 onChange={(e) => setQ(e.target.value)} data-testid="schemes-search" />
        </div>
        {isSA && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
            Show archived
          </label>
        )}
      </div>

      {showForm && (
        <SchemeFormModal
          editing={editing} form={form} setForm={setForm} onCancel={reset}
          onSubmit={() => (editing ? updateMut.mutate() : createMut.mutate())}
          submitPending={createMut.isPending || updateMut.isPending}
          silkTypes={silkTypes} activityOptions={activityOptions} districts={districts}
          assetTypes={assetTypes} castes={castes} religions={religions} educationLevels={educationLevels}
        />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSchemes.map((s) => (
          <SchemeCard key={s.id} scheme={s} isSA={isSA}
            onView={() => setViewing(s)} onEdit={() => openEdit(s)}
            onToggleActive={() => toggleMut.mutate({ id: s.id, is_active: !s.is_active })} togglePending={toggleMut.isPending}
            onPublish={() => publishMut.mutate(s.id)} publishPending={publishMut.isPending}
            onArchive={() => archiveMut.mutate(s.id)} archivePending={archiveMut.isPending}
          />
        ))}
        {filteredSchemes.length === 0 && <div className="text-sm col-span-full" style={{ color: "var(--text-muted)" }}>No schemes found.</div>}
      </div>

      {viewing && (
        <SchemeViewModal scheme={viewing} onClose={() => setViewing(null)}
          activityName={activityName} districtName={districtName} silkTypeName={silkTypeName}
          assetTypeName={assetTypeName} casteName={casteName} religionName={religionName}
          educationLevelName={educationLevelName}
        />
      )}
    </div>
  );
}
