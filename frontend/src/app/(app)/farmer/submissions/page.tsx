"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Eye, Plus } from "@phosphor-icons/react";
import type { FarmerSubmission } from "@/lib/types";

const PAGE_SIZES = [10, 20, 50, 100];

export default function FarmerSubmissionsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data, isLoading } = useQuery<{ items: FarmerSubmission[]; total: number }>({
    queryKey: ["farmer-own-submissions", page, pageSize],
    queryFn: async () => (await api.get("/farmers/me/submissions", { params: { page, page_size: pageSize } })).data,
  });
  const items = data?.items || [];
  const total = data?.total || 0;

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">My submissions</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Your own monthly production/stock submissions</p>
        </div>
        <Link href="/farmer/submit" className="btn-primary inline-flex items-center gap-2">
          <Plus size={14} weight="bold" /> Submit this month
        </Link>
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="seri-table">
            <thead><tr><th>Submission ID</th><th>Month</th><th>Submitted</th><th></th></tr></thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td className="font-semibold">{r.submission_code}</td>
                  <td>{r.submission_month}</td>
                  <td>{new Date(r.submitted_at).toLocaleString()}</td>
                  <td>
                    <Link href={`/farmer/submissions/${r.id}`} className="inline-flex items-center gap-1 text-sm" style={{ color: "var(--primary)" }}>
                      <Eye size={14} weight="bold" /> View
                    </Link>
                  </td>
                </tr>
              ))}
              {!isLoading && items.length === 0 && (
                <tr><td colSpan={4} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No submissions yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {total > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t text-sm" style={{ borderColor: "var(--border)" }}>
            <span style={{ color: "var(--text-muted)" }}>
              Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <select className="input" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
                {PAGE_SIZES.map((s) => <option key={s} value={s}>{s} / page</option>)}
              </select>
              <button className="btn-secondary" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <button className="btn-secondary" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
