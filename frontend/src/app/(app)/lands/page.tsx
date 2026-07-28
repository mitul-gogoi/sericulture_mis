"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, MapPin, X, CheckCircle, XCircle } from "@phosphor-icons/react";
import { toast } from "sonner";
import { MIN_GPS_POINTS, type Land } from "@/lib/types";

const GpsMap = dynamic(() => import("./GpsMap"), { ssr: false, loading: () => <div style={{ height: 420, background: "#F8F7F4" }} className="flex items-center justify-center">Loading map…</div> });

export default function LandsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [gpsLand, setGpsLand] = useState<Land | null>(null);
  const [points, setPoints] = useState<{ latitude: number; longitude: number }[]>([]);
  const [latInput, setLatInput] = useState("");
  const [lngInput, setLngInput] = useState("");

  const { data: lands = [] } = useQuery<Land[]>({ queryKey: ["lands"], queryFn: async () => (await api.get("/lands")).data });

  const addManualPoint = () => {
    const lat = parseFloat(latInput);
    const lng = parseFloat(lngInput);
    if (Number.isNaN(lat) || lat < -90 || lat > 90) return toast.error("Enter a valid latitude (-90 to 90)");
    if (Number.isNaN(lng) || lng < -180 || lng > 180) return toast.error("Enter a valid longitude (-180 to 180)");
    setPoints([...points, { latitude: lat, longitude: lng }]);
    setLatInput(""); setLngInput("");
  };

  const removePoint = (idx: number) => setPoints(points.filter((_, i) => i !== idx));

  const closeGps = () => { setGpsLand(null); setPoints([]); setLatInput(""); setLngInput(""); };

  const submitGps = async () => {
    if (points.length < MIN_GPS_POINTS) return toast.error(`Mark at least ${MIN_GPS_POINTS} points`);
    try {
      const { data } = await api.post("/lands/gps", { farmer_land_id: gpsLand!.id, points });
      toast.success(`Area ${data.area_bigha.toFixed(2)} bigha · overlap: ${data.overlap_detected ? "yes" : "no"}`);
      closeGps();
      qc.invalidateQueries({ queryKey: ["lands"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const verify = async (land: Land, decision: "verified" | "failed") => {
    const reason = decision === "failed" ? prompt("Reason for failure?") || "" : "";
    const override = land.overlap_detected && decision === "verified" ? confirm("Overlap detected — verify anyway?") : false;
    try { await api.post("/lands/verify", { farmer_land_id: land.id, decision, reason, override_overlap: override });
      toast.success("Status updated"); qc.invalidateQueries({ queryKey: ["lands"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const canVerify = user?.role === "DISTRICT_ADMIN" || user?.role === "STATE_ADMIN";
  const pendingCount = lands.filter((l) => l.gps_verified === "Pending").length;
  const overlapCount = lands.filter((l) => l.overlap_detected).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><h1 className="font-heading text-3xl font-extrabold">Land & GIS</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>GPS mapping & verification for existing land parcels — land details are added when a farmer is registered</p></div>
      </div>

      {canVerify && (pendingCount > 0 || overlapCount > 0) && (
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

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Farmer</th><th>Dag/Patta</th><th>Area (bigha)</th><th>Hectare</th><th>Status</th><th>Overlap</th><th></th></tr></thead>
          <tbody>
            {lands.map((l) => (
              <tr key={l.id}>
                <td className="font-semibold">{l.farmer?.first_name} {l.farmer?.last_name}</td>
                <td>{l.dag_no || "—"} / {l.patta_no || "—"}</td>
                <td>{l.land_area_bigha ? l.land_area_bigha.toFixed(2) : "—"}</td>
                <td>{l.land_area_hectare ? l.land_area_hectare.toFixed(4) : "—"}</td>
                <td>
                  {l.gps_verified === "Verified" && <span className="badge badge-success">Verified</span>}
                  {l.gps_verified === "Pending" && <span className="badge badge-warning">Pending</span>}
                  {l.gps_verified === "Failed" && <span className="badge badge-error">Failed</span>}
                  {l.gps_verified === "Not Submitted" && <span className="badge badge-muted">Not submitted</span>}
                </td>
                <td>{l.overlap_detected ? <span className="badge badge-error">Yes ({l.overlapping_parcel_ids?.length})</span> : <span className="badge badge-muted">—</span>}</td>
                <td className="flex items-center gap-2">
                  {l.gps_verified !== "Verified" && user?.role === "FIG_PRESIDENT" && (
                    <button className="btn-secondary inline-flex items-center gap-1 text-sm" onClick={() => { setGpsLand(l); setPoints(l.gps_points || []); }}><MapPin size={14} />GPS</button>
                  )}
                  {canVerify && l.gps_verified === "Pending" && (
                    <>
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--success)" }} onClick={() => verify(l, "verified")} data-testid={`verify-${l.id}`}><CheckCircle size={14} weight="bold" />Verify</button>
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }} onClick={() => verify(l, "failed")}><XCircle size={14} weight="bold" />Fail</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {lands.length === 0 && <tr><td colSpan={7} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No land parcels yet</td></tr>}
          </tbody>
        </table>
        </div>
      </div>

      {gpsLand && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <div><h3 className="font-heading text-xl font-bold">GPS submission · {gpsLand.farmer?.first_name} {gpsLand.farmer?.last_name}</h3>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>Enter each boundary point's coordinates (min {MIN_GPS_POINTS}), or press and hold on the map.</div></div>
              <button onClick={closeGps}><X size={20} /></button>
            </div>
            <div className="p-5">
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
                  <button className="btn-primary" onClick={submitGps} data-testid="submit-gps">Submit GPS</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
