"use client";
import type { FigMember } from "@/lib/types";

export interface PresForm { farmer_id: string }

export function FigPresidentPanel({
  members, presForm, setPresForm, onSetPresident,
}: {
  members: FigMember[]; presForm: PresForm; setPresForm: (f: PresForm) => void; onSetPresident: () => void;
}) {
  return (
    <div className="border-t pt-4 mt-4" style={{ borderColor: "var(--border)" }}>
      <h4 className="font-heading font-bold mb-3">Set / Update President</h4>
      <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
        The president's login is the same account created at farmer registration — no separate password to set here.
      </p>
      <div className="flex gap-2">
        <select className="input flex-1" value={presForm.farmer_id} onChange={(e) => setPresForm({ farmer_id: e.target.value })}>
          <option value="">Choose member</option>
          {members.map((m) => <option key={m.farmer_id} value={m.farmer_id}>{m.farmer?.first_name} {m.farmer?.last_name}</option>)}
        </select>
        <button onClick={onSetPresident} disabled={!presForm.farmer_id} className="btn-primary">Save</button>
      </div>
    </div>
  );
}
