"use client";
import { useState } from "react";
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
import { FigDetailModal } from "@/components/figs/FigDetailModal";
import { type FigEditFormState } from "@/components/figs/FigEditForm";
import { type PresForm } from "@/components/figs/FigPresidentPanel";
import type { Fig, FigDetail, Farmer, District, SericultureCircle, SilkTypeActivityProduct, FigSettings } from "@/lib/types";

const MultiSeriesTrendChart = dynamic(() => import("../dashboard/charts").then((m) => m.MultiSeriesTrendChart), { ssr: false });

const emptyCreateForm = (): FigCreateForm => ({
  fig_name: "", stap_id: "", seri_circle_id: "", district_id: "", formation_date: "", meeting_venue: "",
  village_name: "", panchayat_name: "", post_office: "", police_station: "", pin_code: "", address: "",
  member_ids: [], president_farmer_id: "", president_mobile: "", president_password: "",
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
  const { user } = useAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const canRegisterFig = user?.role === "DISTRICT_ADMIN";
  const canEditDetails = user?.role === "DISTRICT_ADMIN";
  const canToggleActive = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN";
  const canManageMembership = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN";

  const [open, setOpen] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [memberFarmer, setMemberFarmer] = useState("");
  const [presForm, setPresForm] = useState<PresForm>({ farmer_id: "", mobile_no: "", password: "" });
  const [resetPassword, setResetPassword] = useState("");
  const [editingFig, setEditingFig] = useState(false);
  const [editForm, setEditForm] = useState<FigEditFormState | null>(null);
  const [form, setForm] = useState<FigCreateForm>(emptyCreateForm());

  // Filter panel — live-edited state, only takes effect on Search.
  const [qInput, setQInput] = useState("");
  const [reportFilters, setReportFilters] = useState(emptyReportFilters());
  const [appliedQ, setAppliedQ] = useState("");
  const [appliedFilters, setAppliedFilters] = useState(emptyReportFilters());
  const [reportPage, setReportPage] = useState(1);
  const [reportPageSize, setReportPageSize] = useState(20);
  const [hasSearched, setHasSearched] = useState(() => searchParams.get("autoSearch") === "1");
  const [trendFy, setTrendFy] = useState("");

  const { data: reportData } = useQuery<{ items: Fig[]; total: number }>({
    queryKey: ["figs-report", appliedQ, appliedFilters, reportPage, reportPageSize],
    queryFn: async () => (await api.get("/figs", {
      params: { ...filterParamsFrom(appliedFilters, appliedQ), page: reportPage, page_size: reportPageSize },
    })).data,
    enabled: hasSearched || user?.role === "FIG_PRESIDENT",
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
  const { data: circles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-fig", form.district_id || user?.district_id],
    queryFn: async () => {
      const did = form.district_id || user?.district_id;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: !!(form.district_id || user?.district_id),
  });
  const { data: filterCircles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-filter-figs", reportFilters.district_id || user?.district_id],
    queryFn: async () => {
      const did = reportFilters.district_id || user?.district_id;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: user?.role !== "FIG_PRESIDENT" && !!(reportFilters.district_id || user?.district_id),
  });
  const { data: unassignedFarmers = [] } = useQuery<Farmer[]>({
    queryKey: ["farmers-unassigned", form.district_id || user?.district_id],
    queryFn: async () => (await api.get("/farmers", { params: { unassigned: true, district_id: form.district_id || user?.district_id } })).data,
    enabled: open && !!(form.district_id || user?.district_id),
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

  const resetCreateForm = () => setForm(emptyCreateForm());

  const runSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(qInput);
    setAppliedFilters(reportFilters);
    setReportPage(1);
    setHasSearched(true);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.member_ids.length < minMembers) {
      toast.error(`Select at least ${minMembers} member(s) to register a FIG`);
      return;
    }
    if (form.president_farmer_id && (!form.president_mobile || !form.president_password)) {
      toast.error("Provide a login mobile and password for the president");
      return;
    }
    let created: { id: string; fig_code: string } | null = null;
    try {
      const body = {
        fig_name: form.fig_name, stap_id: form.stap_id, seri_circle_id: form.seri_circle_id,
        district_id: user?.role === "DISTRICT_ADMIN" ? user.district_id : form.district_id,
        formation_date: form.formation_date, meeting_venue: form.meeting_venue,
        village_name: form.village_name, panchayat_name: form.panchayat_name,
        post_office: form.post_office, police_station: form.police_station, pin_code: form.pin_code,
        address: form.address, member_ids: form.member_ids,
      };
      const res = await api.post("/figs", body);
      created = res.data;
      if (form.president_farmer_id) {
        await api.post("/figs/president", {
          fig_id: created!.id, farmer_id: form.president_farmer_id,
          mobile_no: form.president_mobile, password: form.president_password,
        });
      }
      toast.success("FIG registered");
      setOpen(false);
      resetCreateForm();
    } catch (e: any) {
      toast.error(fmtErr(e.response?.data?.detail) + (created ? " — FIG was created; finish setup from its detail view." : ""));
    } finally {
      qc.invalidateQueries({ queryKey: ["figs-report"] });
    }
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
      toast.success("President set"); setPresForm({ farmer_id: "", mobile_no: "", password: "" });
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
      post_office: detail.post_office || "", police_station: detail.police_station || "",
      pin_code: detail.pin_code || "", address: detail.address || "",
    });
    setEditingFig(true);
  };
  const saveFigEdit = async () => {
    if (!detail || !editForm) return;
    try {
      await api.patch(`/figs/${detail.id}`, editForm);
      toast.success("FIG updated");
      setEditingFig(false); setEditForm(null);
      qc.invalidateQueries({ queryKey: ["fig", detailId] });
      qc.invalidateQueries({ queryKey: ["figs-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const resetPresidentPassword = async () => {
    if (!detail) return;
    try {
      await api.post("/figs/president/reset-password", { fig_id: detail.id, password: resetPassword });
      toast.success("President password reset"); setResetPassword("");
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
        <table className="seri-table">
          <thead><tr><th>Code</th><th>Name</th><th>Silk Type / Activity / Product</th><th>District</th><th>Sericulture Circle</th><th>Total Members</th><th>Members</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {figsRows.map((f) => (
              <FigRow key={f.id} f={f} staps={staps} districts={districts} allCircles={allCircles} onView={() => setDetailId(f.id)} />
            ))}
            {figsRows.length === 0 && <tr><td colSpan={9} className="text-center py-8" style={{ color: "var(--text-muted)" }}>{!hasSearched && user?.role !== "FIG_PRESIDENT" ? "Use Search to view FIGs" : "No FIGs found"}</td></tr>}
          </tbody>
        </table>
      </div>

      {hasSearched && (
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
      )}

      <div className="card p-6 mt-6">
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
          isStateAdmin={user?.role === "STATE_ADMIN"} userDistrictId={user?.district_id} minMembers={minMembers}
          districts={districts} circles={circles} staps={staps} unassignedFarmers={unassignedFarmers}
        />
      )}

      {detailId && detail && (
        <FigDetailModal
          detail={detail} staps={staps} districts={districts} allCircles={allCircles}
          editingFig={editingFig} editForm={editForm} setEditForm={setEditForm}
          onEditClick={openFigEdit} onSaveEdit={saveFigEdit} onCancelEdit={() => { setEditingFig(false); setEditForm(null); }}
          canEditDetails={canEditDetails} canToggleActive={canToggleActive} canManageMembership={canManageMembership}
          onToggleActive={toggleFigActive} onClose={() => { setDetailId(null); setEditingFig(false); setEditForm(null); }}
          memberFarmer={memberFarmer} setMemberFarmer={setMemberFarmer}
          detailUnassignedFarmers={detailUnassignedFarmers} onAddMember={addMember}
          presForm={presForm} setPresForm={setPresForm} onSetPresident={setPresident}
          resetPassword={resetPassword} setResetPassword={setResetPassword} onResetPassword={resetPresidentPassword}
        />
      )}
    </div>
  );
}
