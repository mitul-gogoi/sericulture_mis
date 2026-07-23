"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Plus, X, GraduationCap, CheckCircle, XCircle, ClipboardText, Certificate as CertificateIcon, DownloadSimple } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { Scheme, Training, TrainingRosterEntry, TrainingCertificate } from "@/lib/types";

function errMsg(e: unknown) {
  return fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail);
}

function fileViewerUrl(path: string) {
  const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
}

const EMPTY_ROSTER: TrainingRosterEntry[] = [];

export default function TrainingsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isDA = user?.role === "DISTRICT_ADMIN";
  const isSA = user?.role === "STATE_ADMIN";

  const [open, setOpen] = useState(false);
  const [completeReq, setCompleteReq] = useState<Training | null>(null);
  const [approveDialog, setApproveDialog] = useState<{ training: Training; decision: "approved" | "rejected" } | null>(null);
  const [managing, setManaging] = useState<Training | null>(null);
  const [revokingCert, setRevokingCert] = useState<TrainingCertificate | null>(null);
  const [revokeReason, setRevokeReason] = useState("");

  const [form, setForm] = useState({ topic: "", description: "", scheme_id: "", proposed_from_date: "", proposed_to_date: "", proposed_venue: "", estimated_participants: 0 });
  const [comp, setComp] = useState({ actual_from_date: "", actual_to_date: "", actual_venue: "", actual_participants: 0, completion_report: "" });
  const [approveForm, setApproveForm] = useState({ approval_from_date: "", approval_to_date: "", approved_venue: "", approval_remarks: "" });
  const [rejectReason, setRejectReason] = useState("");
  const [attendanceEdits, setAttendanceEdits] = useState<Record<string, boolean>>({});

  const { data: reqs = [] } = useQuery<Training[]>({ queryKey: ["trainings"], queryFn: async () => (await api.get("/trainings/requests")).data });
  const { data: trainingSchemes = [] } = useQuery<Scheme[]>({
    queryKey: ["schemes-training-support"],
    queryFn: async () => (await api.get("/schemes", { params: { support_type: "Training" } })).data,
  });
  const { data: roster = EMPTY_ROSTER } = useQuery<TrainingRosterEntry[]>({
    queryKey: ["training-roster", managing?.id],
    queryFn: async () => (await api.get(`/trainings/${managing!.id}/roster`)).data,
    enabled: !!managing,
  });
  const { data: certificates = [] } = useQuery<TrainingCertificate[]>({
    queryKey: ["training-certs", managing?.id],
    queryFn: async () => (await api.get(`/trainings/${managing!.id}/certificates`)).data,
    enabled: !!managing,
  });

  useEffect(() => {
    setAttendanceEdits(Object.fromEntries(roster.map((r) => [r.beneficiary_id, r.is_present])));
  }, [roster]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/trainings/requests", { ...form, scheme_id: form.scheme_id || undefined });
      toast.success("Requested");
      setOpen(false);
      setForm({ topic: "", description: "", scheme_id: "", proposed_from_date: "", proposed_to_date: "", proposed_venue: "", estimated_participants: 0 });
      qc.invalidateQueries({ queryKey: ["trainings"] });
    } catch (e: unknown) { toast.error(errMsg(e)); }
  };

  const submitApproval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!approveDialog) return;
    const body: Record<string, unknown> = { request_id: approveDialog.training.id, decision: approveDialog.decision };
    if (approveDialog.decision === "approved") Object.assign(body, approveForm);
    else body.rejection_reason = rejectReason;
    try {
      await api.post("/trainings/approve", body);
      toast.success(approveDialog.decision === "approved" ? "Approved" : "Rejected");
      setApproveDialog(null);
      setApproveForm({ approval_from_date: "", approval_to_date: "", approved_venue: "", approval_remarks: "" });
      setRejectReason("");
      qc.invalidateQueries({ queryKey: ["trainings"] });
    } catch (e: unknown) { toast.error(errMsg(e)); }
  };

  const complete = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/trainings/complete", { request_id: completeReq!.id, ...comp });
      toast.success("Completed");
      setCompleteReq(null);
      qc.invalidateQueries({ queryKey: ["trainings"] });
    } catch (e: unknown) { toast.error(errMsg(e)); }
  };

  const markAttendanceMut = useMutation({
    mutationFn: () => api.post(`/trainings/${managing!.id}/attendance`, {
      items: Object.entries(attendanceEdits).map(([beneficiary_id, is_present]) => ({ beneficiary_id, is_present })),
    }),
    onSuccess: () => { toast.success("Attendance saved"); qc.invalidateQueries({ queryKey: ["training-roster", managing?.id] }); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const generateCertsMut = useMutation({
    mutationFn: () => api.post(`/trainings/${managing!.id}/certificates/generate`),
    onSuccess: (r) => {
      const created = r.data.created || [];
      toast.success(created.length ? `Generated ${created.length} certificate(s)` : "No new certificates to generate");
      qc.invalidateQueries({ queryKey: ["training-certs", managing?.id] });
      qc.invalidateQueries({ queryKey: ["training-roster", managing?.id] });
    },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const revokeCertMut = useMutation({
    mutationFn: () => api.post(`/trainings/certificates/${revokingCert!.id}/revoke`, { reason: revokeReason }),
    onSuccess: () => {
      toast.success("Certificate revoked");
      setRevokingCert(null);
      setRevokeReason("");
      qc.invalidateQueries({ queryKey: ["training-certs", managing?.id] });
    },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const canManage = (t: Training) => !!t.scheme_id && (t.status === "Approved" || t.status === "Completed");

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><h1 className="font-heading text-3xl font-extrabold">Training Management</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Requests, approvals, attendance & certificate tracking</p></div>
        {isDA && <button onClick={() => setOpen(true)} className="btn-primary inline-flex items-center gap-2"><Plus size={16} weight="bold" />Request</button>}
      </div>

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th>Topic</th><th>Scheme</th><th>Proposed dates</th><th>Venue</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {reqs.map((r) => (
              <tr key={r.id}>
                <td className="font-semibold"><GraduationCap size={14} weight="duotone" color="#2D5134" className="inline mr-1" />{r.topic}</td>
                <td>{r.scheme_id ? (trainingSchemes.find((s) => s.id === r.scheme_id)?.scheme_name || "Linked scheme") : "—"}</td>
                <td>{r.proposed_from_date} → {r.proposed_to_date}</td>
                <td>{r.proposed_venue}</td>
                <td>
                  {r.status === "Pending" && <span className="badge badge-warning">Pending</span>}
                  {r.status === "Approved" && <span className="badge badge-success">Approved</span>}
                  {r.status === "Rejected" && <span className="badge badge-error">Rejected</span>}
                  {r.status === "Completed" && <span className="badge badge-success">Completed</span>}
                </td>
                <td>
                  <div className="flex gap-2 items-center">
                    {isSA && r.status === "Pending" && (
                      <>
                        <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--success)" }} onClick={() => setApproveDialog({ training: r, decision: "approved" })}><CheckCircle size={14} weight="bold" />Approve</button>
                        <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }} onClick={() => setApproveDialog({ training: r, decision: "rejected" })}><XCircle size={14} weight="bold" />Reject</button>
                      </>
                    )}
                    {isDA && r.status === "Approved" && (
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--primary)" }} onClick={() => setCompleteReq(r)}><CheckCircle size={14} weight="bold" />Complete</button>
                    )}
                    {canManage(r) && (
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--primary)" }} onClick={() => setManaging(r)}><ClipboardText size={14} weight="bold" />Attendance & Certificates</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {reqs.length === 0 && <tr><td colSpan={6} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No requests</td></tr>}
          </tbody>
        </table>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}><h3 className="font-heading text-xl font-bold">Request training</h3><button onClick={() => setOpen(false)}><X size={20} /></button></div>
            <form onSubmit={create} className="p-5 grid grid-cols-2 gap-3">
              <div className="col-span-2"><label className="label-tag">Topic</label><input required className="input mt-1" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></div>
              <div className="col-span-2"><label className="label-tag">Description</label><textarea className="input mt-1" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
              <div className="col-span-2">
                <label className="label-tag">Funding Scheme (optional)</label>
                <select className="input mt-1" value={form.scheme_id} onChange={(e) => setForm({ ...form, scheme_id: e.target.value })}>
                  <option value="">No scheme (unfunded request)</option>
                  {trainingSchemes.map((s) => (<option key={s.id} value={s.id}>{s.scheme_name}</option>))}
                </select>
                {form.scheme_id && (
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Attendance and certificates will be tracked against this scheme's approved beneficiaries.
                  </p>
                )}
              </div>
              <div><label className="label-tag">From</label><input type="date" required className="input mt-1" value={form.proposed_from_date} onChange={(e) => setForm({ ...form, proposed_from_date: e.target.value })} /></div>
              <div><label className="label-tag">To</label><input type="date" required className="input mt-1" value={form.proposed_to_date} onChange={(e) => setForm({ ...form, proposed_to_date: e.target.value })} /></div>
              <div className="col-span-2"><label className="label-tag">Venue</label><input required className="input mt-1" value={form.proposed_venue} onChange={(e) => setForm({ ...form, proposed_venue: e.target.value })} /></div>
              <div><label className="label-tag">Participants</label><input type="number" className="input mt-1" value={form.estimated_participants} onChange={(e) => setForm({ ...form, estimated_participants: parseInt(e.target.value) })} /></div>
              <div className="col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary">Submit</button></div>
            </form>
          </div>
        </div>
      )}

      {approveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">{approveDialog.decision === "approved" ? "Approve" : "Reject"} · {approveDialog.training.topic}</h3>
              <button onClick={() => setApproveDialog(null)}><X size={20} /></button>
            </div>
            <form onSubmit={submitApproval} className="p-5 grid grid-cols-2 gap-3">
              {approveDialog.decision === "approved" ? (
                <>
                  <div><label className="label-tag">From</label><input type="date" required className="input mt-1" value={approveForm.approval_from_date} onChange={(e) => setApproveForm({ ...approveForm, approval_from_date: e.target.value })} /></div>
                  <div><label className="label-tag">To</label><input type="date" required className="input mt-1" value={approveForm.approval_to_date} onChange={(e) => setApproveForm({ ...approveForm, approval_to_date: e.target.value })} /></div>
                  <div className="col-span-2"><label className="label-tag">Venue</label><input required className="input mt-1" value={approveForm.approved_venue} onChange={(e) => setApproveForm({ ...approveForm, approved_venue: e.target.value })} /></div>
                  <div className="col-span-2"><label className="label-tag">Remarks</label><textarea className="input mt-1" rows={2} value={approveForm.approval_remarks} onChange={(e) => setApproveForm({ ...approveForm, approval_remarks: e.target.value })} /></div>
                </>
              ) : (
                <div className="col-span-2"><label className="label-tag">Reason</label><textarea required className="input mt-1" rows={3} value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} /></div>
              )}
              <div className="col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setApproveDialog(null)}>Cancel</button><button className="btn-primary">Confirm</button></div>
            </form>
          </div>
        </div>
      )}

      {completeReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}><h3 className="font-heading text-xl font-bold">Complete · {completeReq.topic}</h3><button onClick={() => setCompleteReq(null)}><X size={20} /></button></div>
            <form onSubmit={complete} className="p-5 grid grid-cols-2 gap-3">
              <div><label className="label-tag">From</label><input type="date" required className="input mt-1" value={comp.actual_from_date} onChange={(e) => setComp({ ...comp, actual_from_date: e.target.value })} /></div>
              <div><label className="label-tag">To</label><input type="date" required className="input mt-1" value={comp.actual_to_date} onChange={(e) => setComp({ ...comp, actual_to_date: e.target.value })} /></div>
              <div className="col-span-2"><label className="label-tag">Venue</label><input required className="input mt-1" value={comp.actual_venue} onChange={(e) => setComp({ ...comp, actual_venue: e.target.value })} /></div>
              <div><label className="label-tag">Participants</label><input type="number" required className="input mt-1" value={comp.actual_participants} onChange={(e) => setComp({ ...comp, actual_participants: parseInt(e.target.value) })} /></div>
              <div className="col-span-2"><label className="label-tag">Report</label><textarea required className="input mt-1" rows={3} value={comp.completion_report} onChange={(e) => setComp({ ...comp, completion_report: e.target.value })} /></div>
              <div className="col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setCompleteReq(null)}>Cancel</button><button className="btn-primary">Save</button></div>
            </form>
          </div>
        </div>
      )}

      {managing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-3xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">{managing.topic}</h3>
              <button onClick={() => setManaging(null)}><X size={20} /></button>
            </div>
            <div className="p-5 space-y-6">
              <div>
                <h4 className="font-heading font-bold mb-2 flex items-center gap-2"><ClipboardText size={16} weight="bold" />Roster & Attendance</h4>
                <table className="seri-table">
                  <thead><tr><th></th><th>Name</th><th>Code</th><th>Type</th></tr></thead>
                  <tbody>
                    {roster.map((r) => (
                      <tr key={r.beneficiary_id}>
                        <td>
                          <input type="checkbox" checked={!!attendanceEdits[r.beneficiary_id]}
                                 onChange={(e) => setAttendanceEdits((a) => ({ ...a, [r.beneficiary_id]: e.target.checked }))} />
                        </td>
                        <td className="font-semibold">{r.name}</td>
                        <td>{r.code}</td>
                        <td>{r.beneficiary_type}</td>
                      </tr>
                    ))}
                    {roster.length === 0 && <tr><td colSpan={4} className="text-center py-4" style={{ color: "var(--text-muted)" }}>No approved beneficiaries for this training's scheme yet.</td></tr>}
                  </tbody>
                </table>
                {roster.length > 0 && (
                  <div className="flex justify-end mt-2">
                    <button className="btn-primary btn-sm" disabled={markAttendanceMut.isPending} onClick={() => markAttendanceMut.mutate()}>Save Attendance</button>
                  </div>
                )}
              </div>

              {managing.status === "Completed" && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-heading font-bold flex items-center gap-2"><CertificateIcon size={16} weight="bold" />Certificates</h4>
                    <button className="btn-primary btn-sm" disabled={generateCertsMut.isPending} onClick={() => generateCertsMut.mutate()}>Generate Certificates</button>
                  </div>
                  <table className="seri-table">
                    <thead><tr><th>Certificate No.</th><th>Name</th><th>Issued</th><th>Status</th><th></th></tr></thead>
                    <tbody>
                      {certificates.map((c) => (
                        <tr key={c.id}>
                          <td className="font-mono text-xs">{c.certificate_number}</td>
                          <td>{c.beneficiary_name}</td>
                          <td>{new Date(c.issued_at).toLocaleDateString()}</td>
                          <td>{c.revoked ? <span className="badge badge-error" title={c.revoked_reason || ""}>Revoked</span> : <span className="badge badge-success">Active</span>}</td>
                          <td>
                            <div className="flex gap-2 items-center">
                              {c.pdf_path && (
                                <a href={fileViewerUrl(c.pdf_path)} target="_blank" rel="noreferrer" className="text-xs inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
                                  <DownloadSimple size={14} weight="bold" />Download
                                </a>
                              )}
                              {!c.revoked && (
                                <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }} onClick={() => setRevokingCert(c)}>
                                  <XCircle size={14} weight="bold" />Revoke
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                      {certificates.length === 0 && <tr><td colSpan={5} className="text-center py-4" style={{ color: "var(--text-muted)" }}>No certificates generated yet.</td></tr>}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {revokingCert && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-md">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
              <h3 className="font-heading text-xl font-bold">Revoke {revokingCert.certificate_number}</h3>
              <button onClick={() => { setRevokingCert(null); setRevokeReason(""); }}><X size={20} /></button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); revokeCertMut.mutate(); }} className="p-5 grid gap-3">
              <div><label className="label-tag">Reason</label><textarea required className="input mt-1" rows={3} value={revokeReason} onChange={(e) => setRevokeReason(e.target.value)} /></div>
              <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => { setRevokingCert(null); setRevokeReason(""); }}>Cancel</button><button className="btn-primary" disabled={revokeCertMut.isPending}>Confirm Revoke</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
