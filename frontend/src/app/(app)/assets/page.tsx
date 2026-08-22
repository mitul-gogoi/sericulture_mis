"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { X, CheckCircle, XCircle, Warning, PencilSimple, Trash, MapPin, Paperclip } from "@phosphor-icons/react";
import { toast } from "sonner";
import FileUpload from "@/components/FileUpload";
import { ExportButtons } from "@/components/ExportButtons";
import { AssetFilterPanel, type AssetReportFilters } from "@/components/assets/AssetFilterPanel";
import type {
  AssetInstance, AssetType, AssetsPage, AssetAcquisitionMode,
  AssetConfidence, AssetVerifyResult, District, SericultureCircle, AssetGpsDraft,
} from "@/lib/types";

const MODE_LABELS: Record<AssetAcquisitionMode, string> = {
  SCHEME_DISBURSEMENT: "Scheme Disbursement", SELF_PROCURED: "Self-Procured",
  SELF_DECLARED_AT_REGISTRATION: "Self-Declared (Registration)", LEGACY_SELF_DECLARED: "Legacy Self-Declared",
};
const CONFIDENCE_OPTIONS: { value: AssetConfidence; label: string }[] = [
  { value: "FARMER_SELF_DECLARED", label: "Self-declared" },
  { value: "CIRCLE_OFFICER_RECOLLECTION", label: "Official Visit" },
  { value: "DOCUMENTARY_EVIDENCE_SEEN", label: "Documentary Evidence" },
];
const PAGE_SIZES = [10, 20, 50, 100];

function verificationBadge(status: AssetInstance["verification_status"]) {
  if (status === "CIRCLE_VERIFIED") return <span className="badge badge-success">Verified</span>;
  if (status === "DISPUTED") return <span className="badge badge-error">Disputed</span>;
  return <span className="badge badge-muted">Unverified</span>;
}
function gpsBadge(status: AssetInstance["gps_status"]) {
  if (status === "Verified") return <span className="badge badge-success">Verified</span>;
  if (status === "Pending") return <span className="badge badge-warning">Pending</span>;
  if (status === "Failed") return <span className="badge badge-error">Failed</span>;
  return <span className="badge badge-muted">Not submitted</span>;
}
function ageLeftLabel(days: number | null | undefined) {
  if (days == null) return "—";
  if (days < 0) return "Eligible for replacement";
  return `${days} days`;
}

function fileViewerUrl(path: string) {
  const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
}

const emptyReportFilters = (): AssetReportFilters => ({
  owner_type: "", asset_type_id: "", status: "", verification_status: "",
  confidence: "", gps_status: "", district_id: "", seri_circle_id: "",
});

function filterParamsFrom(f: AssetReportFilters, q: string) {
  const p: Record<string, string> = {};
  if (q) p.q = q;
  if (f.owner_type) p.owner_type = f.owner_type;
  if (f.asset_type_id) p.asset_type_id = f.asset_type_id;
  if (f.status) p.status = f.status;
  if (f.verification_status) p.verification_status = f.verification_status;
  if (f.confidence) p.confidence = f.confidence;
  if (f.gps_status) p.gps_status = f.gps_status;
  if (f.district_id) p.district_id = f.district_id;
  if (f.seri_circle_id) p.seri_circle_id = f.seri_circle_id;
  return p;
}

function errMsg(e: unknown) {
  return fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail);
}

interface EditFormState {
  quantity: string; acquisition_date: string; status: string;
  confidence: AssetConfidence; acquisition_mode: AssetAcquisitionMode;
  photo_path: string | null; remarks: string;
}

