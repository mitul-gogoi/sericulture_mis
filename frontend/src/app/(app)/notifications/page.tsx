"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Bell, PaperPlaneTilt, X, Paperclip } from "@phosphor-icons/react";
import { toast } from "sonner";
import FileUpload from "@/components/FileUpload";
import type { Notification, User, District } from "@/lib/types";

export default function NotificationsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"inbox" | "sent">("inbox");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<{ title: string; details: string; recipient_type: string; attachment_path: string | null; recipient_ids: string[] }>(
    { title: "", details: "", recipient_type: "ALL_FP", attachment_path: null, recipient_ids: [] },
  );

  const { data: inbox = [] } = useQuery<Notification[]>({ queryKey: ["inbox"], queryFn: async () => (await api.get("/notifications/inbox")).data });
  const { data: sent = [] } = useQuery<Notification[]>({
    queryKey: ["sent"], queryFn: async () => (await api.get("/notifications/sent")).data,
    enabled: user?.role !== "FIG_PRESIDENT",
  });

  // Lists for "Selected" recipient pickers
  const needsDAList = form.recipient_type === "SELECTED_DA";
  const needsFPList = form.recipient_type === "SELECTED_FP";
  const { data: das = [] } = useQuery<User[]>({
    queryKey: ["users-da-picker"], queryFn: async () => (await api.get("/users", { params: { role: "DISTRICT_ADMIN" } })).data,
    enabled: needsDAList,
  });
  const { data: fps = [] } = useQuery<User[]>({
    queryKey: ["users-fp-picker"], queryFn: async () => (await api.get("/users", { params: { role: "FIG_PRESIDENT" } })).data,
    enabled: needsFPList,
  });
  const { data: districts = [] } = useQuery<District[]>({ queryKey: ["districts"], queryFn: async () => (await api.get("/master/districts")).data, enabled: needsDAList || needsFPList });
  const distName = (id?: string | null) => districts.find((d) => d.id === id)?.district_name || "—";

  const send = async (e: React.FormEvent) => { e.preventDefault();
    if ((needsDAList || needsFPList) && form.recipient_ids.length === 0) {
      return toast.error("Pick at least one recipient");
    }
    try {
      await api.post("/notifications", form);
      toast.success("Sent"); setOpen(false);
      setForm({ title: "", details: "", recipient_type: "ALL_FP", attachment_path: null, recipient_ids: [] });
      qc.invalidateQueries({ queryKey: ["inbox"] }); qc.invalidateQueries({ queryKey: ["sent"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const markRead = async (id: string) => { await api.post(`/notifications/read/${id}`); qc.invalidateQueries({ queryKey: ["inbox"] }); };
  const retract = async (id: string) => {
    if (!confirm("This will remove the notification from all recipients' inboxes. Continue?")) return;
    try { await api.post(`/notifications/${id}/retract`); toast.success("Retracted");
      qc.invalidateQueries({ queryKey: ["inbox"] }); qc.invalidateQueries({ queryKey: ["sent"] });
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const opts: [string, string][] = user?.role === "STATE_ADMIN"
    ? [["ALL_DA", "All District Admins"], ["ALL_FP", "All FIG Presidents"], ["ALL_DA_AND_FP", "All DAs + FPs"],
       ["SELECTED_DA", "Selected District Admins"], ["SELECTED_FP", "Selected FIG Presidents"]]
    : [["ALL_FP", "All FIG Presidents in my district"], ["SELECTED_FP", "Selected FIG Presidents"]];

  const togglePick = (id: string) => {
    setForm((f) => ({ ...f, recipient_ids: f.recipient_ids.includes(id)
      ? f.recipient_ids.filter((x) => x !== id) : [...f.recipient_ids, id] }));
  };

  const fileViewerUrl = (path: string) => {
    const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
    return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><h1 className="font-heading text-3xl font-extrabold">Notifications</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Broadcasts & announcements</p></div>
        {user?.role !== "FIG_PRESIDENT" && <button onClick={() => setOpen(true)} className="btn-primary inline-flex items-center gap-2" data-testid="broadcast-btn"><PaperPlaneTilt size={16} weight="bold" />Broadcast</button>}
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab("inbox")} className={`px-4 py-2 rounded font-semibold ${tab === "inbox" ? "bg-[#2D5134] text-white" : "bg-white border border-[#E6E4DF]"}`} data-testid="tab-inbox">Inbox ({inbox.length})</button>
        {user?.role !== "FIG_PRESIDENT" && <button onClick={() => setTab("sent")} className={`px-4 py-2 rounded font-semibold ${tab === "sent" ? "bg-[#2D5134] text-white" : "bg-white border border-[#E6E4DF]"}`}>Sent ({sent.length})</button>}
      </div>

      <div className="space-y-3">
        {(tab === "inbox" ? inbox : sent).map((n: any) => (
          <div key={n.id} className={`card p-4 ${tab === "inbox" && !n.is_read ? "border-l-4" : ""}`} style={tab === "inbox" && !n.is_read ? { borderLeftColor: "var(--secondary)" } : {}}>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <Bell size={20} weight="duotone" color="#2D5134" />
                <div>
                  <div className="font-heading font-bold">{n.title} {tab === "inbox" && !n.is_read && <span className="badge badge-warning ml-2">New</span>}</div>
                  <div className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{n.details}</div>
                  {n.attachment_path && (
                    <a href={fileViewerUrl(n.attachment_path)} target="_blank" rel="noopener noreferrer"
                       className="text-xs mt-2 inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
                      <Paperclip size={12} weight="bold" /> Open attachment
                    </a>
                  )}
                  <div className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>{new Date(n.sent_at).toLocaleString()} · {n.sent_by_role}</div>
                </div>
              </div>
              {tab === "inbox" && !n.is_read && n.recipient_id && <button className="text-xs text-[#2D5134] font-semibold" onClick={() => markRead(n.recipient_id!)}>Mark read</button>}
              {tab === "sent" && <button className="text-xs font-semibold" style={{ color: "var(--error)" }} onClick={() => retract(n.id)} data-testid={`retract-${n.id}`}>Retract</button>}
            </div>
          </div>
        ))}
        {(tab === "inbox" ? inbox : sent).length === 0 && <div className="card p-8 text-center" style={{ color: "var(--text-muted)" }}>No notifications</div>}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}><h3 className="font-heading text-xl font-bold">New broadcast</h3><button onClick={() => setOpen(false)}><X size={20} /></button></div>
            <form onSubmit={send} className="p-5 space-y-3">
              <div><label className="label-tag">Title</label><input required className="input mt-1" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
              <div><label className="label-tag">Details</label><textarea required className="input mt-1" rows={4} value={form.details} onChange={(e) => setForm({ ...form, details: e.target.value })} /></div>
              <div><label className="label-tag">Attachment (optional)</label>
                <div className="mt-1"><FileUpload label="Attach file" testId="notif-attach" value={form.attachment_path}
                                              onChange={(p) => setForm({ ...form, attachment_path: p })} /></div></div>
              <div><label className="label-tag">Recipients</label>
                <select className="input mt-1" value={form.recipient_type}
                        onChange={(e) => setForm({ ...form, recipient_type: e.target.value, recipient_ids: [] })}>
                  {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select></div>
              {(needsDAList || needsFPList) && (
                <div className="border rounded p-3 max-h-48 overflow-y-auto" style={{ borderColor: "var(--border)" }}>
                  <div className="label-tag mb-2">Pick recipients ({form.recipient_ids.length} selected)</div>
                  {(needsDAList ? das : fps).map((u) => (
                    <label key={u.id} className="flex items-center gap-2 py-1 text-sm">
                      <input type="checkbox" checked={form.recipient_ids.includes(u.id)} onChange={() => togglePick(u.id)}
                             data-testid={`pick-${u.id}`} />
                      <span>{u.name || u.mobile_no}</span>
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>· {distName(u.district_id)}</span>
                    </label>
                  ))}
                  {(needsDAList ? das : fps).length === 0 && <div className="text-xs" style={{ color: "var(--text-muted)" }}>No users available</div>}
                </div>
              )}
              <div className="flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button className="btn-primary" data-testid="notif-send">Send</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
