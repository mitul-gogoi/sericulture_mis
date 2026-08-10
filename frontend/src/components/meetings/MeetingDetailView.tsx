"use client";
import { useState } from "react";
import { Paperclip, CheckCircle, Minus } from "@phosphor-icons/react";
import { ViewField } from "@/components/ViewField";
import type { MeetingDetail } from "@/lib/types";

function fileViewerUrl(path: string) {
  const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
}

export function MeetingDetailView({ detail, actions }: { detail: MeetingDetail; actions?: React.ReactNode }) {
  const { meeting, attendance, entries } = detail;
  const farmerIds = Array.from(new Set(entries.map((e) => e.farmer_id)));
  const [selectedFarmerId, setSelectedFarmerId] = useState(farmerIds[0] || "");

  const farmerName = (id: string) =>
    entries.find((e) => e.farmer_id === id)?.farmer_name ||
    attendance.find((a) => a.farmer_id === id)?.farmer_name || "—";

  const presentCount = attendance.filter((a) => a.is_present).length;
  const totalActual = entries.reduce((sum, e) => sum + (e.output.actual_yield || 0), 0);
  const totalEarning = entries.reduce(
    (sum, e) => sum + (e.output.earning || 0) + e.byproducts.reduce((s, b) => s + (b.earning || 0), 0),
    0
  );
  const inputCount = entries.reduce((sum, e) => sum + e.inputs.length, 0);
  const byproductCount = entries.reduce((sum, e) => sum + e.byproducts.length, 0);
  const selectedEntries = entries.filter((e) => e.farmer_id === selectedFarmerId);

  return (
    <div>
      <nav className="flex gap-4 mb-4 text-sm font-semibold" style={{ color: "var(--primary)" }}>
        <a href="#meeting">Meeting</a>
        <a href="#attendance">Attendance</a>
        <a href="#submission">Submission</a>
        <a href="#review">Review</a>
      </nav>

      <section id="meeting" className="card p-5 mb-4">
        <h3 className="font-heading text-lg font-bold mb-4">Meeting</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ViewField label="Meeting title" value={meeting.meeting_title} />
          <ViewField label="Date" value={meeting.meeting_date} />
          <ViewField label="Time" value={meeting.meeting_time} />
          <ViewField label="Venue" value={meeting.meeting_venue} />
          <ViewField label="Next meeting" value={meeting.next_meeting_date} />
          <ViewField
            label="Minutes of meeting"
            value={
              meeting.minutes_path ? (
                <a href={fileViewerUrl(meeting.minutes_path)} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
                  <Paperclip size={14} weight="bold" /> Download minutes
                </a>
              ) : "No minutes uploaded"
            }
          />
        </div>
        {meeting.meeting_details && (
          <div className="mt-4">
            <ViewField label="Details" value={meeting.meeting_details} />
          </div>
        )}
      </section>

      <section id="attendance" className="card overflow-hidden mb-4">
        <h3 className="font-heading text-lg font-bold p-5 pb-0">Attendance</h3>
        <div className="overflow-x-auto p-5 pt-3">
          <table className="seri-table">
            <thead><tr><th>Member</th><th>Mobile</th><th>Present</th></tr></thead>
            <tbody>
              {attendance.map((a) => (
                <tr key={a.farmer_id}>
                  <td className="font-semibold">{a.farmer_name}</td>
                  <td>{a.mobile}</td>
                  <td>
                    {a.is_present
                      ? <CheckCircle size={18} weight="fill" style={{ color: "var(--success)" }} />
                      : <Minus size={18} style={{ color: "var(--text-muted)" }} />}
                  </td>
                </tr>
              ))}
              {attendance.length === 0 && <tr><td colSpan={3} className="text-center py-6" style={{ color: "var(--text-muted)" }}>No attendance recorded</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section id="submission" className="card p-5 mb-4">
        <h3 className="font-heading text-lg font-bold mb-4">Submission</h3>
        {entries.length === 0 ? (
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>No yield entries recorded.</div>
        ) : (
          <div className="flex flex-col md:flex-row gap-4">
            <div className="w-full md:w-56 flex-shrink-0 border rounded overflow-y-auto max-h-48 md:max-h-[500px]" style={{ borderColor: "var(--border)" }}>
              {farmerIds.map((fid) => (
                <button key={fid} type="button" onClick={() => setSelectedFarmerId(fid)}
                        className="w-full text-left px-3 py-2 text-sm border-b"
                        style={{ borderColor: "var(--border)", background: fid === selectedFarmerId ? "var(--sidebar)" : "transparent" }}>
                  {farmerName(fid)}
                </button>
              ))}
            </div>
            <div className="flex-1 min-w-0">
              {selectedEntries.map((e) => (
                <div key={e.stap_id} className="mb-6">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold">{e.activity_name}</span>
                    <span className={`badge ${e.is_primary_stage ? "badge-success" : "badge-muted"}`}>
                      {e.is_primary_stage ? "Primary Activity" : "Secondary Activity"}
                    </span>
                  </div>
                  <div className="overflow-x-auto mb-3">
                    <table className="seri-table">
                      <thead><tr><th>Product</th><th>Planned</th><th>Actual</th><th>Sold Qty</th><th>Sold Rate</th><th>Stock</th><th>Next Plan</th><th>Loss Reason</th></tr></thead>
                      <tbody>
                        <tr>
                          <td className="font-semibold">{e.output.product_name}</td>
                          <td>{e.output.planned_yield}</td>
                          <td>{e.output.actual_yield}</td>
                          <td>{e.output.sold_quantity}</td>
                          <td>{e.output.sold_rate}</td>
                          <td>{e.output.stock_balance}</td>
                          <td>{e.output.next_month_plan}</td>
                          <td>{e.output.loss_reason_name || "—"}</td>
                        </tr>
                        {e.byproducts.map((b, i) => (
                          <tr key={i}>
                            <td>{b.product_name} <span className="badge badge-muted text-xs">Byproduct</span></td>
                            <td>{b.planned_quantity}</td>
                            <td>{b.quantity}</td>
                            <td>{b.sold_quantity}</td>
                            <td>{b.sold_rate}</td>
                            <td>{b.stock_balance}</td>
                            <td>{b.next_month_plan}</td>
                            <td>{b.loss_reason_name || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {e.inputs.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="seri-table">
                        <thead><tr><th>Input</th><th>Quantity</th><th>Source</th><th>Scheme</th></tr></thead>
                        <tbody>
                          {e.inputs.map((inp, i) => (
                            <tr key={i}>
                              <td>{inp.product_name} <span style={{ color: "var(--text-muted)" }}>({inp.unit_of_measure})</span></td>
                              <td>{inp.quantity}</td>
                              <td>{inp.source_type_name || "—"}</td>
                              <td>{inp.scheme_name || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <section id="review" className="mb-4">
        <h3 className="font-heading text-lg font-bold mb-4">Review</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <div className="card p-4"><div className="label-tag">Attendance</div><div className="font-semibold text-lg mt-1">{presentCount} / {attendance.length} present</div></div>
          <div className="card p-4"><div className="label-tag">Total actual yield</div><div className="font-semibold text-lg mt-1">{totalActual.toLocaleString()}</div></div>
          <div className="card p-4"><div className="label-tag">Total earning</div><div className="font-semibold text-lg mt-1">₹{totalEarning.toLocaleString()}</div></div>
          <div className="card p-4"><div className="label-tag">Input entries</div><div className="font-semibold text-lg mt-1">{inputCount}</div></div>
          <div className="card p-4"><div className="label-tag">Byproduct entries</div><div className="font-semibold text-lg mt-1">{byproductCount}</div></div>
        </div>
        {actions}
      </section>
    </div>
  );
}