export default function AssetsPage() {
  const { user, activeDistrictId } = useAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const canApprovePhysical = user?.role === "DISTRICT_ADMIN";
  const canEditDelete = user?.role === "DISTRICT_ADMIN";
  const canApproveGps = user?.role === "DISTRICT_ADMIN";
  const canCaptureGps = user?.role === "FIG_PRESIDENT" || user?.role === "FARMER";
  const hasActionsColumn = canApprovePhysical || canEditDelete || canApproveGps || canCaptureGps;

  // Solo farmers capture GPS directly (live); FIG-member farmers stage a private draft their
  // FIG President reviews/finalizes instead — resolved from the farmer's own active-FIG status.
  const { data: ownProfile } = useQuery<{ fig_id: string | null }>({
    queryKey: ["farmer-me"], queryFn: async () => (await api.get("/farmers/me")).data,
    enabled: user?.role === "FARMER",
  });
  const isMemberFarmer = user?.role === "FARMER" && !!ownProfile?.fig_id;
  const [draftPrefillFarmer, setDraftPrefillFarmer] = useState<string | null>(null);

  // Filter panel — live-edited state, only takes effect on Search.
  const initialFilters = (): AssetReportFilters => ({
    ...emptyReportFilters(),
    gps_status: searchParams.get("gps_status") || "",
  });
  const [qInput, setQInput] = useState("");
  const [reportFilters, setReportFilters] = useState<AssetReportFilters>(initialFilters);
  const [appliedQ, setAppliedQ] = useState("");
  const [appliedFilters, setAppliedFilters] = useState<AssetReportFilters>(initialFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [verifyTarget, setVerifyTarget] = useState<AssetInstance | null>(null);
  const [verifyResult, setVerifyResult] = useState<AssetVerifyResult>("CONFIRMED_PRESENT");
  const [verifyPhoto, setVerifyPhoto] = useState<string | null>(null);
  const [verifyRemarks, setVerifyRemarks] = useState("");

  const [editTarget, setEditTarget] = useState<AssetInstance | null>(null);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);

  const [gpsTarget, setGpsTarget] = useState<AssetInstance | null>(null);
  const [gpsLat, setGpsLat] = useState("");
  const [gpsLng, setGpsLng] = useState("");
  const [gpsLocating, setGpsLocating] = useState(false);

  const { data: reportData } = useQuery<AssetsPage>({
    queryKey: ["assets-report", appliedQ, appliedFilters, page, pageSize],
    queryFn: async () => (await api.get("/assets", {
      params: { ...filterParamsFrom(appliedFilters, appliedQ), page, page_size: pageSize },
    })).data,
  });
  const { data: assetTypes = [] } = useQuery<AssetType[]>({
    queryKey: ["master-asset-types-all"],
    queryFn: async () => (await api.get("/master/asset-types?all=true")).data,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data,
    enabled: user?.role === "STATE_ADMIN",
  });
  const { data: filterCircles = [] } = useQuery<SericultureCircle[]>({
    queryKey: ["circles-filter-assets", reportFilters.district_id || activeDistrictId],
    queryFn: async () => {
      const did = reportFilters.district_id || activeDistrictId;
      if (!did) return [];
      return (await api.get("/master/sericulture-circles", { params: { district_id: did } })).data;
    },
    enabled: user?.role !== "FIG_PRESIDENT" && !!(reportFilters.district_id || activeDistrictId),
  });

  const assets = reportData?.items ?? [];
  const total = reportData?.total ?? 0;
  const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const showingTo = Math.min(page * pageSize, total);

  const runSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(qInput);
    setAppliedFilters(reportFilters);
    setPage(1);
  };

  function openVerify(a: AssetInstance) {
    setVerifyTarget(a); setVerifyResult("CONFIRMED_PRESENT"); setVerifyPhoto(null); setVerifyRemarks("");
  }
  async function submitVerify(e: React.FormEvent) {
    e.preventDefault();
    if (!verifyTarget) return;
    try {
      await api.post(`/assets/${verifyTarget.id}/verify`, {
        result: verifyResult, photo_url: verifyPhoto, remarks: verifyRemarks || null,
      });
      toast.success("Verification recorded");
      qc.invalidateQueries({ queryKey: ["assets-report"] });
      setVerifyTarget(null);
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  function openEdit(a: AssetInstance) {
    setEditTarget(a);
    setEditForm({
      quantity: String(a.quantity), acquisition_date: a.acquisition_date?.slice(0, 10) || "",
      status: a.status, confidence: (a.confidence || "FARMER_SELF_DECLARED") as AssetConfidence,
      acquisition_mode: a.acquisition_mode === "SCHEME_DISBURSEMENT" ? "SELF_PROCURED" : a.acquisition_mode,
      photo_path: a.photo_path || null, remarks: a.remarks || "",
    });
  }
  async function submitEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editTarget || !editForm) return;
    try {
      const body: Record<string, unknown> = {
        quantity: Number(editForm.quantity) || 1, acquisition_date: editForm.acquisition_date || null,
        status: editForm.status, confidence: editForm.confidence,
        photo_path: editForm.photo_path, remarks: editForm.remarks || null,
      };
      if (editTarget.acquisition_mode !== "SCHEME_DISBURSEMENT") body.acquisition_mode = editForm.acquisition_mode;
      await api.patch(`/assets/${editTarget.id}`, body);
      toast.success("Asset updated");
      qc.invalidateQueries({ queryKey: ["assets-report"] });
      setEditTarget(null); setEditForm(null);
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  async function deleteAsset(a: AssetInstance) {
    if (!window.confirm(`Delete ${a.asset_type_name || "this asset"} for ${a.owner_name || "this owner"}?`)) return;
    try {
      await api.delete(`/assets/${a.id}`);
      toast.success("Asset deleted");
      qc.invalidateQueries({ queryKey: ["assets-report"] });
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  async function verifyGps(a: AssetInstance, decision: "verified" | "failed") {
    const reason = decision === "failed" ? prompt("Reason for GPS rejection?") || "" : "";
    try {
      await api.post(`/assets/${a.id}/gps/verify`, { decision, reason });
      toast.success("GPS status updated");
      qc.invalidateQueries({ queryKey: ["assets-report"] });
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  async function openCaptureGps(a: AssetInstance) {
    setGpsTarget(a);
    setDraftPrefillFarmer(null);
    if (user?.role === "FIG_PRESIDENT") {
      try {
        const { data } = await api.get<AssetGpsDraft | null>(`/assets/${a.id}/gps/draft`);
        if (data) {
          setGpsLat(String(data.latitude)); setGpsLng(String(data.longitude));
          setDraftPrefillFarmer(a.owner_name || "this member");
          return;
        }
      } catch { /* no draft or not permitted to read one — fall through to normal open */ }
    }
    setGpsLat(a.latitude != null ? String(a.latitude) : "");
    setGpsLng(a.longitude != null ? String(a.longitude) : "");
  }
  function useMyLocation() {
    if (!navigator.geolocation) { toast.error("Geolocation is not supported by this browser"); return; }
    setGpsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsLat(String(pos.coords.latitude)); setGpsLng(String(pos.coords.longitude));
        setGpsLocating(false);
      },
      (err) => {
        setGpsLocating(false);
        if (err.code === err.PERMISSION_DENIED) toast.error("Location permission denied — enable it in your browser settings");
        else if (err.code === err.POSITION_UNAVAILABLE) toast.error("Could not determine your location");
        else toast.error("Location request timed out — try again");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }
  async function submitCaptureGps(e: React.FormEvent) {
    e.preventDefault();
    if (!gpsTarget) return;
    const lat = parseFloat(gpsLat), lng = parseFloat(gpsLng);
    if (Number.isNaN(lat) || lat < -90 || lat > 90) return toast.error("Enter a valid latitude (-90 to 90)");
    if (Number.isNaN(lng) || lng < -180 || lng > 180) return toast.error("Enter a valid longitude (-180 to 180)");
    try {
      if (isMemberFarmer) {
        await api.post(`/assets/${gpsTarget.id}/gps/draft`, { latitude: lat, longitude: lng });
        toast.success("Saved — your FIG President will review and submit this.");
      } else {
        await api.post(`/assets/${gpsTarget.id}/gps`, { latitude: lat, longitude: lng });
        toast.success("GPS location submitted for approval");
      }
      qc.invalidateQueries({ queryKey: ["assets-report"] });
      setGpsTarget(null);
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  return (
    <div>
      <div className="mb-5 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Asset Management</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Durable assets held by farmers and FIGs — used to flag scheme useful-life cooldowns.
            {!hasActionsColumn && " Read-only for your role."}
          </p>
        </div>
      </div>

      <AssetFilterPanel
        qInput={qInput} setQInput={setQInput} filters={reportFilters} setFilters={setReportFilters}
        onSubmit={runSearch} districts={districts} assetTypes={assetTypes} filterCircles={filterCircles} role={user?.role}
      />

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead>
            <tr>
              <th>Asset Code</th><th>Asset Type</th><th>Qty</th><th>Owner Type</th><th>Owner Code</th>
              <th>Owner Name</th><th>Acquired Date</th><th>Age Left</th><th>Acquired Mode</th>
              <th>Confidence Mode</th><th>District</th><th>Sericulture Circle</th><th>GPS Status</th>
              <th>GPS Location</th><th>Verification Status</th><th>Verified By</th><th>Photo</th>
              {hasActionsColumn && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id}>
                <td className="font-mono text-xs">{a.asset_code}</td>
                <td>{a.asset_type_name || "—"}</td>
                <td>{a.quantity}</td>
                <td>{a.owner_type === "FARMER" ? "Farmer" : "FIG"}</td>
                <td className="font-mono text-xs">{a.owner_code || "—"}</td>
                <td className="font-semibold whitespace-nowrap">{a.owner_name || "—"}</td>
                <td>{a.acquisition_date || "—"}</td>
                <td className="text-sm">{ageLeftLabel(a.age_left_days)}</td>
                <td className="text-sm">
                  {MODE_LABELS[a.acquisition_mode]}
                  {a.acquisition_mode === "SCHEME_DISBURSEMENT" && a.scheme_name && ` · ${a.scheme_name}`}
                </td>
                <td className="text-sm">{a.confidence ? CONFIDENCE_OPTIONS.find((c) => c.value === a.confidence)?.label || a.confidence : "—"}</td>
                <td>{a.district_name || "—"}</td>
                <td>{a.circle_name || "—"}</td>
                <td>
                  {gpsBadge(a.gps_status)}
                  {a.has_gps_draft && (
                    <span className="badge badge-warning ml-1" title="Member has self-captured GPS — open Capture GPS to review">Member captured</span>
                  )}
                </td>
                <td className="text-sm">{a.latitude != null && a.longitude != null ? `${a.latitude.toFixed(6)}, ${a.longitude.toFixed(6)}` : "—"}</td>
                <td>{verificationBadge(a.verification_status)}</td>
                <td className="text-sm">{a.last_verified_by_name || "—"}</td>
                <td>
                  {a.photo_path ? (
                    <a href={fileViewerUrl(a.photo_path)} target="_blank" rel="noopener noreferrer"
                       className="text-xs inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
                      <Paperclip size={12} weight="bold" />View
                    </a>
                  ) : "—"}
                </td>
                {hasActionsColumn && (
                  <td>
                    <div className="inline-flex gap-2 items-center flex-wrap">
                      {canApprovePhysical && (
                        <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--success)" }}
                                onClick={() => openVerify(a)}>
                          <CheckCircle size={14} weight="bold" />Approve
                        </button>
                      )}
                      {canApproveGps && a.gps_status === "Pending" && (
                        <>
                          <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--success)" }}
                                  onClick={() => verifyGps(a, "verified")}>
                            <CheckCircle size={14} weight="bold" />Approve GPS
                          </button>
                          <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                                  onClick={() => verifyGps(a, "failed")}>
                            <XCircle size={14} weight="bold" />Reject GPS
                          </button>
                        </>
                      )}
                      {canEditDelete && (
                        <button className="text-xs inline-flex items-center gap-1" onClick={() => openEdit(a)}>
                          <PencilSimple size={14} weight="bold" />Edit
                        </button>
                      )}
                      {canEditDelete && a.acquisition_mode !== "SCHEME_DISBURSEMENT" && (
                        <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                                onClick={() => deleteAsset(a)}>
                          <Trash size={14} weight="bold" />Delete
                        </button>
                      )}
                      {canCaptureGps && a.gps_status !== "Verified" && (
                        <button className="text-xs inline-flex items-center gap-1" onClick={() => openCaptureGps(a)}>
                          <MapPin size={14} weight="bold" />Capture GPS
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {assets.length === 0 && (
              <tr><td colSpan={hasActionsColumn ? 18 : 17} className="text-center py-8" style={{ color: "var(--text-muted)" }}>
                No assets found
              </td></tr>
            )}
          </tbody>
        </table>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>
          Showing {showingFrom}–{showingTo} of {total}
        </div>
        <div className="flex items-center gap-3">
          <select className="input" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
            {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
          </select>
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
          <button className="btn-secondary" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
          <ExportButtons report="assets" params={filterParamsFrom(appliedFilters, appliedQ)} />
        </div>
      </div>

      {verifyTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Approve · {verifyTarget.asset_type_name}</h3>
              <button onClick={() => setVerifyTarget(null)}><X size={20} /></button>
            </div>
            <form onSubmit={submitVerify} className="p-5 grid gap-3">
              <div><label className="label-tag">Result</label>
                <select className="input mt-1" value={verifyResult} onChange={(e) => setVerifyResult(e.target.value as AssetVerifyResult)}>
                  <option value="CONFIRMED_PRESENT">Confirmed Present</option>
                  <option value="PARTIALLY_FUNCTIONAL">Partially Functional</option>
                  <option value="NOT_FOUND">Not Found</option>
                </select></div>
              <div>
                <label className="label-tag block mb-2">Photo</label>
                <FileUpload label="Upload photo" value={verifyPhoto} onChange={setVerifyPhoto}
                            accept=".jpg,.jpeg,.png,.webp" category="assets" farmerIdentifier={verifyTarget.owner_id} />
              </div>
              <div><label className="label-tag">Remarks</label>
                <textarea className="input mt-1" rows={2} value={verifyRemarks} onChange={(e) => setVerifyRemarks(e.target.value)} /></div>
              {verifyResult === "NOT_FOUND" && (
                <div className="text-xs flex items-center gap-1" style={{ color: "var(--error)" }}>
                  <Warning size={14} weight="bold" /> Marks this asset as disputed for follow-up.
                </div>
              )}
              <div className="flex gap-2 justify-end mt-1">
                <button type="button" onClick={() => setVerifyTarget(null)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Submit</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editTarget && editForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Edit · {editTarget.asset_type_name}</h3>
              <button onClick={() => { setEditTarget(null); setEditForm(null); }}><X size={20} /></button>
            </div>
            <form onSubmit={submitEdit} className="p-5 grid gap-3 sm:grid-cols-2">
              <div><label className="label-tag">Quantity</label>
                <input type="number" min={1} className="input mt-1" value={editForm.quantity}
                       onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })} /></div>
              <div><label className="label-tag">Acquisition Date</label>
                <input type="date" className="input mt-1" value={editForm.acquisition_date}
                       onChange={(e) => setEditForm({ ...editForm, acquisition_date: e.target.value })} /></div>
              <div><label className="label-tag">Status</label>
                <select className="input mt-1" value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                  <option value="FUNCTIONAL">Functional</option><option value="UNDER_REPAIR">Under Repair</option>
                  <option value="NON_FUNCTIONAL">Non-Functional</option><option value="DECOMMISSIONED">Decommissioned</option>
                </select></div>
              <div><label className="label-tag">Confidence</label>
                <select className="input mt-1" value={editForm.confidence}
                        onChange={(e) => setEditForm({ ...editForm, confidence: e.target.value as AssetConfidence })}>
                  {CONFIDENCE_OPTIONS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select></div>
              <div className="sm:col-span-2"><label className="label-tag">Acquisition Mode</label>
                <select className="input mt-1" value={editForm.acquisition_mode} disabled={editTarget.acquisition_mode === "SCHEME_DISBURSEMENT"}
                        onChange={(e) => setEditForm({ ...editForm, acquisition_mode: e.target.value as AssetAcquisitionMode })}>
                  <option value="SELF_PROCURED">Self-Procured</option>
                  <option value="SELF_DECLARED_AT_REGISTRATION">Self-Declared (Registration)</option>
                  <option value="LEGACY_SELF_DECLARED">Legacy Self-Declared</option>
                </select>
                {editTarget.acquisition_mode === "SCHEME_DISBURSEMENT" && (
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Scheme-disbursed assets keep their mode.</p>
                )}</div>
              <div className="sm:col-span-2">
                <label className="label-tag block mb-2">Evidence Photo</label>
                <FileUpload label="Upload photo" value={editForm.photo_path}
                            onChange={(p) => setEditForm({ ...editForm, photo_path: p })} accept=".jpg,.jpeg,.png,.webp"
                            category="assets" farmerIdentifier={editTarget.owner_id} />
              </div>
              <div className="sm:col-span-2"><label className="label-tag">Remarks</label>
                <textarea className="input mt-1" rows={2} value={editForm.remarks}
                          onChange={(e) => setEditForm({ ...editForm, remarks: e.target.value })} /></div>
              <div className="sm:col-span-2 flex gap-2 justify-end mt-1">
                <button type="button" onClick={() => { setEditTarget(null); setEditForm(null); }} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {gpsTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-md">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Capture GPS · {gpsTarget.asset_type_name}</h3>
              <button onClick={() => setGpsTarget(null)}><X size={20} /></button>
            </div>
            <form onSubmit={submitCaptureGps} className="p-5 grid gap-3">
              {draftPrefillFarmer && (
                <div className="card p-3 text-sm" style={{ background: "#FBEFD6" }}>
                  Pre-filled from {draftPrefillFarmer}'s self-capture — review, adjust if needed, and submit below.
                </div>
              )}
              {isMemberFarmer && (
                <div className="card p-3 text-sm" style={{ background: "#FBEFD6" }}>
                  You're a FIG member — this won't go live immediately. Saving here stages it for your FIG President to review and submit.
                </div>
              )}
              <div className="grid grid-cols-2 gap-2">
                <div><label className="label-tag">Latitude</label>
                  <input type="number" step="any" min={-90} max={90} className="input mt-1" placeholder="e.g. 26.1445"
                         value={gpsLat} onChange={(e) => setGpsLat(e.target.value)} /></div>
                <div><label className="label-tag">Longitude</label>
                  <input type="number" step="any" min={-180} max={180} className="input mt-1" placeholder="e.g. 91.7362"
                         value={gpsLng} onChange={(e) => setGpsLng(e.target.value)} /></div>
              </div>
              <button type="button" className="btn-secondary inline-flex items-center gap-2 justify-center" onClick={useMyLocation} disabled={gpsLocating}>
                <MapPin size={16} weight="bold" />{gpsLocating ? "Locating…" : "Use my location"}
              </button>
              <div className="flex gap-2 justify-end mt-1">
                <button type="button" onClick={() => setGpsTarget(null)} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">{isMemberFarmer ? "Save for FIG President" : "Submit"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
