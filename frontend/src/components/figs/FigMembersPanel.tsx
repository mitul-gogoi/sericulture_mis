"use client";
import type { FigMember, Farmer } from "@/lib/types";

export function FigMembersPanel({
  members, canManage, detailUnassignedFarmers, memberFarmer, setMemberFarmer, onAddMember,
}: {
  members: FigMember[]; canManage: boolean; detailUnassignedFarmers: Farmer[];
  memberFarmer: string; setMemberFarmer: (v: string) => void; onAddMember: () => void;
}) {
  return (
    <>
      <h4 className="font-heading font-bold mb-3">Members</h4>
      <table className="seri-table mb-4">
        <thead><tr><th>Name</th><th>Mobile</th><th>Role</th></tr></thead>
        <tbody>
          {members?.map((m) => (
            <tr key={m.id}>
              <td className="font-semibold">{m.farmer ? `${m.farmer.first_name} ${m.farmer.last_name}` : "—"}</td>
              <td>{m.farmer?.mobile_no}</td>
              <td><span className={`badge ${m.role === "President" ? "badge-success" : "badge-muted"}`}>{m.role}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      {canManage && (
        <div className="border-t pt-4 mt-4" style={{ borderColor: "var(--border)" }}>
          <h4 className="font-heading font-bold mb-3">Add member</h4>
          <div className="flex gap-2">
            <select className="input flex-1" value={memberFarmer} onChange={(e) => setMemberFarmer(e.target.value)}>
              <option value="">Select farmer</option>
              {detailUnassignedFarmers.map((f) => <option key={f.id} value={f.id}>{f.first_name} {f.last_name} · {f.mobile_no}</option>)}
            </select>
            <button onClick={onAddMember} disabled={!memberFarmer} className="btn-primary">Add</button>
          </div>
        </div>
      )}
    </>
  );
}
