"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { X, Paperclip, PaperPlaneTilt } from "@phosphor-icons/react";
import { toast } from "sonner";
import FileUpload from "@/components/FileUpload";
import type { ThreadDetail, ThreadMessage, NotificationRecipientRow } from "@/lib/types";

const ROLE_LABEL: Record<string, string> = {
  STATE_ADMIN: "State Admin", DISTRICT_ADMIN: "District Admin", FIG_PRESIDENT: "FIG President",
};

const fileViewerUrl = (path: string) => {
  const t = typeof window !== "undefined" ? localStorage.getItem("seri_token") : "";
  return `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/files/${path}?auth=${t}`;
};

const formatRecipients = (names: string[]) => {
  if (names.length === 0) return "—";
  if (names.length <= 3) return names.join(", ");
  return `${names.slice(0, 3).join(", ")} +${names.length - 3} more`;
};

export function ThreadModal({ threadId, onClose, onChanged }: {
  threadId: string; onClose: () => void; onChanged: () => void;
}) {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [replyText, setReplyText] = useState("");
  const [replyAttachment, setReplyAttachment] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const { data: detail, isLoading, isError } = useQuery<ThreadDetail>({
    queryKey: ["thread-detail", threadId],
    queryFn: async () => (await api.get(`/notifications/threads/${threadId}`)).data,
  });

  useEffect(() => {
    if (!detail) return;
    api.post(`/notifications/threads/${threadId}/read`).then(onChanged).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId, !!detail]);

  const messages = detail?.messages ?? [];
  const root = messages[0];
  const receiptsTarget = detail?.ancestor ?? root;
  const isOwnReceiptsTarget = !!receiptsTarget && receiptsTarget.sent_by_user_id === user?.id;

  const { data: recipients = [] } = useQuery<NotificationRecipientRow[]>({
    queryKey: ["notification-recipients", receiptsTarget?.id],
    queryFn: async () => (await api.get(`/notifications/${receiptsTarget!.id}/recipients`)).data,
    enabled: isOwnReceiptsTarget,
  });

  const sendReply = async () => {
    if (!replyText.trim()) return toast.error("Enter a reply message");
    setSending(true);
    try {
      const res = await api.post(`/notifications/threads/${threadId}/reply`, { details: replyText, attachment_path: replyAttachment });
      toast.success(`Reply sent — Message ID ${res.data.notification_code} · #${res.data.reply_seq}`);
      setReplyText(""); setReplyAttachment(null);
      qc.invalidateQueries({ queryKey: ["thread-detail", threadId] });
      onChanged();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
    finally { setSending(false); }
  };

  const bubble = (m: ThreadMessage, muted: boolean) => {
    const own = m.sent_by_user_id === user?.id;
    return (
      <div key={m.id} className={`flex ${own ? "justify-end" : "justify-start"}`}>
        <div className="max-w-[85%] rounded-lg p-3"
             style={{ background: muted ? "var(--bg)" : own ? "var(--primary)" : "#fff",
                      color: muted ? "var(--text-muted)" : own ? "#fff" : "var(--text)",
                      border: muted || !own ? "1px solid var(--border)" : "none" }}>
          <div className="flex items-center gap-2 flex-wrap text-xs opacity-90 mb-0.5">
            <span className="font-semibold">From: {m.sent_by_name || "—"}</span>
            <span>({ROLE_LABEL[m.sent_by_role] || m.sent_by_role})</span>
            <span className="font-mono">#{m.reply_seq}</span>
            <span>{new Date(m.sent_at).toLocaleString()}</span>
          </div>
          <div className="text-xs opacity-90 mb-1">To: {formatRecipients(m.recipient_names)}</div>
          <div className="text-sm whitespace-pre-wrap">{m.details}</div>
          {m.attachment_path && (
            <a href={fileViewerUrl(m.attachment_path)} target="_blank" rel="noopener noreferrer"
               className="text-xs mt-2 inline-flex items-center gap-1" style={{ color: muted || !own ? "var(--primary)" : "#fff" }}>
              <Paperclip size={12} weight="bold" /> Open attachment
            </a>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-lg max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b flex-shrink-0" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-heading text-lg font-bold">{root?.title || "Notification"}</h3>
            {root && (
              <span className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg)", color: "var(--text-muted)" }}
                    data-testid="notif-message-id">{root.notification_code} · #{messages[messages.length - 1]?.reply_seq}</span>
            )}
          </div>
          <button onClick={onClose} data-testid="notif-detail-close"><X size={20} /></button>
        </div>

        <div className="p-5 space-y-3 overflow-y-auto flex-1">
          {isLoading && <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>}
          {isError && <div className="text-sm" style={{ color: "var(--error)" }}>Could not load this conversation.</div>}

          {detail?.ancestor && bubble(detail.ancestor, true)}
          {messages.map((m) => bubble(m, false))}

          {isOwnReceiptsTarget && recipients.length > 0 && (
            <div className="pt-2">
              <div className="label-tag mb-2">Read receipts</div>
              <div className="border rounded overflow-hidden" style={{ borderColor: "var(--border)" }}>
                <div className="overflow-x-auto">
                  <table className="seri-table">
                    <thead><tr><th>Recipient</th><th>Read</th><th>Read at</th></tr></thead>
                    <tbody>
                      {recipients.map((r) => (
                        <tr key={r.id}>
                          <td>{r.user_name || r.user_mobile || "—"}</td>
                          <td>{r.is_read ? <span className="badge badge-success">Yes</span> : <span className="badge badge-muted">No</span>}</td>
                          <td>{r.read_at ? new Date(r.read_at).toLocaleString() : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {detail && (
          <div className="p-5 pt-3 border-t flex-shrink-0" style={{ borderColor: "var(--border)" }}>
            <textarea className="input" rows={3} placeholder="Write a reply…" value={replyText}
                      onChange={(e) => setReplyText(e.target.value)} data-testid="notif-reply-text" />
            <div className="mt-2 flex items-center justify-between gap-2">
              <FileUpload label="Attach file" testId="notif-reply-attach" value={replyAttachment} onChange={setReplyAttachment} />
              <button type="button" className="btn-primary inline-flex items-center gap-2" onClick={sendReply}
                      disabled={sending} data-testid="notif-reply-send">
                <PaperPlaneTilt size={14} weight="bold" /> Send reply
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
