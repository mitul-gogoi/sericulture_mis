"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { UsersThree, Warning, CheckCircle, XCircle, Hourglass } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { Scheme, Beneficiary, SchemeCandidate, SchemeCandidatesResponse } from "@/lib/types";

interface BulkRow {
  selected: boolean;
  benefit_amount: string;
  cooldown_override_reason: string;
}

function errMsg(e: unknown) {
  return fmtErr((e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail);
}

export default function BeneficiariesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isDA = user?.role === "DISTRICT_ADMIN";
  const isSA = user?.role === "STATE_ADMIN";
  const canRegister = user?.role === "STATE_ADMIN" || isDA;

  const [schemeId, setSchemeId] = useState("");
  const [rows, setRows] = useState<Record<string, BulkRow>>({});
  const [selectedPending, setSelectedPending] = useState<Record<string, boolean>>({});
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>({});

  const { data: schemes = [] } = useQuery<Scheme[]>({
    queryKey: ["schemes-ben"],
    // include_archived so beneficiary rows tied to a since-archived scheme still resolve a name
    queryFn: async () => (await api.get("/schemes", { params: { all: true, include_archived: true } })).data,
  });
  const { data: beneficiaries = [] } = useQuery<Beneficiary[]>({
    queryKey: ["beneficiaries"],
    queryFn: async () => (await api.get("/schemes/beneficiaries")).data,
  });
  const { data: pending = [] } = useQuery<Beneficiary[]>({
    queryKey: ["beneficiaries-pending"],
    queryFn: async () => (await api.get("/schemes/beneficiaries", { params: { status: "PENDING_APPROVAL" } })).data,
    enabled: isSA,
  });
  const { data: candidateData } = useQuery<SchemeCandidatesResponse>({
    queryKey: ["scheme-candidates", schemeId],
    queryFn: async () => (await api.get(`/schemes/${schemeId}/candidates`)).data,
    enabled: isDA && !!schemeId,
  });

  const selectedScheme = schemes.find((s) => s.id === schemeId) || null;
  const schemeName = (id: string) => schemes.find((s) => s.id === id)?.scheme_name || "—";

  function rowFor(id: string): BulkRow {
    return rows[id] || { selected: false, benefit_amount: "0", cooldown_override_reason: "" };
  }
  function updateRow(id: string, patch: Partial<BulkRow>) {
    setRows((r) => ({ ...r, [id]: { ...rowFor(id), ...patch } }));
  }

  const bulkMut = useMutation({
    mutationFn: () => {
      const items = (candidateData?.candidates || [])
        .filter((c) => rowFor(c.id).selected)
        .map((c) => ({
          beneficiary_type: candidateData!.beneficiary_kind,
          farmer_id: candidateData!.beneficiary_kind === "FARMER" ? c.id : undefined,
          fig_id: candidateData!.beneficiary_kind === "FIG" ? c.id : undefined,
          benefit_amount: Number(rowFor(c.id).benefit_amount) || 0,
          cooldown_override_reason: rowFor(c.id).cooldown_override_reason || undefined,
        }));
      return api.post("/schemes/beneficiaries/bulk", { scheme_id: schemeId, items });
    },
    onSuccess: (r) => {
      const { created, errors } = r.data;
      if (created.length) toast.success(`Registered ${created.length} beneficiar${created.length === 1 ? "y" : "ies"}`);
      if (errors.length) toast.error(`${errors.length} row(s) failed — see console`);
      if (errors.length) console.warn("Bulk registration errors:", errors);
      setRows({});
      qc.invalidateQueries({ queryKey: ["beneficiaries"] });
      qc.invalidateQueries({ queryKey: ["scheme-candidates", schemeId] });
    },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  function invalidatePending() {
    qc.invalidateQueries({ queryKey: ["beneficiaries"] });
    qc.invalidateQueries({ queryKey: ["beneficiaries-pending"] });
  }

  const approveOneMut = useMutation({
    mutationFn: (id: string) => api.post(`/schemes/beneficiaries/${id}/approve`),
    onSuccess: () => { toast.success("Approved"); invalidatePending(); },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });
  const rejectOneMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/schemes/beneficiaries/${id}/reject`, { rejection_reason: reason }),
    onSuccess: (_r, { id }) => {
      toast.success("Rejected");
      setRejectReasons((r) => { const n = { ...r }; delete n[id]; return n; });
      invalidatePending();
    },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });
  const approveBulkMut = useMutation({
    mutationFn: () => api.post("/schemes/beneficiaries/approve/bulk", {
      beneficiary_ids: Object.keys(selectedPending).filter((id) => selectedPending[id]),
    }),
    onSuccess: (r) => {
      const { approved, errors } = r.data;
      if (approved.length) toast.success(`Approved ${approved.length}`);
      if (errors.length) toast.error(`${errors.length} row(s) failed — see console`);
      if (errors.length) console.warn("Bulk approval errors:", errors);
      setSelectedPending({});
      invalidatePending();
    },
    onError: (e: unknown) => toast.error(errMsg(e)),
  });

  const pendingBeneficiaryLabel = (b: Beneficiary) =>
    b.beneficiary_type === "FIG"
      ? (b.fig ? `${b.fig.fig_name} (${b.fig.fig_code})` : "—")
      : (b.farmer ? `${b.farmer.first_name} ${b.farmer.last_name} (${b.farmer.farmer_code})` : "—");
  const selectedPendingCount = Object.values(selectedPending).filter(Boolean).length;

  const selectedCount = Object.values(rows).filter((r) => r.selected).length;
  const candidates = candidateData?.candidates || [];

  function candidateLabel(c: SchemeCandidate) {
    return candidateData?.beneficiary_kind === "FIG"
      ? `${c.name} (${c.fig_code})` : `${c.name} (${c.farmer_code})`;
  }

  return (
    <div data-testid="schemes-ben-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Beneficiaries</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {isDA
              ? "Pick a scheme that targets your district, then select who actually receives it from the matched candidate pool."
              : "Farmers and FIGs who received scheme benefits."}
          </p>
        </div>
      </div>

      {isSA && (
        <div className="card p-5 mb-5" data-testid="schemes-ben-pending">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-heading text-lg font-bold flex items-center gap-2">
              <Hourglass size={16} weight="bold" />Pending Approval ({pending.length})
            </h2>
            {pending.length > 0 && (
              <button className="btn-primary btn-sm" disabled={selectedPendingCount === 0 || approveBulkMut.isPending}
                      onClick={() => approveBulkMut.mutate()} data-testid="schemes-ben-approve-bulk">
                Approve {selectedPendingCount || ""} selected
              </button>
            )}
          </div>
          <table className="seri-table">
            <thead>
              <tr><th></th><th>Beneficiary</th><th>Scheme</th><th className="text-right">Amount (₹)</th><th>Reject reason</th><th></th></tr>
            </thead>
            <tbody>
              {pending.map((b) => (
                <tr key={b.id} data-testid={`schemes-ben-pending-${b.id}`}>
                  <td>
                    <input type="checkbox" checked={!!selectedPending[b.id]}
                           onChange={(e) => setSelectedPending((s) => ({ ...s, [b.id]: e.target.checked }))} />
                  </td>
                  <td className="font-semibold">{pendingBeneficiaryLabel(b)}</td>
                  <td>{schemeName(b.scheme_id)}</td>
                  <td className="text-right">{(b.benefit_amount || 0).toLocaleString()}</td>
                  <td>
                    <input className="input w-56" placeholder="Required to reject"
                           value={rejectReasons[b.id] || ""}
                           onChange={(e) => setRejectReasons((r) => ({ ...r, [b.id]: e.target.value }))} />
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--success)" }}
                              disabled={approveOneMut.isPending}
                              onClick={() => approveOneMut.mutate(b.id)}>
                        <CheckCircle size={14} weight="bold" />Approve
                      </button>
                      <button className="text-xs inline-flex items-center gap-1" style={{ color: "var(--error)" }}
                              disabled={rejectOneMut.isPending || !rejectReasons[b.id]}
                              onClick={() => rejectOneMut.mutate({ id: b.id, reason: rejectReasons[b.id] })}>
                        <XCircle size={14} weight="bold" />Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {pending.length === 0 && (
                <tr><td colSpan={6} className="text-center py-6" style={{ color: "var(--text-muted)" }}>Nothing pending approval.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {isDA && (
        <div className="card p-5 mb-5" data-testid="schemes-ben-candidates">
          <label className="block mb-3">
            <span className="label-tag block mb-1">Scheme</span>
            <select className="input w-full max-w-md" value={schemeId}
                    onChange={(e) => { setSchemeId(e.target.value); setRows({}); }}
                    data-testid="schemes-ben-input-scheme">
              <option value="">Select a scheme targeting your district…</option>
              {schemes.filter((s) => s.is_active).map((s) => (<option key={s.id} value={s.id}>{s.scheme_name}</option>))}
            </select>
          </label>

          {schemeId && candidateData && (
            <>
              <table className="seri-table">
                <thead>
                  <tr>
                    <th></th><th>{candidateData.beneficiary_kind === "FIG" ? "FIG" : "Farmer"}</th>
                    <th>Cooldown</th><th>Benefit Amount (₹)</th><th>Override Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c) => {
                    const row = rowFor(c.id);
                    const blocked = c.cooldown && !c.cooldown.eligible;
                    return (
                      <tr key={c.id} data-testid={`schemes-ben-candidate-${c.id}`}>
                        <td>
                          <input type="checkbox" checked={row.selected} disabled={c.already_beneficiary}
                                 onChange={(e) => updateRow(c.id, { selected: e.target.checked })} />
                        </td>
                        <td className="font-semibold">
                          {candidateLabel(c)}
                          {c.already_beneficiary && <span className="badge badge-muted ml-2">Already registered</span>}
                        </td>
                        <td>
                          {!c.cooldown ? "—" : c.cooldown.eligible
                            ? <span className="badge badge-success inline-flex items-center gap-1"><CheckCircle size={12} weight="bold" />Eligible</span>
                            : <span className="badge badge-error inline-flex items-center gap-1" title={c.cooldown.reason || ""}>
                                <Warning size={12} weight="bold" />Until {c.cooldown.cooldown_until}
                              </span>}
                        </td>
                        <td>
                          <input type="number" className="input w-28" value={row.benefit_amount}
                                 onChange={(e) => updateRow(c.id, { benefit_amount: e.target.value })} />
                        </td>
                        <td>
                          {blocked && row.selected && (
                            <input className="input w-56" placeholder="Required to override cooldown"
                                   value={row.cooldown_override_reason}
                                   onChange={(e) => updateRow(c.id, { cooldown_override_reason: e.target.value })} />
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {candidates.length === 0 && (
                    <tr><td colSpan={5} className="text-center py-6" style={{ color: "var(--text-muted)" }}>
                      No {selectedScheme?.beneficiary_kind === "FIG" ? "FIGs" : "farmers"} in your district match this scheme's criteria.
                    </td></tr>
                  )}
                </tbody>
              </table>
              {candidates.length > 0 && (
                <div className="flex justify-end mt-3">
                  <button className="btn-primary" disabled={selectedCount === 0 || bulkMut.isPending}
                          onClick={() => bulkMut.mutate()} data-testid="schemes-ben-bulk-submit">
                    Register {selectedCount || ""} selected
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="seri-table">
          <thead><tr><th><UsersThree size={14} weight="bold" className="inline mr-1" />Beneficiary</th><th>Scheme</th><th className="text-right">Amount (₹)</th><th>Material</th><th>Date</th><th>Status</th></tr></thead>
          <tbody>
            {beneficiaries.map((b) => (
              <tr key={b.id}>
                <td className="font-semibold">
                  {b.beneficiary_type === "FIG"
                    ? (b.fig ? b.fig.fig_name : "—")
                    : (b.farmer ? `${b.farmer.first_name} ${b.farmer.last_name}` : "—")}
                  {b.beneficiary_type === "FIG" && b.fig?.fig_code && <span className="text-xs ml-2" style={{ color: "var(--text-muted)" }}>{b.fig.fig_code}</span>}
                  {b.beneficiary_type === "FARMER" && b.farmer?.farmer_code && <span className="text-xs ml-2" style={{ color: "var(--text-muted)" }}>{b.farmer.farmer_code}</span>}
                </td>
                <td>{schemeName(b.scheme_id)}</td>
                <td className="text-right">{(b.benefit_amount || 0).toLocaleString()}</td>
                <td>{b.benefit_material || "—"}</td>
                <td>{b.disbursement_date || "—"}</td>
                <td>
                  {b.status === "PENDING_APPROVAL" && <span className="badge badge-warning">Pending Approval</span>}
                  {b.status === "APPROVED" && <span className="badge badge-success">Approved</span>}
                  {b.status === "REJECTED" && <span className="badge badge-error" title={b.rejection_reason || ""}>Rejected</span>}
                </td>
              </tr>
            ))}
            {beneficiaries.length === 0 && <tr><td colSpan={6} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No beneficiaries registered yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
