"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Bell, PaperPlaneTilt, X } from "@phosphor-icons/react";
import { toast } from "sonner";
import FileUpload from "@/components/FileUpload";
import { RecipientPicker } from "@/components/notifications/RecipientPicker";
import { ThreadModal } from "@/components/notifications/ThreadModal";
import type { PaginatedThreads, NotificationCandidate } from "@/lib/types";

const PAGE_SIZES = [10, 20, 50, 100];

export default function NotificationsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"inbox" | "sent">("inbox");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [open, setOpen] = useState(false);
  const [openThreadId, setOpenThreadId] = useState<string | null>(null);
  const [form, setForm] = useState<{ title: string; details: string; recipient_type: string; attachment_path: string | null; recipient_ids: string[] }>(
    { title: "", details: "", recipient_type: "ALL_FP", attachment_path: null, recipient_ids: [] },
  );

  const canSeeSent = user?.role !== "FIG_PRESIDENT";
  const effectiveTab = canSeeSent ? tab : "inbox";

  const { data } = useQuery<PaginatedThreads>({
    queryKey: ["notif-threads", effectiveTab, page, pageSize],
    queryFn: async () => (await api.get("/notifications/threads", { params: { box: effectiveTab, page, page_size: pageSize } })).data,
  });
  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const showingFrom = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const showingTo = Math.min(page * pageSize, total);

  const invalidateThreads = () => qc.invalidateQueries({ queryKey: ["notif-threads"] });

  // Candidate list for "Selected" recipient pickers — one server-joined, role-scoped call
  const needsDAList = form.recipient_type === "SELECTED_DA";
  const needsFPList = form.recipient_type === "SELECTED_FP";
  const needsSAList = form.recipient_type === "SELECTED_SA";
  const { data: candidates = [] } = useQuery<NotificationCandidate[]>({
    queryKey: ["notif-candidates", form.recipient_type],
    queryFn: async () => (await api.get("/notifications/candidates", { params: { recipient_type: form.recipient_type } })).data,
    enabled: needsDAList || needsFPList || needsSAList,
  });

  const send = async (e: React.FormEvent) => { e.preventDefault();
    if ((needsDAList || needsFPList || needsSAList) && form.recipient_ids.length === 0) {
      return toast.error("Pick at least one recipient");
    }
    try {
      const res = await api.post("/notifications", form);
      toast.success(`Sent — Message ID ${res.data.notification_code}`); setOpen(false);
      setForm({ title: "", details: "", recipient_type: "ALL_FP", attachment_path: null, recipient_ids: [] });
      invalidateThreads();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };
  const retract = async (id: string) => {
    if (!confirm("This will remove the notification from all recipients' inboxes. Continue?")) return;
    try { await api.post(`/notifications/${id}/retract`); toast.success("Retracted"); invalidateThreads();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const opts: [string, string][] = user?.role === "STATE_ADMIN"
    ? [["ALL_DA", "All District Admins"], ["ALL_FP", "All FIG Presidents"], ["ALL_DA_AND_FP", "All DAs + FPs"],
       ["SELECTED_DA", "Selected District Admins"], ["SELECTED_FP", "Selected FIG Presidents"]]
    : [["ALL_FP", "All FIG Presidents in my district"], ["SELECTED_FP", "Selected FIG Presidents"],
       ["ALL_SA", "All State Admins"], ["SELECTED_SA", "Selected State Admins"]];

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div><h1 className="font-heading text-3xl font-extrabold">Notifications</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Broadcasts & announcements</p></div>
        {canSeeSent && <button onClick={() => setOpen(true)} className="btn-primary inline-flex items-center gap-2" data-testid="broadcast-btn"><PaperPlaneTilt size={16} weight="bold" />Send Message</button>}
      </div>

      <div className="flex gap-2 mb-4">
        <button onClick={() => { setTab("inbox"); setPage(1); }} className={`px-4 py-2 rounded font-semibold ${effectiveTab === "inbox" ? "bg-[#2D5134] text-white" : "bg-white border border-[#E6E4DF]"}`} data-testid="tab-inbox">Inbox</button>
        {canSeeSent && <button onClick={() => { setTab("sent"); setPage(1); }} className={`px-4 py-2 rounded font-semibold ${effectiveTab === "sent" ? "bg-[#2D5134] text-white" : "bg-white border border-[#E6E4DF]"}`}>Sent</button>}
      </div>

      <div className="space-y-3">
        {items.map((n) => (
          <div key={n.thread_id} className={`card p-4 cursor-pointer hover:shadow-sm transition ${effectiveTab === "inbox" && !n.is_read ? "border-l-4" : ""}`}
               style={effectiveTab === "inbox" && !n.is_read ? { borderLeftColor: "var(--secondary)" } : {}}
               onClick={() => setOpenThreadId(n.thread_id)} data-testid={`notif-card-${n.thread_id}`}>
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <Bell size={20} weight="duotone" color="#2D5134" />
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-heading font-bold">{n.title}</span>
                    <span className="text-xs font-mono px-1 rounded" style={{ background: "var(--bg)", color: "var(--text-muted)" }}>{n.notification_code}</span>
                    <span className="text-xs font-mono px-1 rounded" style={{ background: "var(--bg)", color: "var(--text-muted)" }}>#{n.latest_reply_seq}</span>
                    {effectiveTab === "inbox" && !n.is_read && <span className="badge badge-warning">New</span>}
                  </div>
                  {n.other_party_name && (
                    <div className="text-xs mt-1 font-semibold" style={{ color: "var(--primary)" }}>with {n.other_party_name}</div>
                  )}
                  <div className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{n.latest_details_snippet}</div>
                  <div className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>{new Date(n.latest_sent_at).toLocaleString()} · {n.latest_sent_by_role}</div>
                </div>
              </div>
              {effectiveTab === "sent" && (
                <button className="text-xs font-semibold" style={{ color: "var(--error)" }}
                        onClick={(e) => { e.stopPropagation(); retract(n.thread_id); }} data-testid={`retract-${n.thread_id}`}>Retract</button>
              )}
            </div>
          </div>
        ))}
        {items.length === 0 && <div className="card p-8 text-center" style={{ color: "var(--text-muted)" }}>No notifications</div>}
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            Showing {showingFrom}–{showingTo} of {total}
          </div>
          <div className="flex items-center gap-3">
            <select className="input" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
            </select>
            <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
            <button className="btn-secondary" disabled={page * pageSize >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
          </div>
        </div>
      )}

      {openThreadId && (
        <ThreadModal
          threadId={openThreadId}
          onClose={() => setOpenThreadId(null)}
          onChanged={invalidateThreads}
        />
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
          <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}><h3 className="font-heading text-xl font-bold">New Message</h3><button onClick={() => setOpen(false)}><X size={20} /></button></div>
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
              {(needsDAList || needsFPList || needsSAList) && (
                <div>
                  <label className="label-tag">Pick recipients</label>
                  <div className="mt-1">
                    <RecipientPicker candidates={candidates} selected={form.recipient_ids}
                                     onChange={(ids) => setForm({ ...form, recipient_ids: ids })}
                                     groupByDistrict={needsFPList} />
                  </div>
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
