"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { fmtErr } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ArrowLeft, Warning } from "@phosphor-icons/react";
import { toast } from "sonner";
import type { FarmerSubmissionDetail, PendingFarmerCorrectionRow } from "@/lib/types";
import { FarmerSubmissionDetailView } from "@/components/farmers/FarmerSubmissionDetailView";

export default function FarmerSubmissionAdminDetailPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const { user } = useAuth();
  const id = params.id as string;
  const isDA = user?.role === "DISTRICT_ADMIN";

  const { data, isLoading, error } = useQuery<FarmerSubmissionDetail>({
    queryKey: ["farmer-submission-admin-detail", id],
    queryFn: async () => (await api.get(`/farmer-submissions/${id}`)).data,
    enabled: !!id, retry: false,
  });

  const { data: pending = [] } = useQuery<PendingFarmerCorrectionRow[]>({
    queryKey: ["pending-farmer-corrections"],
    queryFn: async () => (await api.get("/farmer-submissions/corrections/pending")).data,
    enabled: isDA,
  });
  const pendingCorrection = pending.find((c) => c.farmer_submission_id === id);

  const { data: correctionPreview } = useQuery<FarmerSubmissionDetail>({
    queryKey: ["farmer-correction-preview", pendingCorrection?.correction_id],
    queryFn: async () => (await api.get(`/farmer-submissions/corrections/${pendingCorrection!.correction_id}/preview`)).data,
    enabled: !!pendingCorrection,
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["farmer-submission-admin-detail", id] });
    qc.invalidateQueries({ queryKey: ["pending-farmer-corrections"] });
  };

  const handleAccept = async () => {
    if (!pendingCorrection) return;
    if (!window.confirm("Accept this resubmission? This will overwrite the live submission with the corrected data.")) return;
    try {
      await api.post(`/farmer-submissions/corrections/${pendingCorrection.correction_id}/accept`);
      toast.success("Resubmission accepted");
      invalidateAll();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  const handleReject = async () => {
    if (!pendingCorrection) return;
    const reason = window.prompt("Reason for rejecting this resubmission?");
    if (!reason) return;
    try {
      await api.post(`/farmer-submissions/corrections/${pendingCorrection.correction_id}/reject`, { rejection_reason: reason });
      toast.success("Resubmission rejected");
      invalidateAll();
    } catch (e: any) { toast.error(fmtErr(e.response?.data?.detail)); }
  };

  return (
    <div>
      <button type="button" onClick={() => router.back()} className="inline-flex items-center gap-1 text-sm mb-4" style={{ color: "var(--primary)" }}>
        <ArrowLeft size={16} weight="bold" /> Back
      </button>

      {isLoading && <div className="text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>}
      {error && (
        <div className="card p-5">
          <div className="font-semibold mb-1">Can&apos;t open this submission</div>
          <div className="text-sm" style={{ color: "var(--text-muted)" }}>
            {(error as any)?.response?.status === 403 ? "You don't have access to this submission." : "This submission could not be found."}
          </div>
        </div>
      )}

      {data && (
        <>
          <div className="mb-5">
            <h1 className="font-heading text-3xl font-extrabold">{data.submission.submission_code}</h1>
            <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
              {data.submission.farmer_name} ({data.submission.farmer_code}) · {data.submission.submission_month}
            </p>
          </div>

          <FarmerSubmissionDetailView detail={data} />

          {isDA && pendingCorrection && correctionPreview && (
            <div className="mt-8">
              <div className="card p-4 mb-4 flex items-center gap-2" style={{ background: "#FBEFD6" }}>
                <Warning size={18} weight="fill" style={{ color: "var(--warning)" }} />
                <div className="text-sm font-semibold">A resubmission is pending your review — the live data above is unchanged until you accept it.</div>
              </div>
              <h2 className="font-heading text-xl font-bold mb-3">Proposed resubmission</h2>
              <FarmerSubmissionDetailView
                detail={correctionPreview}
                actions={
                  <div className="flex gap-2">
                    <button className="btn-primary" onClick={handleAccept}>Accept resubmission</button>
                    <button className="btn-secondary" style={{ color: "var(--error)" }} onClick={handleReject}>Reject resubmission</button>
                  </div>
                }
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
