"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fyOptions } from "@/lib/fiscal";
import { ExportButtons } from "@/components/ExportButtons";
import { BulkUploadModal } from "@/components/farmers/BulkUploadModal";
import { downloadFarmerBulkTemplate } from "@/lib/export";
import { Plus, ChartLineUp, DownloadSimple, UploadSimple } from "@phosphor-icons/react";
import { toast } from "sonner";
import { type LandRow } from "@/components/LandRowsEditor";
import { type AssetRow } from "@/components/AssetRowsEditor";
import { FarmerRow } from "@/components/farmers/FarmerRow";
import { FarmerFilterPanel, type FarmerReportFilters } from "@/components/farmers/FarmerFilterPanel";
import { FarmerRegisterModal, type FarmerForm } from "@/components/farmers/FarmerRegisterModal";
import { FarmerEditModal, type FarmerEditForm } from "@/components/farmers/FarmerEditModal";
import { FarmerViewModal } from "@/components/farmers/FarmerViewModal";
import type { Farmer, District, SericultureCircle, Lac, SilkTypeActivityProduct, Caste, Religion, EducationLevel, Activity, Land, AssetType, AssetInstance, ActivityOnboardingResponse } from "@/lib/types";

const MultiSeriesTrendChart = dynamic(() => import("../dashboard/charts").then((m) => m.MultiSeriesTrendChart), { ssr: false });

const emptyForm = (): FarmerForm => ({
  // gender starts blank on purpose — it drives scheme eligibility, so the DA must choose
  // rather than have the form quietly default every farmer to "Male".
  first_name: "", middle_name: "", last_name: "", gender: "", date_of_birth: "",
  mobile_no: "", aadhaar_no: "", pan_no: "",
  district_id: "", seri_circle_id: "", village_name: "", gaon_panchayat: "", development_block: "",
  post_office: "", pin_code: "",
  stap_ids: [], experience_activity_ids: [],
  farmer_type: "Small", education_level_id: "", experience_years: 0,
  caste_id: "", religion_id: "", family_member_male: 0, family_member_female: 0,
  photo_path: null,
  account_number: "", bank_name: "", branch_name: "", ifsc_code: "", passbook_path: null,
  lands: [], assets: [],
});

const emptyReportFilters = (): FarmerReportFilters => ({
  gender: "", education_level_id: "", caste_id: "", religion_id: "",
  district_id: "", seri_circle_id: "", experience_min: "", experience_max: "",
  has_bank_details: "", is_active: "", has_fig: "",
});

function toApiBody(form: Record<string, any>) {
  const body: Record<string, any> = { ...form };
  if (!body.date_of_birth) body.date_of_birth = null;
  if (!body.caste_id) body.caste_id = null;
  if (!body.religion_id) body.religion_id = null;
  if (!body.education_level_id) body.education_level_id = null;
  // Every one of these is an optional FK. An empty string is NOT null to Postgres, so
  // sending "" fails the foreign-key constraint with a 500 instead of storing "unset" —
  // which is exactly what happens when a farmer is registered with no silk type /
  // activity / product picked, since that field is optional on the form.
  return body;
}

function filterParamsFrom(f: FarmerReportFilters, q: string) {
  const p: Record<string, string> = {};
  if (q) p.q = q;
  if (f.gender) p.gender = f.gender;
  if (f.education_level_id) p.education_level_id = f.education_level_id;
  if (f.caste_id) p.caste_id = f.caste_id;
  if (f.religion_id) p.religion_id = f.religion_id;
  if (f.district_id) p.district_id = f.district_id;
  if (f.seri_circle_id) p.seri_circle_id = f.seri_circle_id;
  if (f.experience_min) p.experience_min = f.experience_min;
  if (f.experience_max) p.experience_max = f.experience_max;
  if (f.has_bank_details) p.has_bank_details = f.has_bank_details;
  if (f.is_active) p.is_active = f.is_active;
  if (f.has_fig) p.has_fig = f.has_fig;
  return p;
}

