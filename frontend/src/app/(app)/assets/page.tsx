"use client";
import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, X, CheckCircle, Warning, Trash, ClockCounterClockwise } from "@phosphor-icons/react";
import { toast } from "sonner";
import FileUpload from "@/components/FileUpload";
import type {
  AssetInstance, AssetType, AssetVerificationLog, AssetOwnerType, AssetAcquisitionMode,
  AssetConfidence, AssetVerifyResult, Farmer, Fig,
} from "@/lib/types";

const MODE_LABELS: Record<AssetAcquisitionMode, string> = {
  SCHEME_DISBURSEMENT: "Scheme Disbursement", SELF_PROCURED: "Self-Procured",
  SELF_DECLARED_AT_REGISTRATION: "Self-Declared (Registration)", LEGACY_SELF_DECLARED: "Legacy Self-Declared",
};
const CONFIDENCE_OPTIONS: { value: AssetConfidence; label: string }[] = [
  { value: "FARMER_SELF_DECLARED", label: "Farmer self-declared" },
  { value: "CIRCLE_OFFICER_RECOLLECTION", label: "Circle officer recollection" },
  { value: "DOCUMENTARY_EVIDENCE_SEEN", label: "Documentary evidence seen" },
];

function statusBadge(status: AssetInstance["status"]) {
  if (status === "FUNCTIONAL") return <span className="badge badge-success">Functional</span>;
  if (status === "UNDER_REPAIR") return <span className="badge badge-warning">Under Repair</span>;
  if (status === "NON_FUNCTIONAL") return <span className="badge badge-error">Non-Functional</span>;
  return <span className="badge badge-muted">Decommissioned</span>;
}
function verificationBadge(status: AssetInstance["verification_status"]) {
  if (status === "CIRCLE_VERIFIED") return <span className="badge badge-success">Verified</span>;
  if (status === "DISPUTED") return <span className="badge badge-error">Disputed</span>;
  return <span className="badge badge-muted">Unverified</span>;
}

const EMPTY_ADD = {
  owner_type: "FARMER" as AssetOwnerType, owner_id: "", asset_type_id: "",
  quantity: "1", acquisition_date: "", acquisition_mode: "LEGACY_SELF_DECLARED" as AssetAcquisitionMode,
  confidence: "FARMER_SELF_DECLARED" as AssetConfidence, photo_path: null as string | null, remarks: "",
};

function errMsg(e: unknown) {
  return fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail);
}

