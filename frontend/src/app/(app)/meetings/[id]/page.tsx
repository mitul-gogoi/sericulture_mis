"use client";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ArrowLeft, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { MeetingDetail, MeetingCorrection } from "@/lib/types";
import { MeetingDetailView } from "@/components/meetings/MeetingDetailView";

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const { user } = useAuth();
  const id = params.id as string;

  const { data, isLoading, error } = useQuery<MeetingDetail>({
    queryKey: ["meeting-detail", id],
    queryFn: async () => (await api.get(`/meetings/${id}`)).data,
    enabled: !!id,
    retry: false,
  });

  const { data: corrections = [] } = useQuery<MeetingCorrection[]>({
    queryKey: ["meeting-corrections", id],
    queryFn: async () => (await api.get(`/meetings/${id}/corrections`)).data,
    enabled: !!id,
  });
  const pendingCorrection = corrections.find((c) => c.status === "PENDING");

  const { data: correctionPreview } = useQuery<MeetingDetail>({
    queryKey: ["correction-preview", pendingCorrection?.id],
    queryFn: async () => (await api.get(`/meetings/corrections/${pendingCorrection!.id}/preview`)).data,
    enabled: !!pendingCorrection,
  });

  const isFP = user?.role === "FIG_PRESIDENT";
  // District Admin can see the pending-correction preview (it's still a live-data concern
  // for their district) but only State Admin can Accept/Reject it — see CLAUDE.md's
  // correction-authority rule.
  const canViewCorrection = user?.role === "DISTRICT_ADMIN" || user?.role === "STATE_ADMIN";
  const canActOnCorrection = user?.role === "STATE_ADMIN";

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["meeting-detail", id] });
    qc.invalidateQueries({ queryKey: ["meeting-corrections", id] });
  };

  const handleAccept = async () => {
    if (!pendingCorrection) return;
    if (!window.confirm("Accept this correction? This will overwrite the live submission with the corrected data.")) return;
    try {
      await api.post(`/meetings/corrections/${pendingCorrection.id}/accept`);
      toast.success("Correction accepted");
      invalidateAll();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const handleReject = async () => {
    if (!pendingCorrection) return;
    const reason = window.prompt("Reason for rejecting this correction?");
    if (!reason) return;
    try {
      await api.post(`/meetings/corrections/${pendingCorrection.id}/reject`, { rejection_reason: reason });
      toast.success("Correction rejected");
      invalidateAll();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const fpActions = isFP && (
    pendingCorrection ? (
      <span className="badge badge-warning">Correction pending review</span>
    ) : (
      <Link href={`/submission?correctMeetingId=${id}`} className="btn-secondary inline-flex items-center gap-2 text-sm">
        Request correction
      </Link>
    )
  );

  return (
    <div>
      <button type="button" onClick={() => router.back()}
              className="inline-flex items-center gap-1 text-sm mb-4" style={{ color: "var(--primary)" }}>
        <ArrowLeft size={16} weight="bold" /> Back
      </button>

      {isLoading && <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>}

      {error && (
        <div className="card p-5">
          <div className="font-semibold mb-1">Can&apos;t open this submission</div>
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            {(error as any)?.response?.status === 403
              ? "You don't have access to this submission."
              : "This submission could not be found."}
          </div>
        </div>
      )}

      {data && (
        <>
          <div className="mb-5 flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="font-heading text-3xl font-extrabold">{data.meeting.meeting_title}</h1>
              <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
                {data.meeting.fig_name} · {data.meeting.meeting_month}
              </p>
            </div>
            {fpActions}
          </div>

          <MeetingDetailView detail={data} />

          {canViewCorrection && pendingCorrection && correctionPreview && (
            <div className="mt-8">
              <div className="card p-4 mb-4 flex items-center gap-2" style={{ background: "#FBEFD6" }}>
                <Warning size={18} weight="fill" style={{ color: "var(--warning)" }} />
                <div className="text-sm font-semibold">
                  {canActOnCorrection
                    ? "A correction is pending your review — the live data above is unchanged until you accept it."
                    : "A correction is pending State Admin review — the live data above is unchanged until it's accepted."}
                </div>
              </div>
              <h2 className="font-heading text-xl font-bold mb-3">Proposed correction</h2>
              <MeetingDetailView
                detail={correctionPreview}
                actions={canActOnCorrection ? (
                  <div className="flex gap-2">
                    <button className="btn-primary" onClick={handleAccept} data-testid="correction-accept">Accept correction</button>
                    <button className="btn-secondary" style={{ color: "var(--error)" }} onClick={handleReject} data-testid="correction-reject">Reject correction</button>
                  </div>
                ) : undefined}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
