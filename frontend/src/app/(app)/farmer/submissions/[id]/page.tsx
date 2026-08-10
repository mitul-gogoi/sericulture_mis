"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { FarmerSubmissionDetail } from "@/lib/types";
import { FarmerSubmissionDetailView } from "@/components/farmers/FarmerSubmissionDetailView";

export default function FarmerSubmissionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: detail, isLoading, isError } = useQuery<FarmerSubmissionDetail>({
    queryKey: ["farmer-own-submission-detail", id],
    queryFn: async () => (await api.get(`/farmers/me/submissions/${id}`)).data,
    enabled: !!id,
  });

  if (isLoading) return <div>Loading…</div>;
  if (isError || !detail) return <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>Submission not found.</div>;

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">{detail.submission.submission_code}</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{detail.submission.submission_month}</p>
      </div>
      <FarmerSubmissionDetailView
        detail={detail}
        actions={
          <button className="btn-secondary" onClick={() => router.push(`/farmer/submit?correctSubmissionId=${id}`)}>
            Request resubmission
          </button>
        }
      />
    </div>
  );
}
