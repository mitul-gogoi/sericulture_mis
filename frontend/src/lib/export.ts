"use client";
import api from "./api";

const MEDIA_TYPES: Record<string, string> = {
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  pdf: "application/pdf",
};

export async function downloadReport(report: string, format: "xlsx" | "pdf", params: Record<string, string> = {}) {
  const { data, headers } = await api.get("/reports/export", {
    params: { report, format, ...params },
    responseType: "blob",
  });
  // Prefer the server's Content-Disposition filename (e.g. timestamped for farmers) —
  // only fall back to the generic name if the header is missing for some reason.
  const disposition: string | undefined = headers["content-disposition"];
  const match = disposition?.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || `${report}.${format}`;
  const blob = new Blob([data], { type: MEDIA_TYPES[format] });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Save an already-fetched blob. Used by the bulk-upload template and error report, which
 *  are not "reports" and so do not belong in the /reports/export dispatcher. */
export function downloadBlob(data: BlobPart, filename: string, format: "xlsx" | "pdf" = "xlsx") {
  const blob = new Blob([data], { type: MEDIA_TYPES[format] });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function downloadFarmerBulkTemplate() {
  const { data } = await api.get("/farmers/bulk-template", { responseType: "blob" });
  downloadBlob(data, "Farmer Registration - Bulk Upload Template.xlsx");
}
