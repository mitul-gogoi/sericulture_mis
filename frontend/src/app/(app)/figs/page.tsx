"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";
import { Plus, ChartLineUp } from "@phosphor-icons/react";
import { toast } from "sonner";
import { FigRow } from "@/components/figs/FigRow";
import { FigFilterPanel, type FigReportFilters } from "@/components/figs/FigFilterPanel";
import { FigRegisterModal, type FigCreateForm } from "@/components/figs/FigRegisterModal";
import { FigDocumentsStep, type FigDocuments } from "@/components/figs/FigDocumentsStep";
import { FigDetailModal } from "@/components/figs/FigDetailModal";
import { type FigEditFormState } from "@/components/figs/FigEditForm";
import { type PresForm } from "@/components/figs/FigPresidentPanel";
import { type AssetRow } from "@/components/AssetRowsEditor";
import type { Fig, FigDetail, Farmer, District, SericultureCircle, SubdivisionCdc, SilkTypeActivityProduct, FigSettings, AssetType, AssetInstance } from "@/lib/types";

const MultiSeriesTrendChart = dynamic(() => import("../dashboard/charts").then((m) => m.MultiSeriesTrendChart), { ssr: false });

const emptyCreateForm = (): FigCreateForm => ({
  fig_name: "", stap_id: "", seri_circle_id: "", district_id: "", formation_date: "", meeting_venue: "",
  village_name: "", panchayat_name: "", post_office: "", pin_code: "", address: "",
  member_ids: [], president_farmer_id: "", assets: [],
});

const emptyReportFilters = (): FigReportFilters => ({
  stap_id: "", district_id: "", seri_circle_id: "", formation_date_from: "", formation_date_to: "", is_active: "",
});

function filterParamsFrom(f: FigReportFilters, q: string) {
  const p: Record<string, string> = {};
  if (q) p.q = q;
  if (f.stap_id) p.stap_id = f.stap_id;
  if (f.district_id) p.district_id = f.district_id;
  if (f.seri_circle_id) p.seri_circle_id = f.seri_circle_id;
  if (f.formation_date_from) p.formation_date_from = f.formation_date_from;
  if (f.formation_date_to) p.formation_date_to = f.formation_date_to;
  if (f.is_active) p.is_active = f.is_active;
  return p;
}

