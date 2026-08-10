"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Eye, CheckCircle, XCircle } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { FarmerSubmissionListRow, PendingFarmerCorrectionRow } from "@/lib/types";

const currentMonth = () => new Date().toISOString().slice(0, 7);
const PAGE_SIZES = [10, 20, 50, 100];

function PendingFarmerResubmissions() {
  const qc = useQueryClient();
  const { data: rows = [] } = useQuery<PendingFarmerCorrectionRow[]>({
    queryKey: ["pending-farmer-corrections"],
    queryFn: async () => (await api.get("/farmer-submissions/corrections/pending")).data,
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["pending-farmer-corrections"] });
    qc.invalidateQueries({ queryKey: ["farmer-submissions-list"] });
  };

  const approve = async (row: PendingFarmerCorrectionRow) => {
    if (!confirm(`Approve ${row.farmer_name}'s resubmission for ${row.month}? This will overwrite the live submission.`)) return;
    try {
      await api.post(`/farmer-submissions/corrections/${row.correction_id}/accept`);
      toast.success("Resubmission approved");
      refresh();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const reject = async (row: PendingFarmerCorrectionRow) => {
    const reason = prompt("Reason for rejection?");
    if (!reason) return;
    try {
      await api.post(`/farmer-submissions/corrections/${row.correction_id}/reject`, { rejection_reason: reason });
      toast.success("Resubmission rejected");
      refresh();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  if (rows.length === 0) return null;

  return (
    <div className="card overflow-hidden mb-5">
      <div className="p-4 border-b">
        <h2 className="font-heading text-lg font-bold">Pending Farmer Resubmission Requests</h2>
        <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>Solo farmers' corrections awaiting your review</p>
      </div>
      <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>Farmer</th><th>District</th><th>Month</th><th>Re-submitted on</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.correction_id}>
                <td className="font-semibold">{r.farmer_name} <span style={{ color: "var(--text-muted)" }}>({r.farmer_code})</span></td>
                <td>{r.district_name}</td>
                <td>{r.month}</td>
                <td>{new Date(r.submitted_on).toLocaleDateString()}</td>
                <td>
                  <div className="flex items-center gap-3">
                    <Link href={`/farmer-submissions/${r.farmer_submission_id}`} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--primary)" }}>
                      <Eye size={14} weight="bold" /> View
                    </Link>
                    <button onClick={() => approve(r)} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--success)" }}>
                      <CheckCircle size={14} weight="bold" /> Approve
                    </button>
                    <button onClick={() => reject(r)} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--error)" }}>
                      <XCircle size={14} weight="bold" /> Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function FarmerSubmissionsAdminPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState(currentMonth());
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const isDA = user?.role === "DISTRICT_ADMIN";

  const { data } = useQuery<{ items: FarmerSubmissionListRow[]; total: number }>({
    queryKey: ["farmer-submissions-list", month, page, pageSize],
    queryFn: async () => (await api.get("/farmer-submissions", { params: { month, page, page_size: pageSize } })).data,
    enabled: !!user,
  });
  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const showingTo = Math.min(page * pageSize, total);

  return (
    <div>
      {isDA && <PendingFarmerResubmissions />}
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">Individual Farmer Submissions</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Monthly production/stock submitted directly by farmers with no active FIG</p>
      </div>
      <div className="card p-4 mb-4 flex items-center gap-3">
        <label className="label-tag">Month</label>
        <input type="month" className="input max-w-xs" value={month} onChange={(e) => { setMonth(e.target.value); setPage(1); }} />
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="seri-table">
            <thead><tr><th>Submission ID</th><th>Farmer</th>{!isDA && <th>District</th>}<th>Submitted on</th><th></th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.submission_id}>
                  <td className="font-semibold">{r.submission_code}</td>
                  <td>{r.farmer_name} <span style={{ color: "var(--text-muted)" }}>({r.farmer_code})</span></td>
                  {!isDA && <td>{r.district_name}</td>}
                  <td>{new Date(r.submitted_on).toLocaleDateString()}</td>
                  <td>
                    <Link href={`/farmer-submissions/${r.submission_id}`} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--primary)" }}>
                      <Eye size={14} weight="bold" /> View
                    </Link>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={isDA ? 4 : 5} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No individual submissions for this month</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
        <div className="text-sm" style={{ color: "var(--text-muted)" }}>Showing {showingFrom}–{showingTo} of {total}</div>
        <div className="flex items-center gap-3">
          <select className="input" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
            {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
          </select>
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
          <button className="btn-secondary" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
    </div>
  );
}
