"use client";
import type { FigMember } from "@/lib/types";

export interface PresForm { farmer_id: string; mobile_no: string; password: string }

export function FigPresidentPanel({
  members, presForm, setPresForm, onSetPresident,
  resetPassword, setResetPassword, onResetPassword,
}: {
  members: FigMember[]; presForm: PresForm; setPresForm: (f: PresForm) => void; onSetPresident: () => void;
  resetPassword: string; setResetPassword: (v: string) => void; onResetPassword: () => void;
}) {
  const hasPresident = members?.some((m) => m.role === "President");
  return (
    <>
      <div className="border-t pt-4 mt-4" style={{ borderColor: "var(--border)" }}>
        <h4 className="font-heading font-bold mb-3">Set / Update President</h4>
        <div className="grid grid-cols-3 gap-2">
          <select className="input" value={presForm.farmer_id} onChange={(e) => {
            const member = members.find((m) => m.farmer_id === e.target.value);
            setPresForm({ ...presForm, farmer_id: e.target.value, mobile_no: member?.farmer?.mobile_no || "" });
          }}>
            <option value="">Choose member</option>
            {members.map((m) => <option key={m.farmer_id} value={m.farmer_id}>{m.farmer?.first_name} {m.farmer?.last_name}</option>)}
          </select>
          <input placeholder="Login mobile" className="input" value={presForm.mobile_no} onChange={(e) => setPresForm({ ...presForm, mobile_no: e.target.value })} />
          <input placeholder="Password" type="password" className="input" value={presForm.password} onChange={(e) => setPresForm({ ...presForm, password: e.target.value })} />
        </div>
        <button onClick={onSetPresident} disabled={!presForm.farmer_id || !presForm.mobile_no || !presForm.password} className="btn-primary mt-3">Save</button>
      </div>
      {hasPresident && (
        <div className="border-t pt-4 mt-4" style={{ borderColor: "var(--border)" }}>
          <h4 className="font-heading font-bold mb-3">Reset president password</h4>
          <div className="flex gap-2">
            <input placeholder="New password" type="password" className="input flex-1" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} />
            <button onClick={onResetPassword} disabled={!resetPassword} className="btn-primary">Reset</button>
          </div>
        </div>
      )}
    </>
  );
}