export default function FIGsPage() {
  const { user, activeDistrictId } = useAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const canRegisterFig = user?.role === "DISTRICT_ADMIN";
  const canEditDetails = user?.role === "DISTRICT_ADMIN";
  const canToggleActive = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN";
  const canManageMembership = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN";

  const [open, setOpen] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [memberFarmer, setMemberFarmer] = useState("");
  const [presForm, setPresForm] = useState<PresForm>({ farmer_id: "" });
  const [editingFig, setEditingFig] = useState(false);
  const [editForm, setEditForm] = useState<FigEditFormState | null>(null);
  // Step 2 of registration: set once the FIG exists, so the upload folder can be named
  // after its real code. Null means we're still on step 1.
  const [newFig, setNewFig] = useState<{ id: string; fig_code: string; district_id: string; seri_circle_id: string; fig_name: string } | null>(null);
  const [newFigDocs, setNewFigDocs] = useState<FigDocuments>({ minutes_path: null, group_photo_path: null });
  const [editNewAssets, setEditNewAssets] = useState<AssetRow[]>([]);
  const [form, setForm] = useState<FigCreateForm>(emptyCreateForm());
  // Location fields the DA has hand-edited — the register modal's autofill-from-members
  // effect leaves these alone so a manual correction survives a member-list change.
  const [touchedLocation, setTouchedLocation] = useState<string[]>([]);

  // Filter panel — live-edited state, only takes effect on Search.
  const [qInput, setQInput] = useState("");
  const [reportFilters, setReportFilters] = useState(emptyReportFilters());
  const [appliedQ, setAppliedQ] = useState("");
  const [appliedFilters, setAppliedFilters] = useState(emptyReportFilters());
  const [reportPage, setReportPage] = useState(1);
  const [reportPageSize, setReportPageSize] = useState(20);
  const [trendFy, setTrendFy] = useState("");
  const [justFocused, setJustFocused] = useState(false);

  useEffect(() => {
    if (searchParams.get("focus") !== "onboarding-trend") return;
    const el = document.getElementById("onboarding-trend");
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setJustFocused(true);
    const t = setTimeout(() => setJustFocused(false), 2000);
    return () => clearTimeout(t);
  }, [searchParams]);

  const { data: reportData } = useQuery<{ items: Fig[]; total: number }>({
    queryKey: ["figs-report", appliedQ, appliedFilters, reportPage, reportPageSize],
    queryFn: async () => (await api.get("/figs", {
      params: { ...filterParamsFrom(appliedFilters, appliedQ), page: reportPage, page_size: reportPageSize },
    })).data,
  });
  const { data: trend } = useQuery<{ months: string[]; figs_monthly: number[] }>({
    queryKey: ["figs-onboarding-trend", trendFy],
    queryFn: async () => (await api.get("/reports/onboarding-trend", { params: trendFy ? { fiscal_year: trendFy } : {} })).data,
  });

  const figsRows = reportData?.items ?? [];
  const total = reportData?.total ?? 0;
  const showingFrom = total === 0 ? 0 : (reportPage - 1) * reportPageSize + 1;
  const showingTo = Math.min(reportPage * reportPageSize, total);
  const chartData = (trend?.months ?? []).map((m, i) => ({ label: m, FIGs: trend?.figs_monthly[i] ?? 0 }));

  const { data: staps = [] } = useQuery<SilkTypeActivityProduct[]>({ queryKey: ["staps", "output"], queryFn: async () => (await api.get("/master/silk-type-activity-products?role=OUTPUT")).data });
  const { data: figSettings } = useQuery<FigSettings>({ queryKey: ["fig-settings"], queryFn: async () => (await api.get("/master/fig-settings")).data });
  const minMembers = figSettings?.min_members ?? 1;
  const { data: districts = [] } = useQuery<District[]>({ queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data });
  const { data: allCircles = [] } = useQuery<SericultureCircle[]>({ queryKey: ["circles-all-figs"], queryFn: async () => (await api.get("/master/sericulture-circles")).data });
  const { data: subdivisionCdcs = [] } = useQuery<SubdivisionCdc[]>({ queryKey: ["subdivision-cdc-all"], queryFn: async () => (await api.get("/master/subdivision-cdc")).data });
  const { data: assetTypes = [] } = useQuery<AssetType[]>({ queryKey: ["master-asset-types-all"], queryFn: async () => (await api.get("/master/asset-types?all=true")).data });
  const { data: circles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-fig", form.district_id || activeDistrictId],
    queryFn: async () => {
      const did = form.district_id || activeDistrictId;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: !!(form.district_id || activeDistrictId),
  });
  const { data: filterCircles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-filter-figs", reportFilters.district_id || activeDistrictId],
    queryFn: async () => {
      const did = reportFilters.district_id || activeDistrictId;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: user?.role !== "FIG_PRESIDENT" && !!(reportFilters.district_id || activeDistrictId),
  });
  const { data: unassignedFarmers = [] } = useQuery<Farmer[]>({
    queryKey: ["farmers-unassigned", form.district_id || activeDistrictId],
    queryFn: async () => (await api.get("/farmers", { params: { unassigned: true, district_id: form.district_id || activeDistrictId } })).data,
    enabled: open && !!(form.district_id || activeDistrictId),
  });
  const { data: detail } = useQuery<FigDetail>({
    queryKey: ["fig", detailId], queryFn: async () => (await api.get(`/figs/${detailId}`)).data,
    enabled: !!detailId,
  });
  const { data: detailUnassignedFarmers = [] } = useQuery<Farmer[]>({
    queryKey: ["farmers-unassigned-detail", detail?.district_id],
    queryFn: async () => (await api.get("/farmers", { params: { unassigned: true, district_id: detail!.district_id } })).data,
    enabled: !!detail,
  });
  const { data: editAssets = [] } = useQuery<AssetInstance[]>({
    queryKey: ["assets-for-fig", detail?.id],
    queryFn: async () => (await api.get(`/assets?owner_type=FIG&owner_id=${detail!.id}`)).data,
    enabled: !!detail,
  });

  const resetCreateForm = () => { setForm(emptyCreateForm()); setTouchedLocation([]); };

  const runSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(qInput);
    setAppliedFilters(reportFilters);
    setReportPage(1);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.member_ids.length < minMembers) {
      toast.error(`Select at least ${minMembers} member(s) to register a FIG`);
      return;
    }
    let created: { id: string; fig_code: string } | null = null;
    try {
      const body = {
        fig_name: form.fig_name, stap_id: form.stap_id, seri_circle_id: form.seri_circle_id,
        district_id: user?.role === "DISTRICT_ADMIN" ? activeDistrictId : form.district_id,
        formation_date: form.formation_date, meeting_venue: form.meeting_venue,
        village_name: form.village_name, panchayat_name: form.panchayat_name,
        post_office: form.post_office, pin_code: form.pin_code,
        address: form.address, member_ids: form.member_ids,
        assets: form.assets.filter((row) => row.asset_type_id).map((row) => ({
          asset_type_id: row.asset_type_id, quantity: Number(row.quantity) || 1,
          acquisition_year: row.acquisition_year ? Number(row.acquisition_year) : null,
        })),
      };
      const res = await api.post("/figs", body);
      created = res.data;
      if (form.president_farmer_id) {
        await api.post("/figs/president", { fig_id: created!.id, farmer_id: form.president_farmer_id });
      }
      toast.success(`FIG registered — ${created!.fig_code}`);
      // Hand over to step 2 rather than closing. The FIG already exists at this point;
      // skipping the documents leaves it created and flagged, never rolled back.
      setNewFig({
        id: created!.id, fig_code: created!.fig_code, fig_name: form.fig_name,
        district_id: user?.role === "DISTRICT_ADMIN" ? (activeDistrictId as string) : form.district_id,
        seri_circle_id: form.seri_circle_id,
      });
      setNewFigDocs({ minutes_path: null, group_photo_path: null });
      setOpen(false);
    } catch (e: any) {
      toast.error(fmtErr(e.response?.data?.detail) + (created ? " — FIG was created; finish setup from its detail view." : ""));
    } finally {
      qc.invalidateQueries({ queryKey: ["figs-report"] });
    }
  };

  const saveNewFigDocs = async () => {
    if (!newFig) return;
    try {
      await api.patch(`/figs/${newFig.id}`, newFigDocs);
      toast.success("Documents saved");
      closeDocsStep();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const closeDocsStep = () => {
    setNewFig(null);
    setNewFigDocs({ minutes_path: null, group_photo_path: null });
    resetCreateForm();
    qc.invalidateQueries({ queryKey: ["figs-report"] });
  };

  const addMember = async () => {
    try { await api.post("/figs/members", { fig_id: detailId, farmer_id: memberFarmer });
      toast.success("Member added"); setMemberFarmer("");
      qc.invalidateQueries({ queryKey: ["fig", detailId] });
      qc.invalidateQueries({ queryKey: ["farmers-unassigned-detail"] });
      qc.invalidateQueries({ queryKey: ["figs-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const setPresident = async () => {
    try { await api.post("/figs/president", { fig_id: detailId, ...presForm });
      toast.success("President set"); setPresForm({ farmer_id: "" });
      qc.invalidateQueries({ queryKey: ["fig", detailId] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const toggleFigActive = async () => {
    if (!detail) return;
    try {
      await api.patch(`/figs/${detail.id}/active`, { is_active: !detail.is_active });
      toast.success(detail.is_active ? "FIG deactivated" : "FIG activated");
      qc.invalidateQueries({ queryKey: ["fig", detailId] });
      qc.invalidateQueries({ queryKey: ["figs-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const openFigEdit = () => {
    if (!detail) return;
    setEditForm({
      fig_name: detail.fig_name, stap_id: detail.stap_id,
      formation_date: detail.formation_date?.slice(0, 10) || "",
      meeting_venue: detail.meeting_venue || "",
      village_name: detail.village_name || "", panchayat_name: detail.panchayat_name || "",
      post_office: detail.post_office || "",
      pin_code: detail.pin_code || "", address: detail.address || "",
      minutes_path: detail.minutes_path || null, group_photo_path: detail.group_photo_path || null,
    });
    setEditNewAssets([]);
    setEditingFig(true);
  };
  const saveFigEdit = async () => {
    if (!detail || !editForm) return;
    try {
      await api.patch(`/figs/${detail.id}`, editForm);
      const newAssets = editNewAssets.filter((row) => row.asset_type_id);
      for (const row of newAssets) {
        await api.post("/assets", {
          asset_type_id: row.asset_type_id, owner_type: "FIG", owner_id: detail.id,
          quantity: Number(row.quantity) || 1,
          acquisition_date: row.acquisition_year ? `${row.acquisition_year}-01-01` : null,
          acquisition_mode: "SELF_PROCURED", confidence: "FARMER_SELF_DECLARED",
        });
      }
      toast.success("FIG updated");
      setEditingFig(false); setEditForm(null); setEditNewAssets([]);
      qc.invalidateQueries({ queryKey: ["fig", detailId] });
      qc.invalidateQueries({ queryKey: ["figs-report"] });
      qc.invalidateQueries({ queryKey: ["assets-for-fig", detail.id] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const deleteFigAsset = async (assetId: string) => {
    if (!detail) return;
    try {
      await api.delete(`/assets/${assetId}`);
      toast.success("Asset deleted");
      qc.invalidateQueries({ queryKey: ["assets-for-fig", detail.id] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><h1 className="font-heading text-3xl font-extrabold">Farmer Interest Groups</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Group-level operational units</p></div>
        {canRegisterFig && <button onClick={() => setOpen(true)} className="btn-primary inline-flex items-center gap-2" data-testid="add-fig-btn"><Plus size={16} weight="bold" />Register FIG</button>}
      </div>

      {user?.role !== "FIG_PRESIDENT" && (
        <FigFilterPanel
          qInput={qInput} setQInput={setQInput} filters={reportFilters} setFilters={setReportFilters}
          onSubmit={runSearch} staps={staps} districts={districts} filterCircles={filterCircles} role={user?.role}
        />
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Code</th><th>Name</th><th>Silk Type / Activity / Product</th><th>District</th><th>Sericulture Circle</th><th>Total Members</th><th>Members</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {figsRows.map((f) => (
              <FigRow key={f.id} f={f} staps={staps} districts={districts} allCircles={allCircles} onView={() => setDetailId(f.id)} />
            ))}
            {figsRows.length === 0 && <tr><td colSpan={9} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No FIGs found</td></tr>}
          </tbody>
        </table>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>
          Showing {showingFrom}–{showingTo} of {total}
        </div>
        <div className="flex items-center gap-3">
          <select className="input" value={reportPageSize} onChange={(e) => { setReportPageSize(Number(e.target.value)); setReportPage(1); }}>
            {[10, 20, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}
          </select>
          <button className="btn-secondary" disabled={reportPage <= 1} onClick={() => setReportPage((p) => p - 1)}>Prev</button>
          <button className="btn-secondary" disabled={reportPage * reportPageSize >= total} onClick={() => setReportPage((p) => p + 1)}>Next</button>
          <ExportButtons report="figs" params={filterParamsFrom(appliedFilters, appliedQ)} />
        </div>
      </div>

      <div id="onboarding-trend" className="card p-6 mt-6" style={justFocused ? { boxShadow: "0 0 0 3px var(--primary)" } : undefined}>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <ChartLineUp size={20} weight="duotone" color="#2D5134" />
            <h3 className="font-heading text-lg font-bold">FIG onboarding trend</h3>
          </div>
          <select className="input max-w-xs" value={trendFy} onChange={(e) => setTrendFy(e.target.value)}>
            <option value="">Trailing 12 months</option>
            {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
        <div style={{ height: 280 }}>
          <MultiSeriesTrendChart data={chartData} seriesKeys={["FIGs"]} />
        </div>
        {chartData.length === 0 && (
          <div className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>No data yet</div>
        )}
      </div>

      {open && (
        <FigRegisterModal
          form={form} setForm={setForm} onClose={() => { setOpen(false); resetCreateForm(); }} onSubmit={submit}
          isStateAdmin={user?.role === "STATE_ADMIN"} userDistrictId={activeDistrictId} minMembers={minMembers}
          districts={districts} circles={circles} subdivisionCdcs={subdivisionCdcs} staps={staps} unassignedFarmers={unassignedFarmers}
          assetTypes={assetTypes}
          touchedLocation={touchedLocation} setTouchedLocation={setTouchedLocation}
        />
      )}

      {newFig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.45)" }}>
          <div className="card w-full max-w-2xl p-6">
            <h3 className="font-heading text-lg font-bold">Step 2 of 2 — FIG documents</h3>
            <p className="text-sm mt-1 mb-4" style={{ color: "var(--text-muted)" }}>
              <span className="font-semibold">{newFig.fig_name}</span>{" "}
              <span className="font-mono text-xs">({newFig.fig_code})</span> has been created.
            </p>
            <FigDocumentsStep
              figName={newFig.fig_name} figCode={newFig.fig_code}
              districtId={newFig.district_id} seriCircleId={newFig.seri_circle_id}
              value={newFigDocs} onChange={setNewFigDocs}
            />
            <div className="flex justify-end gap-2 mt-6">
              <button type="button" className="btn-secondary" onClick={closeDocsStep} data-testid="fig-docs-later">
                I&apos;ll do this later
              </button>
              <button type="button" className="btn-primary" onClick={saveNewFigDocs} data-testid="fig-docs-save"
                      disabled={!newFigDocs.minutes_path && !newFigDocs.group_photo_path}>
                Save documents
              </button>
            </div>
          </div>
        </div>
      )}

      {detailId && detail && (
        <FigDetailModal
          detail={detail} staps={staps} districts={districts} allCircles={allCircles} subdivisionCdcs={subdivisionCdcs}
          editingFig={editingFig} editForm={editForm} setEditForm={setEditForm}
          onEditClick={openFigEdit} onSaveEdit={saveFigEdit} onCancelEdit={() => { setEditingFig(false); setEditForm(null); setEditNewAssets([]); }}
          canEditDetails={canEditDetails} canToggleActive={canToggleActive} canManageMembership={canManageMembership}
          onToggleActive={toggleFigActive} onClose={() => { setDetailId(null); setEditingFig(false); setEditForm(null); setEditNewAssets([]); }}
          memberFarmer={memberFarmer} setMemberFarmer={setMemberFarmer}
          detailUnassignedFarmers={detailUnassignedFarmers} onAddMember={addMember}
          presForm={presForm} setPresForm={setPresForm} onSetPresident={setPresident}
          assetTypes={assetTypes} editAssets={editAssets} editNewAssets={editNewAssets}
          setEditNewAssets={setEditNewAssets} onDeleteAsset={deleteFigAsset}
        />
      )}
    </div>
  );
}
