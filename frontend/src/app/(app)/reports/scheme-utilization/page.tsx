"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { ExportButtons } from "@/components/ExportButtons";

interface DistrictAlloc { district_id: string; district_name: string; allocated_rs: number; utilised_rs: number; remaining_rs: number; }
interface SchemeUtil {
  scheme_id: string; scheme_name: string; total_budget_rs: number;
  allocated_rs: number; utilised_rs: number; remaining_rs: number; districts: DistrictAlloc[];
}

export default function SchemeUtilizationPage() {
  const { data: rows = [] } = useQuery<SchemeUtil[]>({
    queryKey: ["scheme-utilization"],
    queryFn: async () => (await api.get("/reports/scheme-utilization")).data,
  });

  return (
    <div>
      <div className="mb-5 flex items-start justify-between flex-wrap gap-3">
        <div><h1 className="font-heading text-3xl font-extrabold">Scheme utilization</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Budget vs. allocated vs. disbursed, per scheme and district</p></div>
        <ExportButtons report="scheme-utilization" />
      </div>

      {rows.map((s) => {
        const pct = s.allocated_rs ? Math.round((s.utilised_rs / s.allocated_rs) * 1000) / 10 : 0;
        return (
          <div key={s.scheme_id} className="card p-5 mb-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="font-heading text-lg font-bold">{s.scheme_name}</div>
                <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Total budget ₹{s.total_budget_rs.toLocaleString()}</div>
              </div>
              <div className="flex gap-4 text-sm">
                <div><span className="label-tag block">Allocated</span>₹{s.allocated_rs.toLocaleString()}</div>
                <div><span className="label-tag block">Utilised</span>₹{s.utilised_rs.toLocaleString()}</div>
                <div><span className="label-tag block">Remaining</span>₹{s.remaining_rs.toLocaleString()}</div>
                <div><span className="label-tag block">% Utilised</span>{pct}%</div>
              </div>
            </div>
            {s.districts.length > 0 ? (
              <table className="seri-table mt-4">
                <thead><tr><th>District</th><th>Allocated</th><th>Utilised</th><th>Remaining</th></tr></thead>
                <tbody>
                  {s.districts.map((d) => (
                    <tr key={d.district_id}>
                      <td>{d.district_name}</td>
                      <td>₹{d.allocated_rs.toLocaleString()}</td>
                      <td>₹{d.utilised_rs.toLocaleString()}</td>
                      <td>₹{d.remaining_rs.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-sm mt-3" style={{ color: "var(--text-muted)" }}>No allocations yet</div>
            )}
          </div>
        );
      })}
      {rows.length === 0 && <div className="card p-8 text-center" style={{ color: "var(--text-muted)" }}>No active schemes</div>}
    </div>
  );
}
