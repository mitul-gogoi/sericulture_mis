"use client";
import { useState } from "react";
import { X } from "@phosphor-icons/react";
import { toast } from "sonner";
import api, { fmtErr } from "@/lib/api";

export function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error("New password and confirmation do not match");
      return;
    }
    setSaving(true);
    try {
      await api.post("/auth/change-password", { old_password: oldPassword, new_password: newPassword });
      toast.success("Password changed successfully");
      onClose();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">Change Password</h3>
          <button onClick={onClose} data-testid="change-password-close"><X size={20} /></button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-3">
          <div>
            <label className="label-tag">Current Password</label>
            <input required type="password" className="input mt-1" value={oldPassword}
                   onChange={(e) => setOldPassword(e.target.value)} data-testid="change-password-old" />
          </div>
          <div>
            <label className="label-tag">New Password</label>
            <input required type="password" minLength={6} className="input mt-1" value={newPassword}
                   onChange={(e) => setNewPassword(e.target.value)} data-testid="change-password-new" />
          </div>
          <div>
            <label className="label-tag">Confirm New Password</label>
            <input required type="password" minLength={6} className="input mt-1" value={confirmPassword}
                   onChange={(e) => setConfirmPassword(e.target.value)} data-testid="change-password-confirm" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={saving} data-testid="change-password-submit">
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