export default function AssetsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canManage = user?.role === "DISTRICT_ADMIN" || user?.role === "STATE_ADMIN";

  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState(EMPTY_ADD);
  const [verifyTarget, setVerifyTarget] = useState<AssetInstance | null>(null);
  const [verifyResult, setVerifyResult] = useState<AssetVerifyResult>("CONFIRMED_PRESENT");
  const [verifyPhoto, setVerifyPhoto] = useState<string | null>(null);
  const [verifyRemarks, setVerifyRemarks] = useState("");
  const [logTarget, setLogTarget] = useState<AssetInstance | null>(null);

  const { data: assets = [], isLoading } = useQuery<AssetInstance[]>({
    queryKey: ["assets"], queryFn: async () => (await api.get("/assets")).data,
  });
  const { data: assetTypes = [] } = useQuery<AssetType[]>({
    queryKey: ["master-asset-types-all"],
    queryFn: async () => (await api.get("/master/asset-types?all=true")).data,
  });
  const { data: farmers = [] } = useQuery<Farmer[]>({
    queryKey: ["farmers-for-assets"],
    queryFn: async () => (await api.get("/farmers", { params: { limit: 300 } })).data,
    enabled: showAdd && addForm.owner_type === "FARMER",
  });
  const { data: figs = [] } = useQuery<Fig[]>({
    queryKey: ["figs-for-assets"],
    queryFn: async () => (await api.get("/figs", { params: { page_size: 300, page: 1 } })).data?.items ?? [],
    enabled: showAdd && addForm.owner_type === "FIG",
  });
  const { data: verificationLog = [] } = useQuery<AssetVerificationLog[]>({
    queryKey: ["asset-verification-log", logTarget?.id],
    queryFn: async () => (await api.get(`/assets/${logTarget!.id}/verification-log`)).data,
    enabled: !!logTarget,
  });

  const eligibleTypesForOwner = useMemo(
    () => assetTypes.filter((t) => t.is_active && (addForm.owner_type === "FIG" ? t.ownership_level !== "INDIVIDUAL" : t.ownership_level !== "FIG")),
    [assetTypes, addForm.owner_type],
  );

  function resetAdd() { setShowAdd(false); setAddForm(EMPTY_ADD); }

  async function submitAdd(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.post("/assets", {
        asset_type_id: addForm.asset_type_id, owner_type: addForm.owner_type, owner_id: addForm.owner_id,
        quantity: Number(addForm.quantity) || 1, acquisition_date: addForm.acquisition_date || null,
        acquisition_mode: addForm.acquisition_mode, confidence: addForm.confidence,
        photo_path: addForm.photo_path, remarks: addForm.remarks || null,
      });
      toast.success("Asset recorded");
      qc.invalidateQueries({ queryKey: ["assets"] });
      resetAdd();
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  async function deleteAsset(a: AssetInstance) {
    if (!window.confirm(`Delete ${a.asset_type_name || "this asset"} for ${a.owner_name || "this owner"}?`)) return;
    try {
      await api.delete(`/assets/${a.id}`);
      toast.success("Asset deleted");
      qc.invalidateQueries({ queryKey: ["assets"] });
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

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
      qc.invalidateQueries({ queryKey: ["assets"] });
      setVerifyTarget(null);
    } catch (e: unknown) { toast.error(errMsg(e)); }
  }

  return (
    <div>
      <div className="mb-5 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Asset Management</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Durable assets held by farmers and FIGs — used to flag scheme useful-life cooldowns.
            {!canManage && " Read-only for your role."}
          </p>
        </div>
        {canManage && (
          <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
            <Plus size={16} weight="bold" /> Add Asset
          </button>
        )}
      </div>

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead>
            <tr>
              <th>Owner</th><th>Asset Type</th><th>Qty</th><th>Acquired</th><th>Mode</th>
              <th>Status</th><th>Verification</th><th>Verified By</th>{canManage && <th></th>}
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.id}>
                <td className="font-semibold">{a.owner_name || "—"} <span className="text-xs" style={{ color: "var(--text-muted)" }}>({a.owner_type})</span></td>
                <td>{a.asset_type_name || "—"}</td>
                <td>{a.quantity}</td>
                <td>{a.acquisition_date || "—"}</td>
                <td className="text-sm">{MODE_LABELS[a.acquisition_mode]}</td>
                <td>{statusBadge(a.status)}</td>
                <td>{verificationBadge(a.verification_status)}</td>
                <td className="text-sm">{a.last_verified_by_name || "—"}</td>
                {canManage && (
                  <td>
                    <div className="inline-flex gap-2 items-center">
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--success)" }}
                              onClick={() => openVerify(a)}>
                        <CheckCircle size={14} weight="bold" />Verify
                      </button>
                      <button className="text-xs inline-flex items-center gap-1" onClick={() => setLogTarget(a)}>
                        <ClockCounterClockwise size={14} weight="bold" />Log
                      </button>
                      {a.acquisition_mode !== "SCHEME_DISBURSEMENT" && (
                        <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                                onClick={() => deleteAsset(a)}>
                          <Trash size={14} weight="bold" />Delete
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {!isLoading && assets.length === 0 && (
              <tr><td colSpan={canManage ? 9 : 8} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No assets recorded yet</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Add Asset</h3>
              <button onClick={resetAdd}><X size={20} /></button>
            </div>
            <form onSubmit={submitAdd} className="p-5 grid gap-3 sm:grid-cols-2">
              <div><label className="label-tag">Owner Type</label>
                <select className="input mt-1" value={addForm.owner_type}
                        onChange={(e) => setAddForm({ ...addForm, owner_type: e.target.value as AssetOwnerType, owner_id: "", asset_type_id: "" })}>
                  <option value="FARMER">Farmer</option>
                  <option value="FIG">FIG</option>
                </select></div>
              <div><label className="label-tag">Owner</label>
                <select required className="input mt-1" value={addForm.owner_id}
                        onChange={(e) => setAddForm({ ...addForm, owner_id: e.target.value })}>
                  <option value="">Select…</option>
                  {addForm.owner_type === "FARMER"
                    ? farmers.map((f) => <option key={f.id} value={f.id}>{f.first_name} {f.last_name} ({f.farmer_code})</option>)
                    : figs.map((g) => <option key={g.id} value={g.id}>{g.fig_name} ({g.fig_code})</option>)}
                </select></div>
              <div className="sm:col-span-2"><label className="label-tag">Asset Type</label>
                <select required className="input mt-1" value={addForm.asset_type_id}
                        onChange={(e) => setAddForm({ ...addForm, asset_type_id: e.target.value })}>
                  <option value="">Select…</option>
                  {eligibleTypesForOwner.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select></div>
              <div><label className="label-tag">Quantity</label>
                <input type="number" min={1} className="input mt-1" value={addForm.quantity}
                       onChange={(e) => setAddForm({ ...addForm, quantity: e.target.value })} /></div>
              <div><label className="label-tag">Acquisition Date</label>
                <input type="date" className="input mt-1" value={addForm.acquisition_date}
                       onChange={(e) => setAddForm({ ...addForm, acquisition_date: e.target.value })} /></div>
              <div><label className="label-tag">Acquisition Mode</label>
                <select className="input mt-1" value={addForm.acquisition_mode}
                        onChange={(e) => setAddForm({ ...addForm, acquisition_mode: e.target.value as AssetAcquisitionMode })}>
                  <option value="LEGACY_SELF_DECLARED">Legacy Self-Declared</option>
                  <option value="SELF_PROCURED">Self-Procured</option>
                </select></div>
              <div><label className="label-tag">Confidence</label>
                <select className="input mt-1" value={addForm.confidence}
                        onChange={(e) => setAddForm({ ...addForm, confidence: e.target.value as AssetConfidence })}>
                  {CONFIDENCE_OPTIONS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select></div>
              <div className="sm:col-span-2">
                <label className="label-tag block mb-2">Evidence Photo</label>
                <FileUpload label="Upload photo" value={addForm.photo_path}
                            onChange={(p) => setAddForm({ ...addForm, photo_path: p })} accept=".jpg,.jpeg,.png,.webp"
                            category="assets" farmerIdentifier={addForm.owner_id} />
              </div>
              <div className="sm:col-span-2"><label className="label-tag">Remarks</label>
                <textarea className="input mt-1" rows={2} value={addForm.remarks}
                          onChange={(e) => setAddForm({ ...addForm, remarks: e.target.value })} /></div>
              <div className="sm:col-span-2 flex gap-2 justify-end mt-1">
                <button type="button" onClick={resetAdd} className="btn-secondary">Cancel</button>
                <button type="submit" className="btn-primary">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {verifyTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Verify · {verifyTarget.asset_type_name}</h3>
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

      {logTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Verification Log · {logTarget.asset_type_name}</h3>
              <button onClick={() => setLogTarget(null)}><X size={20} /></button>
            </div>
            <div className="p-5">
              {verificationLog.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>No verifications recorded yet.</p>
              ) : (
                <table className="seri-table">
                  <thead><tr><th>Date</th><th>Result</th><th>By</th><th>Remarks</th></tr></thead>
                  <tbody>
                    {verificationLog.map((l) => (
                      <tr key={l.id}>
                        <td>{new Date(l.checked_at).toLocaleDateString()}</td>
                        <td>{l.result}</td>
                        <td>{l.checked_by || "—"}</td>
                        <td className="text-sm">{l.remarks || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
