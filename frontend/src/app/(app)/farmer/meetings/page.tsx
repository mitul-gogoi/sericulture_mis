"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Paperclip, Eye } from "@phosphor-icons/react";
import type { FpSubmissionHistoryRow } from "@/lib/types";

const fileViewerUrl = (path: string) => {
  const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
};

export default function FarmerMeetingsPage() {
  const { data: rows = [] } = useQuery<FpSubmissionHistoryRow[]>({
    queryKey: ["farmer-meetings"],
    queryFn: async () => (await api.get("/farmers/me/meetings")).data,
  });

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
              {rows.length === 0 && <tr><td colSpan={7} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No submissions yet — this may be because you aren't currently part of a FIG</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