export default function FarmersPage() {
  const { user, activeDistrictId } = useAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const isReportRole = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN" || user?.role === "FIG_PRESIDENT";
  const canRegisterEdit = user?.role === "DISTRICT_ADMIN";
  const canResetPassword = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN";
  const canToggleActive = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN";
  const canView = isReportRole;

  // Filter panel — live-edited state, only takes effect on Search.
  const [qInput, setQInput] = useState("");
  const [reportFilters, setReportFilters] = useState(emptyReportFilters());
  const [appliedQ, setAppliedQ] = useState("");
  const [appliedFilters, setAppliedFilters] = useState(emptyReportFilters());
  const [reportPage, setReportPage] = useState(1);
  const [reportPageSize, setReportPageSize] = useState(20);
  const [trendFy, setTrendFy] = useState("");
  // Activity-wise onboarding: all-time by default, since that is the cumulative figure.
  const [actMode, setActMode] = useState<"all" | "month" | "range">("all");
  const [actMonth, setActMonth] = useState("");
  const [actFrom, setActFrom] = useState("");
  const [actTo, setActTo] = useState("");
  const [actDistrict, setActDistrict] = useState("");
  const [justFocused, setJustFocused] = useState(false);
  // False until the admin actually types a new Aadhaar. While false, submitEdit drops the
  // field from the PATCH so the masked placeholder can never overwrite the stored number.
  const [aadhaarDirty, setAadhaarDirty] = useState(false);

  useEffect(() => {
    if (searchParams.get("focus") !== "onboarding-trend" || !isReportRole) return;
    const el = document.getElementById("onboarding-trend");
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setJustFocused(true);
    const t = setTimeout(() => setJustFocused(false), 2000);
    return () => clearTimeout(t);
  }, [searchParams, isReportRole]);

  const [open, setOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);

  async function downloadTemplate() {
    try {
      await downloadFarmerBulkTemplate();
    } catch {
      toast.error("Could not build the template — check that your district has sericulture circles set up");
    }
  }
  const [form, setForm] = useState<FarmerForm>(emptyForm());
  const [editing, setEditing] = useState<Farmer | null>(null);
  const [editForm, setEditForm] = useState<FarmerEditForm | null>(null);
  const [editNewLands, setEditNewLands] = useState<LandRow[]>([]);
  const [editNewAssets, setEditNewAssets] = useState<AssetRow[]>([]);
  const [viewing, setViewing] = useState<Farmer | null>(null);
  const [resetPassword, setResetPassword] = useState("");

  const { data: reportData } = useQuery<{ items: Farmer[]; total: number }>({
    queryKey: ["farmers-report", appliedQ, appliedFilters, reportPage, reportPageSize],
    queryFn: async () => (await api.get("/farmers", {
      params: { ...filterParamsFrom(appliedFilters, appliedQ), page: reportPage, page_size: reportPageSize },
    })).data,
    enabled: isReportRole,
  });

  const { data: trend } = useQuery<{ months: string[]; farmers_monthly: number[] }>({
    queryKey: ["farmers-onboarding-trend", trendFy],
    queryFn: async () => (await api.get("/reports/onboarding-trend", { params: trendFy ? { fiscal_year: trendFy } : {} })).data,
    enabled: isReportRole,
  });

  const farmers = reportData?.items ?? [];
  const total = reportData?.total ?? 0;
  const showingFrom = total === 0 ? 0 : (reportPage - 1) * reportPageSize + 1;
  const showingTo = Math.min(reportPage * reportPageSize, total);
  const chartData = (trend?.months ?? []).map((m, i) => ({ label: m, Farmers: trend?.farmers_monthly[i] ?? 0 }));

  const activityParams: Record<string, string> = {
    ...(actMode === "month" && actMonth ? { month: actMonth } : {}),
    ...(actMode === "range" && actFrom ? { from_date: actFrom } : {}),
    ...(actMode === "range" && actTo ? { to_date: actTo } : {}),
    ...(actDistrict ? { district_id: actDistrict } : {}),
  };
  const { data: activityOnboarding } = useQuery<ActivityOnboardingResponse>({
    queryKey: ["activity-onboarding", activityParams],
    queryFn: async () => (await api.get("/reports/activity-onboarding", { params: activityParams })).data,
    enabled: user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN",
  });
  const activitySum = (activityOnboarding?.items ?? []).reduce((n, i) => n + i.farmers, 0);

  const { data: districts = [] } = useQuery<District[]>({ queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data });
  const { data: lacs = [] } = useQuery<Lac[]>({ queryKey: ["lacs-all"], queryFn: async () => (await api.get("/master/lacs")).data });
  const { data: staps = [] } = useQuery<SilkTypeActivityProduct[]>({ queryKey: ["staps", "output"], queryFn: async () => (await api.get("/master/silk-type-activity-products?role=OUTPUT")).data });
  const { data: castes = [] } = useQuery<Caste[]>({ queryKey: ["castes"], queryFn: async () => (await api.get("/master/castes")).data });
  const { data: religions = [] } = useQuery<Religion[]>({ queryKey: ["religions"], queryFn: async () => (await api.get("/master/religions")).data });
  const { data: educationLevels = [] } = useQuery<EducationLevel[]>({ queryKey: ["education-levels"], queryFn: async () => (await api.get("/master/education-levels")).data });
  const { data: activities = [] } = useQuery<Activity[]>({ queryKey: ["activities"], queryFn: async () => (await api.get("/master/activities")).data });
  const { data: circles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles", form.district_id || activeDistrictId],
    queryFn: async () => {
      const did = form.district_id || activeDistrictId;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: !!(form.district_id || activeDistrictId),
  });
  const { data: editCircles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-edit", editing?.district_id],
    queryFn: async () => (await api.get("/master/sericulture-circles", { params: { district_id: editing!.district_id } })).data,
    enabled: !!editing,
  });
  const { data: viewCircles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-view", viewing?.district_id],
    queryFn: async () => (await api.get("/master/sericulture-circles", { params: { district_id: viewing!.district_id } })).data,
    enabled: !!viewing,
  });
  const { data: editLands = [] } = useQuery<Land[]>({
    queryKey: ["lands-for-farmer", editing?.id],
    queryFn: async () => (await api.get(`/lands?farmer_id=${editing!.id}`)).data,
    enabled: !!editing,
  });
  const { data: viewLands = [] } = useQuery<Land[]>({
    queryKey: ["lands-for-farmer", viewing?.id],
    queryFn: async () => (await api.get(`/lands?farmer_id=${viewing!.id}`)).data,
    enabled: !!viewing,
  });
  const { data: assetTypes = [] } = useQuery<AssetType[]>({
    queryKey: ["master-asset-types-all"],
    queryFn: async () => (await api.get("/master/asset-types?all=true")).data,
  });
  const { data: editAssets = [] } = useQuery<AssetInstance[]>({
    queryKey: ["assets-for-farmer", editing?.id],
    queryFn: async () => (await api.get(`/assets?owner_type=FARMER&owner_id=${editing!.id}`)).data,
    enabled: !!editing,
  });
  const { data: viewAssets = [] } = useQuery<AssetInstance[]>({
    queryKey: ["assets-for-farmer", viewing?.id],
    queryFn: async () => (await api.get(`/assets?owner_type=FARMER&owner_id=${viewing!.id}`)).data,
    enabled: !!viewing,
  });
  const { data: filterCircles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-filter", reportFilters.district_id || activeDistrictId],
    queryFn: async () => {
      const did = reportFilters.district_id || activeDistrictId;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: isReportRole && !!(reportFilters.district_id || activeDistrictId),
  });

  const runSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(qInput);
    setAppliedFilters(reportFilters);
    setReportPage(1);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const body = toApiBody(form);
      if (user?.role === "DISTRICT_ADMIN") body.district_id = activeDistrictId;
      body.lands = form.lands.filter((row) => row.dag_no || row.patta_no);
      body.assets = form.assets
        .filter((row) => row.asset_type_id)
        .map((row) => ({
          asset_type_id: row.asset_type_id,
          quantity: Number(row.quantity) || 1,
          acquisition_year: row.acquisition_year ? Number(row.acquisition_year) : null,
        }));
      await api.post("/farmers", body);
      toast.success("Farmer registered");
      setOpen(false);
      setForm(emptyForm());
      qc.invalidateQueries({ queryKey: ["farmers"] });
      qc.invalidateQueries({ queryKey: ["farmers-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const openEdit = (f: Farmer) => {
    setEditing(f);
    setEditNewLands([]);
    setEditNewAssets([]);
    setAadhaarDirty(false);
    setEditForm({
      first_name: f.first_name, middle_name: f.middle_name || "", last_name: f.last_name,
      gender: f.gender, date_of_birth: f.date_of_birth ? f.date_of_birth.slice(0, 10) : "",
      mobile_no: f.mobile_no, aadhaar_no: "", pan_no: f.pan_no || "",
      seri_circle_id: f.seri_circle_id, village_name: f.village_name,
      gaon_panchayat: f.gaon_panchayat || "", development_block: f.development_block || "", post_office: f.post_office || "",
      pin_code: f.pin_code || "",
      stap_ids: f.stap_ids || [],
      experience_activity_ids: f.experience_activity_ids || [],
      farmer_type: f.farmer_type || "Small",
      education_level_id: f.education_level_id || "", experience_years: f.experience_years || 0,
      caste_id: f.caste_id || "", religion_id: f.religion_id || "",
      family_member_male: f.family_member_male || 0, family_member_female: f.family_member_female || 0,
      photo_path: f.photo_path || null,
      account_number: f.account_number || "", bank_name: f.bank_name || "",
      branch_name: f.branch_name || "", ifsc_code: f.ifsc_code || "", passbook_path: f.passbook_path || null,
    });
  };

  const submitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editing || !editForm) return;
    try {
      const editBody = toApiBody(editForm);
      // Untouched Aadhaar must not be sent at all — see aadhaarDirty above.
      if (!aadhaarDirty) delete editBody.aadhaar_no;
      await api.patch(`/farmers/${editing.id}`, editBody);
      const newLands = editNewLands.filter((row) => row.dag_no || row.patta_no);
      for (const row of newLands) {
        await api.post("/lands", { farmer_id: editing.id, ...row });
      }
      const newAssets = editNewAssets.filter((row) => row.asset_type_id);
      for (const row of newAssets) {
        await api.post("/assets", {
          asset_type_id: row.asset_type_id, owner_type: "FARMER", owner_id: editing.id,
          quantity: Number(row.quantity) || 1,
          acquisition_date: row.acquisition_year ? `${row.acquisition_year}-01-01` : null,
          acquisition_mode: "SELF_PROCURED", confidence: "FARMER_SELF_DECLARED",
        });
      }
      toast.success("Farmer updated");
      setEditing(null); setEditForm(null); setEditNewLands([]); setEditNewAssets([]);
      qc.invalidateQueries({ queryKey: ["farmers"] });
      qc.invalidateQueries({ queryKey: ["farmers-report"] });
      qc.invalidateQueries({ queryKey: ["lands-for-farmer", editing.id] });
      qc.invalidateQueries({ queryKey: ["assets-for-farmer", editing.id] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const deleteLand = async (landId: string) => {
    if (!editing) return;
    try {
      await api.delete(`/lands/${landId}`);
      toast.success("Land parcel deleted");
      qc.invalidateQueries({ queryKey: ["lands-for-farmer", editing.id] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const deleteAsset = async (assetId: string) => {
    if (!editing) return;
    try {
      await api.delete(`/assets/${assetId}`);
      toast.success("Asset deleted");
      qc.invalidateQueries({ queryKey: ["assets-for-farmer", editing.id] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const toggleActive = async (f: Farmer) => {
    try {
      await api.patch(`/farmers/${f.id}/active`, { is_active: !f.is_active });
      toast.success(f.is_active ? "Farmer deactivated" : "Farmer activated");
      qc.invalidateQueries({ queryKey: ["farmers"] });
      qc.invalidateQueries({ queryKey: ["farmers-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const resetFarmerPassword = async () => {
    if (!viewing) return;
    try {
      await api.post(`/farmers/${viewing.id}/reset-password`, { password: resetPassword });
      toast.success("Password reset"); setResetPassword("");
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Farmers</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {user?.role === "STATE_ADMIN" ? "State-wide register" : user?.role === "DISTRICT_ADMIN" ? "Your district’s register" : "Members of your FIG"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {canRegisterEdit && (
            <>
              <button onClick={downloadTemplate} className="btn-secondary inline-flex items-center gap-2" data-testid="bulk-template-btn">
                <DownloadSimple size={16} weight="bold" />Download template
              </button>
              <button onClick={() => setBulkOpen(true)} className="btn-secondary inline-flex items-center gap-2" data-testid="bulk-upload-btn">
                <UploadSimple size={16} weight="bold" />Bulk upload
              </button>
            </>
          )}
          {canRegisterEdit && <button onClick={() => setOpen(true)} className="btn-primary inline-flex items-center gap-2" data-testid="add-farmer-btn"><Plus size={16} weight="bold" />Register farmer</button>}
        </div>
      </div>

      <FarmerFilterPanel
        qInput={qInput} setQInput={setQInput} filters={reportFilters} setFilters={setReportFilters}
        onSubmit={runSearch} districts={districts} educationLevels={educationLevels} castes={castes}
        religions={religions} filterCircles={filterCircles} role={user?.role}
      />

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Code</th><th>Name</th><th>Mobile</th><th>Village</th><th>Gender</th><th>FIG</th><th>Status</th>{(canView || canRegisterEdit || canToggleActive) && <th>Actions</th>}</tr></thead>
          <tbody>
            {farmers.map((f) => (
              <FarmerRow key={f.id} f={f} canView={canView} canEdit={canRegisterEdit} canToggle={canToggleActive}
                         onView={() => setViewing(f)} onEdit={() => openEdit(f)} onToggle={() => toggleActive(f)} />
            ))}
            {farmers.length === 0 && <tr><td colSpan={(canView || canRegisterEdit || canToggleActive) ? 8 : 7} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No farmers found</td></tr>}
          </tbody>
        </table>
        </div>
      </div>

      {isReportRole && (
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
            <ExportButtons report="farmers" params={filterParamsFrom(appliedFilters, appliedQ)} />
          </div>
        </div>
      )}

      {isReportRole && (
        <div id="onboarding-trend" className="card p-6 mt-6" style={justFocused ? { boxShadow: "0 0 0 3px var(--primary)" } : undefined}>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <ChartLineUp size={20} weight="duotone" color="#2D5134" />
              <h3 className="font-heading text-lg font-bold">Farmer onboarding trend</h3>
            </div>
            <select className="input max-w-xs" value={trendFy} onChange={(e) => setTrendFy(e.target.value)}>
              <option value="">Trailing 12 months</option>
              {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div style={{ height: 280 }}>
            <MultiSeriesTrendChart data={chartData} seriesKeys={["Farmers"]} />
          </div>
          {chartData.length === 0 && (
            <div className="text-sm text-center py-6" style={{ color: "var(--text-muted)" }}>No data yet</div>
          )}
        </div>
      )}

      {(user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN") && (
        <div className="card p-6 mt-6">
          <div className="flex items-center justify-between mb-1 flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <ChartLineUp size={20} weight="duotone" color="#2D5134" />
              <h3 className="font-heading text-lg font-bold">Farmers onboarded by activity</h3>
            </div>
            <ExportButtons report="activity-onboarding" params={activityParams} />
          </div>

          <div className="flex items-end gap-3 flex-wrap mt-4">
            <div>
              <label className="label-tag">Period</label>
              <select className="input mt-1" value={actMode} data-testid="activity-period-mode"
                      onChange={(e) => setActMode(e.target.value as "all" | "month" | "range")}>
                <option value="all">All time (cumulative)</option>
                <option value="month">Month</option>
                <option value="range">Date range</option>
              </select>
            </div>
            {actMode === "month" && (
              <div>
                <label className="label-tag">Month</label>
                <input type="month" className="input mt-1" value={actMonth} onChange={(e) => setActMonth(e.target.value)} />
              </div>
            )}
            {actMode === "range" && (
              <>
                <div>
                  <label className="label-tag">From</label>
                  <input type="date" className="input mt-1" value={actFrom} onChange={(e) => setActFrom(e.target.value)} />
                </div>
                <div>
                  <label className="label-tag">To</label>
                  <input type="date" className="input mt-1" value={actTo} onChange={(e) => setActTo(e.target.value)} />
                </div>
              </>
            )}
            {user?.role === "STATE_ADMIN" && (
              <div>
                <label className="label-tag">District</label>
                <select className="input mt-1" value={actDistrict} onChange={(e) => setActDistrict(e.target.value)}>
                  <option value="">All districts</option>
                  {districts.map((d) => <option key={d.id} value={d.id}>{d.district_name}</option>)}
                </select>
              </div>
            )}
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="seri-table">
              <thead><tr><th>Silk Type</th><th>Activity</th><th className="text-right">Farmers</th></tr></thead>
              <tbody>
                {(activityOnboarding?.items ?? []).map((i) => (
                  <tr key={i.activity_id}>
                    <td>{i.silk_type_name}</td>
                    <td>{i.activity_name}</td>
                    <td className="text-right font-semibold">{i.farmers}</td>
                  </tr>
                ))}
                {(activityOnboarding?.items ?? []).length === 0 && (
                  <tr><td colSpan={3} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No activities configured</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
            <strong>{activityOnboarding?.distinct_farmers ?? 0}</strong> distinct farmers onboarded in this
            period. The column above totals <strong>{activitySum}</strong> because a farmer registered for
            more than one activity is counted under each of them.
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            Counts use the date the farmer was registered and their activities as recorded today — adding an
            activity to an existing farmer changes the figure for the month they were originally registered.
          </p>
        </div>
      )}

      {open && (
        <FarmerRegisterModal
          form={form} setForm={setForm} onClose={() => setOpen(false)} onSubmit={submit}
          isStateAdmin={user?.role === "STATE_ADMIN"}
          districts={districts} circles={circles} lacs={lacs} educationLevels={educationLevels} castes={castes}
          religions={religions} activities={activities} staps={staps} assetTypes={assetTypes}
          lastFarmer={reportData?.items?.[0] ?? null}
        />
      )}

      {bulkOpen && (
        <BulkUploadModal
          onClose={() => setBulkOpen(false)}
          onImported={() => qc.invalidateQueries({ queryKey: ["farmers-report"] })}
        />
      )}

      {editing && editForm && (
        <FarmerEditModal
          editing={editing} editForm={editForm} setEditForm={setEditForm}
          onClose={() => { setEditing(null); setEditForm(null); }} onSubmit={submitEdit}
          editCircles={editCircles} lacs={lacs} educationLevels={educationLevels} castes={castes} religions={religions}
          activities={activities} staps={staps} assetTypes={assetTypes}
          editLands={editLands} editAssets={editAssets}
          editNewLands={editNewLands} setEditNewLands={setEditNewLands}
          editNewAssets={editNewAssets} setEditNewAssets={setEditNewAssets}
          onDeleteLand={deleteLand} onDeleteAsset={deleteAsset}
          aadhaarDirty={aadhaarDirty} setAadhaarDirty={setAadhaarDirty}
        />
      )}

      {viewing && (
        <FarmerViewModal
          viewing={viewing} onClose={() => { setViewing(null); setResetPassword(""); }}
          viewCircles={viewCircles} lacs={lacs} viewLands={viewLands} viewAssets={viewAssets}
          districts={districts} castes={castes} religions={religions} educationLevels={educationLevels}
          activities={activities} staps={staps}
          canResetPassword={canResetPassword} resetPassword={resetPassword} setResetPassword={setResetPassword}
          onResetPassword={resetFarmerPassword}
        />
      )}
    </div>
  );
}
