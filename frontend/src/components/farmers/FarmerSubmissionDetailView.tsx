"use client";
import type { FarmerSubmissionDetail } from "@/lib/types";

export function FarmerSubmissionDetailView({ detail, actions }: { detail: FarmerSubmissionDetail; actions?: React.ReactNode }) {
  const { submission, entries } = detail;
  const totalActual = entries.reduce((sum, e) => sum + (e.output.actual_yield || 0), 0);
  const totalEarning = entries.reduce(
    (sum, e) => sum + (e.output.earning || 0) + e.byproducts.reduce((s, b) => s + (b.earning || 0), 0),
    0
  );
  const inputCount = entries.reduce((sum, e) => sum + e.inputs.length, 0);
  const byproductCount = entries.reduce((sum, e) => sum + e.byproducts.length, 0);

  return (
    <div>
      <nav className="flex gap-4 mb-4 text-sm font-semibold" style={{ color: "var(--primary)" }}>
        <a href="#submission">Submission</a>
        <a href="#review">Review</a>
      </nav>

      <section className="card p-5 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div><div className="label-tag">Submission ID</div><div className="font-semibold mt-1">{submission.submission_code}</div></div>
          <div><div className="label-tag">Month</div><div className="font-semibold mt-1">{submission.submission_month}</div></div>
          <div><div className="label-tag">Submitted</div><div className="font-semibold mt-1">{new Date(submission.submitted_at).toLocaleString()}</div></div>
        </div>
      </section>

      <section id="submission" className="card p-5 mb-4">
        <h3 className="font-heading text-lg font-bold mb-4">Submission</h3>
        {entries.length === 0 ? (
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>No yield entries recorded.</div>
        ) : (
          entries.map((e) => (
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
          ))
        )}
      </section>

      <section id="review" className="mb-4">
        <h3 className="font-heading text-lg font-bold mb-4">Review</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
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
