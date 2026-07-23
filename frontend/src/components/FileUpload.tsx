"use client";
import { useRef, useState } from "react";
import api, { fmtErr } from "@/lib/api";
import { Paperclip, X, FileArrowUp } from "@phosphor-icons/react";
import { toast } from "sonner";

interface Props {
  label?: string;
  value?: string | null;
  onChange: (path: string | null) => void;
  accept?: string;
  testId?: string;
  category?: "farmer_photo" | "farmer_passbook" | "fig_minutes" | "assets" | "other";
  districtId?: string;
  seriCircleId?: string;
  farmerIdentifier?: string;
  month?: string;
}

export default function FileUpload({
  label = "Upload file", value, onChange, accept = ".jpg,.jpeg,.png,.webp,.pdf", testId,
  category, districtId, seriCircleId, farmerIdentifier, month,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      if (category) fd.append("category", category);
      if (districtId) fd.append("district_id", districtId);
      if (seriCircleId) fd.append("seri_circle_id", seriCircleId);
      if (farmerIdentifier) fd.append("farmer_identifier", farmerIdentifier);
      if (month) fd.append("month", month);
      const { data } = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      onChange(data.path);
      toast.success("Uploaded");
    } catch (e: any) {
      toast.error(fmtErr(e.response?.data?.detail) || "Upload failed");
    } finally { setUploading(false); }
  };

  if (value) {
    const name = value.split("/").pop();
    return (
      <div className="flex items-center gap-2 text-sm">
        <Paperclip size={14} weight="bold" color="#2D5134" />
        <span className="font-mono text-xs truncate max-w-[200px]" title={name}>{name}</span>
        <button type="button" className="text-xs" style={{ color: "var(--error)" }} onClick={() => onChange(null)} data-testid={testId ? `${testId}-clear` : undefined}>
          <X size={14} weight="bold" />
        </button>
      </div>
    );
  }

  return (
    <>
      <button type="button" className="btn-secondary inline-flex items-center gap-2 text-sm py-1.5"
              onClick={() => inputRef.current?.click()} disabled={uploading} data-testid={testId}>
        <FileArrowUp size={14} weight="bold" />
        {uploading ? "Uploading…" : label}
      </button>
      <input ref={inputRef} type="file" accept={accept} className="hidden"
             onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
    </>
  );
}
