"use client";
import { useState } from "react";
import { DownloadSimple } from "@phosphor-icons/react";
import { toast } from "sonner";
import { downloadReport } from "@/lib/export";

export function ExportButtons({ report, params = {} }: { report: string; params?: Record<string, string> }) {
  const [loading, setLoading] = useState<"xlsx" | "pdf" | null>(null);

  async function handle(format: "xlsx" | "pdf") {
    setLoading(format);
    try {
      await downloadReport(report, format, params);
    } catch {
      toast.error("Export failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button onClick={() => handle("xlsx")} disabled={loading !== null} className="btn-secondary text-sm inline-flex items-center gap-1">
        <DownloadSimple size={14} weight="bold" /> Excel
      </button>
      <button onClick={() => handle("pdf")} disabled={loading !== null} className="btn-secondary text-sm inline-flex items-center gap-1">
        <DownloadSimple size={14} weight="bold" /> PDF
      </button>
    </div>
  );
}
