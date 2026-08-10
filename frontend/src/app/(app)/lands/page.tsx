"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, MapPin, X, CheckCircle, XCircle, Eye } from "@phosphor-icons/react";
import { toast } from "sonner";
import { ExportButtons } from "@/components/ExportButtons";
import { MIN_GPS_POINTS, type Land, type LandsPage, type LandGpsDraft } from "@/lib/types";

const GpsMap = dynamic(() => import("./GpsMap"), { ssr: false, loading: () => <div style={{ height: 420, background: "#F8F7F4" }} className="flex items-center justify-center">Loading map…</div> });

const PAGE_SIZES = [10, 20, 50, 100];

export default function LandsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const [gpsLand, setGpsLand] = useState<Land | null>(null);
  const [viewingLand, setViewingLand] = useState<Land | null>(null);
  const [points, setPoints] = useState<{ latitude: number; longitude: number }[]>([]);
  const [latInput, setLatInput] = useState("");
  const [lngInput, setLngInput] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState(() => searchParams.get("status") || "");
  const [draftPrefillFarmer, setDraftPrefillFarmer] = useState<string | null>(null);

  const { data: reportData } = useQuery<LandsPage>({
    queryKey: ["lands-report", page, pageSize, statusFilter],
    queryFn: async () => (await api.get("/lands", { params: { page, page_size: pageSize, ...(statusFilter ? { status: statusFilter } : {}) } })).data,
  });

  // Solo farmers capture GPS directly (live); FIG-member farmers stage a private draft their
  // FIG President reviews/finalizes instead — resolved from the farmer's own active-FIG status.
  const { data: ownProfile } = useQuery<{ fig_id: string | null }>({
    queryKey: ["farmer-me"], queryFn: async () => (await api.get("/farmers/me")).data,
    enabled: user?.role === "FARMER",
  });
  const isSoloFarmer = user?.role === "FARMER" && !ownProfile?.fig_id;
  const isMemberFarmer = user?.role === "FARMER" && !!ownProfile?.fig_id;
  const lands = reportData?.items ?? [];
  const total = reportData?.total ?? 0;
  const pendingCount = reportData?.pending_count ?? 0;
  const overlapCount = reportData?.overlap_count ?? 0;
  const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const showingTo = Math.min(page * pageSize, total);

  const addManualPoint = () => {
    const lat = parseFloat(latInput);
    const lng = parseFloat(lngInput);
    if (Number.isNaN(lat) || lat < -90 || lat > 90) return toast.error("Enter a valid latitude (-90 to 90)");
    if (Number.isNaN(lng) || lng < -180 || lng > 180) return toast.error("Enter a valid longitude (-180 to 180)");
    setPoints([...points, { latitude: lat, longitude: lng }]);
    setLatInput(""); setLngInput("");
  };

  const removePoint = (idx: number) => setPoints(points.filter((_, i) => i !== idx));

  const closeGps = () => { setGpsLand(null); setPoints([]); setLatInput(""); setLngInput(""); setDraftPrefillFarmer(null); };

  // FIG President's existing per-row capture action — opening it now also checks for a
  // member's own self-captured draft and pre-fills from it (editable) if one exists.
  const openGpsDialog = async (land: Land) => {
    setGpsLand(land);
    setDraftPrefillFarmer(null);
    if (user?.role === "FIG_PRESIDENT") {
      try {
        const { data } = await api.get<LandGpsDraft | null>(`/lands/${land.id}/gps/draft`);
        if (data) { setPoints(data.points); setDraftPrefillFarmer(land.farmer_name || "this member"); return; }
      } catch { /* no draft or not permitted to read one — fall through to normal open */ }
    }
    setPoints(land.gps_points || []);
  };

  const submitGps = async () => {
    if (points.length < MIN_GPS_POINTS) return toast.error(`Mark at least ${MIN_GPS_POINTS} points`);
    try {
      const { data } = await api.post("/lands/gps", { farmer_land_id: gpsLand!.id, points });
      toast.success(`Area ${data.area_bigha.toFixed(2)} bigha · overlap: ${data.overlap_detected ? "yes" : "no"}`);
      closeGps();
      qc.invalidateQueries({ queryKey: ["lands-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  // FIG-member farmer's own capture never goes live directly — it saves as a private draft
  // that only becomes visible when their FIG President opens the same dialog above.
  const saveDraft = async () => {
    try {
      await api.post(`/lands/${gpsLand!.id}/gps/draft`, { points });
      toast.success("Saved — your FIG President will review and submit this.");
      closeGps();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const verify = async (land: Land, decision: "verified" | "failed") => {
    const reason = decision === "failed" ? prompt("Reason for GPS re-capture request?") || "" : "";
    const override = land.overlap_detected && decision === "verified" ? confirm("Overlap detected — verify anyway?") : false;
    try { await api.post("/lands/verify", { farmer_land_id: land.id, decision, reason, override_overlap: override });
      toast.success("Status updated"); qc.invalidateQueries({ queryKey: ["lands-report"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  // Only District Admin can act (Verify/Fail) — State Admin and FIG President can view
  // everything (including View Details) but never mutate a submission's status.
  const canViewDetails = user?.role === "STATE_ADMIN" || user?.role === "DISTRICT_ADMIN" || user?.role === "FIG_PRESIDENT";
  const canVerifyReject = user?.role === "DISTRICT_ADMIN";

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><h1 className="font-heading text-3xl font-extrabold">Land & GIS</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>GPS mapping & verification for existing land parcels — land details are added when a farmer is registered</p></div>
      </div>

      {canViewDetails && (pendingCount > 0 || overlapCount > 0) && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="card p-4 flex items-center justify-between" style={{ background: pendingCount > 0 ? "#FBEFD6" : undefined }}>
            <div>
              <div className="label-tag">GPS Verification Queue</div>
              <div className="font-heading text-2xl font-extrabold mt-1">{pendingCount}</div>
            </div>
            <span className={`badge ${pendingCount > 0 ? "badge-warning" : "badge-muted"}`}>Pending action</span>
          </div>
          <div className="card p-4 flex items-center justify-between" style={{ background: overlapCount > 0 ? "#F5DDDB" : undefined }}>
            <div>
              <div className="label-tag">Overlap detected</div>
              <div className="font-heading text-2xl font-extrabold mt-1">{overlapCount}</div>
            </div>
            <span className={`badge ${overlapCount > 0 ? "badge-error" : "badge-muted"}`}>Review carefully</span>
          </div>
        </div>
      )}

      {statusFilter && (
        <div className="flex items-center gap-2 mb-3 text-sm" style={{ color: "var(--text-muted)" }}>
          Showing: {statusFilter} only
          <button className="font-semibold" style={{ color: "var(--primary)" }} onClick={() => setStatusFilter("")}>Clear filter</button>
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr>
            <th>Dag No</th><th>Patta No</th><th>Farmer Code</th><th>Farmer Name</th>
            <th>Area (Bigha)</th><th>Area (Hectare)</th><th>Village Name</th><th>Panchayat</th>
            <th>Development Block</th><th>Sericulture Circle</th><th>District</th>
            <th>Status</th><th>Overlap</th><th></th>
          </tr></thead>
          <tbody>
            {lands.map((l) => (
              <tr key={l.id}>
                <td>{l.dag_no || "—"}</td>
                <td>{l.patta_no || "—"}</td>
                <td className="font-mono text-xs">{l.farmer_code || "—"}</td>
                <td className="font-semibold whitespace-nowrap">{l.farmer_name || "—"}</td>
                <td>{l.land_area_bigha ? l.land_area_bigha.toFixed(2) : "—"}</td>
                <td>{l.land_area_hectare ? l.land_area_hectare.toFixed(4) : "—"}</td>
                <td>{l.village_name || "—"}</td>
                <td>{l.gaon_panchayat || "—"}</td>
                <td>{l.development_block || "—"}</td>
                <td>{l.circle_name || "—"}</td>
                <td>{l.district_name || "—"}</td>
                <td>
                  {l.gps_verified === "Verified" && <span className="badge badge-success">Verified</span>}
                  {l.gps_verified === "Pending" && <span className="badge badge-warning">Pending</span>}
                  {l.gps_verified === "Failed" && <span className="badge badge-error">Failed</span>}
                  {l.gps_verified === "Not Submitted" && <span className="badge badge-muted">Not submitted</span>}
                  {l.has_gps_draft && (
                    <span className="badge badge-warning ml-1" title="Member has self-captured GPS — open Capture GPS to review">Member captured</span>
                  )}
                </td>
                <td>{l.overlap_detected ? <span className="badge badge-error">Yes ({l.overlapping_parcel_ids?.length})</span> : <span className="badge badge-muted">—</span>}</td>
                <td className="flex items-center gap-2 whitespace-nowrap">
                  {canViewDetails && (
                    <button className="btn-secondary inline-flex items-center gap-1 text-xs px-2 py-1"
                            onClick={() => setViewingLand(l)} data-testid={`view-land-${l.id}`}>
                      <Eye size={14} weight="bold" />View Details
                    </button>
                  )}
                  {l.gps_verified !== "Verified" && user?.role === "FIG_PRESIDENT" && (
                    <button className="btn-secondary inline-flex items-center gap-1 text-sm" onClick={() => openGpsDialog(l)}><MapPin size={14} />GPS</button>
                  )}
                  {l.gps_verified !== "Verified" && user?.role === "FARMER" && (
                    <button className="btn-secondary inline-flex items-center gap-1 text-sm" onClick={() => openGpsDialog(l)}><MapPin size={14} />Capture GPS</button>
                  )}
                  {canVerifyReject && l.gps_verified === "Pending" && (
                    <>
                      <button className="btn-secondary inline-flex items-center gap-1 text-xs px-2 py-1" onClick={() => verify(l, "verified")} data-testid={`verify-${l.id}`}><CheckCircle size={14} weight="bold" />Approve</button>
                      <button className="btn-secondary inline-flex items-center gap-1 text-xs px-2 py-1" onClick={() => verify(l, "failed")} data-testid={`fail-${l.id}`}><XCircle size={14} weight="bold" />Re-Capture GPS</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {lands.length === 0 && <tr><td colSpan={14} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No land parcels yet</td></tr>}
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
          <ExportButtons report="lands" params={{}} />
        </div>
      </div>

      {viewingLand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <div>
                <h3 className="font-heading text-xl font-bold">Land details · {viewingLand.farmer_name || "—"}</h3>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Dag {viewingLand.dag_no || "—"} / Patta {viewingLand.patta_no || "—"} · GPS boundary points (read-only)
                </div>
              </div>
              <button onClick={() => setViewingLand(null)}><X size={20} /></button>
            </div>
            <div className="p-5">
              {(viewingLand.gps_points?.length ?? 0) > 0 ? (
                <>
                  <div className="mb-4 border rounded overflow-hidden" style={{ borderColor: "var(--border)" }}>
                    <table className="seri-table">
                      <thead><tr><th>#</th><th>Latitude</th><th>Longitude</th></tr></thead>
                      <tbody>
                        {viewingLand.gps_points!.map((p, i) => (
                          <tr key={i}><td>{i + 1}</td><td>{p.latitude.toFixed(6)}</td><td>{p.longitude.toFixed(6)}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <GpsMap points={viewingLand.gps_points!} onAdd={() => {}} readOnly />
                </>
              ) : (
                <div className="text-center py-8" style={{ color: "var(--text-muted)" }}>No GPS points submitted yet</div>
              )}
            </div>
          </div>
        </div>
      )}

      {gpsLand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <div><h3 className="font-heading text-xl font-bold">GPS submission · {gpsLand.farmer_name || "—"}</h3>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>Enter each boundary point's coordinates (min {MIN_GPS_POINTS}), or press and hold on the map.</div></div>
              <button onClick={closeGps}><X size={20} /></button>
            </div>
            <div className="p-5">
              {draftPrefillFarmer && (
                <div className="card p-3 mb-4 text-sm" style={{ background: "#FBEFD6" }}>
                  Pre-filled from {draftPrefillFarmer}'s self-capture — review, adjust if needed, and submit below.
                </div>
              )}
              {isMemberFarmer && (
                <div className="card p-3 mb-4 text-sm" style={{ background: "#FBEFD6" }}>
                  You're a FIG member — this won't go live immediately. Saving here stages it for your FIG President to review and submit.
                </div>
              )}
              <div className="flex items-end gap-2 mb-4">
                <div>
                  <label className="label-tag">Latitude</label>
                  <input type="number" step="any" min={-90} max={90} className="input mt-1 w-40" placeholder="e.g. 26.1445"
                         data-testid="gps-lat-input" value={latInput} onChange={(e) => setLatInput(e.target.value)} />
                </div>
                <div>
                  <label className="label-tag">Longitude</label>
                  <input type="number" step="any" min={-180} max={180} className="input mt-1 w-40" placeholder="e.g. 91.7362"
                         data-testid="gps-lng-input" value={lngInput} onChange={(e) => setLngInput(e.target.value)} />
                </div>
                <button type="button" className="btn-primary inline-flex items-center gap-1" onClick={addManualPoint} data-testid="gps-add-point">
                  <Plus size={16} weight="bold" />Add point
                </button>
              </div>

              {points.length > 0 && (
                <div className="mb-4 border rounded overflow-hidden" style={{ borderColor: "var(--border)" }}>
                  <table className="seri-table">
                    <thead><tr><th>#</th><th>Latitude</th><th>Longitude</th><th></th></tr></thead>
                    <tbody>
                      {points.map((p, i) => (
                        <tr key={i}>
                          <td>{i + 1}</td>
                          <td>{p.latitude.toFixed(6)}</td>
                          <td>{p.longitude.toFixed(6)}</td>
                          <td><button type="button" onClick={() => removePoint(i)} style={{ color: "var(--error)" }}><X size={16} weight="bold" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <GpsMap points={points} onAdd={(p) => setPoints([...points, p])} />
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm">{points.length} points marked</div>
                <div className="flex gap-2">
                  <button className="btn-secondary" onClick={() => setPoints([])}>Clear</button>
                  {isMemberFarmer ? (
                    <button className="btn-primary" onClick={saveDraft} data-testid="save-gps-draft">Save for FIG President</button>
                  ) : (
                    <button className="btn-primary" onClick={submitGps} data-testid="submit-gps">Submit GPS</button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
