"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Paperclip } from "@phosphor-icons/react";
import type { Fig, Meeting, District } from "@/lib/types";

const currentMonth = () => new Date().toISOString().slice(0, 7);

export default function MeetingsPage() {
  const { user } = useAuth();
  const [month, setMonth] = useState(currentMonth());
  const isFP = user?.role === "FIG_PRESIDENT";

  const { data: meetings = [] } = useQuery<Meeting[]>({
    queryKey: ["meetings", isFP ? "all" : month],
    queryFn: async () => (await api.get("/meetings", { params: isFP ? {} : { month } })).data,
    enabled: !!user,
  });
  const { data: figs = [] } = useQuery<Fig[]>({
    queryKey: ["figs-submission-status"],
    queryFn: async () => (await api.get("/figs")).data,
    enabled: !isFP,
  });
  const { data: districts = [] } = useQuery<District[]>({
    queryKey: ["districts"],
    queryFn: async () => (await api.get("/master/districts")).data,
    enabled: user?.role === "STATE_ADMIN",
  });

  const fileViewerUrl = (path: string) => {
    const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
    return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
  };

  if (isFP) {
    return (
      <div>
        <div className="mb-5">
          <h1 className="font-heading text-3xl font-extrabold">Submission history</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Past monthly meeting submissions for your FIG</p>
        </div>
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
          <table className="seri-table">
            <thead><tr><th>Month</th><th>Meeting title</th><th>Date</th><th>Venue</th><th>Minutes</th></tr></thead>
            <tbody>
              {meetings.map((m) => (
                <tr key={m.id}>
                  <td>{m.meeting_month}</td>
                  <td className="font-semibold">{m.meeting_title}</td>
                  <td>{m.meeting_date}</td>
                  <td>{m.meeting_venue}</td>
                  <td>
                    {m.minutes_path ? (
                      <a href={fileViewerUrl(m.minutes_path)} target="_blank" rel="noopener noreferrer"
                         className="inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
                        <Paperclip size={12} weight="bold" /> Download
                      </a>
                    ) : "—"}
                  </td>
                </tr>
              ))}
              {meetings.length === 0 && <tr><td colSpan={5} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No submissions yet</td></tr>}
            </tbody>
          </table>
          </div>
        </div>
      </div>
    );
  }

  const meetingByFig = new Map(meetings.map((m) => [m.fig_id, m]));
  const districtName = (id: string) => districts.find((d) => d.id === id)?.district_name || "—";
  const isSA = user?.role === "STATE_ADMIN";
  const submittedCount = figs.filter((f) => meetingByFig.has(f.id)).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="font-heading text-3xl font-extrabold">Monthly submission status</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {submittedCount} of {figs.length} FIGs submitted for {month}
          </p>
        </div>
      </div>
      <div className="card p-4 mb-4 flex items-center gap-3">
        <label className="label-tag">Month</label>
        <input type="month" data-testid="submission-status-month" className="input max-w-xs" value={month} onChange={(e) => setMonth(e.target.value)} />
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
        <table className="seri-table">
          <thead><tr><th>FIG</th>{isSA && <th>District</th>}<th>Status</th><th>Submitted on</th></tr></thead>
          <tbody>
            {figs.map((f) => {
              const m = meetingByFig.get(f.id);
              return (
                <tr key={f.id}>
                  <td className="font-semibold">{f.fig_name} <span className="font-mono text-xs" style={{ color: "var(--text-muted)" }}>· {f.fig_code}</span></td>
                  {isSA && <td>{districtName(f.district_id)}</td>}
                  <td>{m ? <span className="badge badge-success">Submitted</span> : <span className="badge badge-warning">Pending</span>}</td>
                  <td>{m ? new Date(m.submitted_at).toLocaleDateString() : "—"}</td>
                </tr>
              );
            })}
            {figs.length === 0 && <tr><td colSpan={isSA ? 4 : 3} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No FIGs registered yet</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
