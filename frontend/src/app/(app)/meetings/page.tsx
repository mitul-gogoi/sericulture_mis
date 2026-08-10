"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Paperclip, Eye, CheckCircle, XCircle } from "@phosphor-icons/react";
import { toast } from "sonner";
import { ExportButtons } from "@/components/ExportButtons";
import type { SubmissionStatusRow, FpSubmissionHistoryRow, PendingCorrectionRow } from "@/lib/types";

const currentMonth = () => new Date().toISOString().slice(0, 7);
const PAGE_SIZES = [10, 20, 50, 100];

const fileViewerUrl = (path: string) => {
  const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
};

function ResubmissionRequests() {
  const qc = useQueryClient();
  const searchParams = useSearchParams();
  const [justFocused, setJustFocused] = useState(false);
  const { data: rows = [] } = useQuery<PendingCorrectionRow[]>({
    queryKey: ["pending-corrections"],
    queryFn: async () => (await api.get("/meetings/corrections/pending")).data,
  });

  useEffect(() => {
    if (searchParams.get("focus") !== "resubmission-requests" || rows.length === 0) return;
    const el = document.getElementById("resubmission-requests");
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setJustFocused(true);
    const t = setTimeout(() => setJustFocused(false), 2000);
    return () => clearTimeout(t);
  }, [searchParams, rows.length]);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["pending-corrections"] });
    qc.invalidateQueries({ queryKey: ["submission-status"] });
  };

  const approve = async (row: PendingCorrectionRow) => {
    if (!confirm(`Approve ${row.fig_name}'s resubmission for ${row.month}? This will overwrite the live submission.`)) return;
    try {
      await api.post(`/meetings/corrections/${row.correction_id}/accept`);
      toast.success("Correction approved");
      refresh();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const reject = async (row: PendingCorrectionRow) => {
    const reason = prompt("Reason for rejection?");
    if (!reason) return;
    try {
      await api.post(`/meetings/corrections/${row.correction_id}/reject`, { rejection_reason: reason });
      toast.success("Correction rejected");
      refresh();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  if (rows.length === 0) return null;

  return (
    <div id="resubmission-requests" className="card overflow-hidden mb-5" style={justFocused ? { boxShadow: "0 0 0 3px var(--primary)" } : undefined}>
      <div className="p-4 border-b">
        <h2 className="font-heading text-lg font-bold">Resubmission Requests</h2>
        <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>FIG Presidents' corrections awaiting your review</p>
      </div>
      <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>FIG</th><th>District</th><th>Month</th><th>Re-submitted on</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.correction_id}>
                <td className="font-semibold">{r.fig_name}</td>
                <td>{r.district_name}</td>
                <td>{r.month}</td>
                <td>{new Date(r.submitted_on).toLocaleDateString()}</td>
                <td>
                  <div className="flex items-center gap-3">
                    <Link href={`/meetings/${r.meeting_id}`} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--primary)" }}>
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

export default function MeetingsPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState(currentMonth());
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const isFP = user?.role === "FIG_PRESIDENT";
  const isSA = user?.role === "STATE_ADMIN";

  const { data: statusData } = useQuery<{ items: SubmissionStatusRow[]; total: number }>({
    queryKey: ["submission-status", month, page, pageSize],
    queryFn: async () => (await api.get("/meetings/submission-status", { params: { month, page, page_size: pageSize } })).data,
    enabled: !!user && !isFP,
  });
  const { data: historyData } = useQuery<{ items: FpSubmissionHistoryRow[]; total: number }>({
    queryKey: ["submission-history", page, pageSize],
    queryFn: async () => (await api.get("/meetings/submission-history", { params: { page, page_size: pageSize } })).data,
    enabled: !!user && isFP,
  });

  if (isFP) {
    const rows = historyData?.items ?? [];
    const total = historyData?.total ?? 0;
    const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
    const showingTo = Math.min(page * pageSize, total);
    return (
      <div>
        <div className="mb-5">
          <h1 className="font-heading text-3xl font-extrabold">Submission history</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Past monthly meeting submissions for your FIG</p>
        </div>
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
          <table className="seri-table">
            <thead><tr><th>Month</th><th>Meeting Title</th><th>Submission Date</th><th>Venue</th><th>Re-submitted</th><th>Minutes</th><th></th></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.meeting_id}-${i}`}>
                  <td>{r.month}</td>
                  <td className="font-semibold">{r.meeting_title}</td>
                  <td>{new Date(r.submitted_on).toLocaleDateString()}</td>
                  <td>{r.venue}</td>
                  <td>{r.re_submitted === "Yes" ? <span className="badge badge-warning">Yes</span> : "No"}</td>
                  <td>
                    {r.minutes_path ? (
                      <a href={fileViewerUrl(r.minutes_path)} target="_blank" rel="noopener noreferrer"
                         className="inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
                        <Paperclip size={12} weight="bold" /> Download
                      </a>
                    ) : "—"}
                  </td>
                  <td>
                    <Link href={`/meetings/${r.meeting_id}`} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--primary)" }}>
                      <Eye size={14} weight="bold" /> View
                    </Link>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={7} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No submissions yet</td></tr>}
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
            <ExportButtons report="submission-history" params={{}} />
          </div>
        </div>
      </div>
    );
  }

  const rows = statusData?.items ?? [];
  const total = statusData?.total ?? 0;
  const submittedCount = rows.filter((r) => r.status === "Submitted").length;
  const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const showingTo = Math.min(page * pageSize, total);

  return (
    <div>
      {isSA && <ResubmissionRequests />}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Monthly submission status</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {submittedCount} of {total} FIGs submitted for {month}
          </p>
        </div>
      </div>
      <div className="card p-4 mb-4 flex items-center gap-3">
        <label className="label-tag">Month</label>
        <input type="month" data-testid="submission-status-month" className="input max-w-xs" value={month}
               onChange={(e) => { setMonth(e.target.value); setPage(1); }} />
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>FIG</th>{isSA && <th>District</th>}<th>Status</th><th>Submitted on</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.fig_id}>
                <td className="font-semibold">{r.fig_name}</td>
                {isSA && <td>{r.district_name}</td>}
                <td>{r.status === "Submitted" ? <span className="badge badge-success">Submitted</span> : <span className="badge badge-warning">Pending</span>}</td>
                <td>{r.submitted_on ? new Date(r.submitted_on).toLocaleDateString() : "—"}</td>
                <td>
                  {r.meeting_id && (
                    <Link href={`/meetings/${r.meeting_id}`} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--primary)" }}>
                      <Eye size={14} weight="bold" /> View
                    </Link>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={isSA ? 5 : 4} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No FIGs formed yet for this month</td></tr>}
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
          <ExportButtons report="submission-status" params={{ month }} />
        </div>
      </div>
    </div>
  );
}
