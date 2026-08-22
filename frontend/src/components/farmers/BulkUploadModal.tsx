"use client";
import { useState } from "react";
import { X, UploadSimple, DownloadSimple, WarningCircle, CheckCircle } from "@phosphor-icons/react";
import { toast } from "sonner";
import api from "@/lib/api";
import { downloadBlob } from "@/lib/export";
import type { BulkRowError, BulkValidateResult } from "@/lib/types";

/**
 * Bulk upload is deliberately two steps: the file is validated server-side and previewed
 * before anything is written. The same file is posted again on confirm rather than the
 * server holding parsed rows — there is no server-side session state in this app, and
 * re-checking at commit time also catches a mobile someone else registered meanwhile.
 */
export function BulkUploadModal({ onClose, onImported }: {
  onClose: () => void; onImported: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<BulkValidateResult | null>(null);
  const [busy, setBusy] = useState<null | "validate" | "import" | "errors">(null);

  const fmtErr = (e: unknown) =>
    (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Something went wrong";

  function pick(f: File | null) {
    setFile(f);
    setResult(null);
  }

  async function post(path: string, responseType?: "blob") {
    const fd = new FormData();
    fd.append("file", file as File);
    return api.post(path, fd, responseType ? { responseType } : undefined);
  }

  async function validate() {
    if (!file) return;
    setBusy("validate");
    try {
      const { data } = await post("/farmers/bulk-validate");
      setResult(data);
    } catch (e) { toast.error(fmtErr(e)); } finally { setBusy(null); }
  }

  async function downloadErrors() {
    if (!file) return;
    setBusy("errors");
    try {
      const { data } = await post("/farmers/bulk-errors", "blob");
      downloadBlob(data, "bulk-upload-errors.xlsx");
    } catch (e) { toast.error(fmtErr(e)); } finally { setBusy(null); }
  }

  async function confirmImport() {
    if (!file || !result) return;
    setBusy("import");
    try {
      const { data } = await post("/farmers/bulk-import");
      toast.success(`${data.imported} farmer${data.imported === 1 ? "" : "s"} registered`);
      onImported();
      onClose();
    } catch (e) { toast.error(fmtErr(e)); } finally { setBusy(null); }
  }

  const blocked = !!result && (result.error_count > 0 || result.sheet_errors.length > 0);
  const canImport = !!result && !blocked && result.ready_count > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">Bulk upload farmers</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="p-5">
          <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
            Fill in the downloaded template, then upload it here. Nothing is saved until you
            confirm — you will see exactly what will be created first.
          </p>

          <label className="label-tag">Filled-in template (.xlsx)</label>
          <input type="file" accept=".xlsx,.xlsm,.xls" data-testid="bulk-file"
                 className="input mt-1"
                 onChange={(e) => pick(e.target.files?.[0] || null)} />

          <div className="flex justify-end gap-2 mt-3">
            <button className="btn-primary inline-flex items-center gap-2" disabled={!file || busy !== null}
                    data-testid="bulk-validate" onClick={validate}>
              <UploadSimple size={16} weight="bold" />
              {busy === "validate" ? "Checking…" : "Check file"}
            </button>
          </div>

          {result && (
            <div className="mt-5 border-t pt-4" style={{ borderColor: "var(--border)" }}>
              {result.sheet_errors.length > 0 && (
                <div className="p-3 rounded mb-3 text-sm" style={{ background: "#F5DDDB" }}>
                  {result.sheet_errors.map((m, i) => <div key={i}>{m}</div>)}
                </div>
              )}

              <div className="flex items-center gap-5 mb-3 text-sm">
                <span className="inline-flex items-center gap-2" style={{ color: "var(--success)" }}>
                  <CheckCircle size={18} weight="bold" />
                  <strong data-testid="bulk-ready">{result.ready_count}</strong> ready to import
                </span>
                {result.error_count > 0 && (
                  <span className="inline-flex items-center gap-2" style={{ color: "var(--error)" }}>
                    <WarningCircle size={18} weight="bold" />
                    <strong data-testid="bulk-errors-count">{result.error_count}</strong> need fixing
                  </span>
                )}
              </div>

              {result.errors.length > 0 && <ErrorTable errors={result.errors} />}

              {blocked && (
                <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
                  Fix these rows in the spreadsheet and check the file again. Nothing is imported
                  while any row has a problem.
                </p>
              )}

              {canImport && (
                <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
                  {result.ready_count} farmer login{result.ready_count === 1 ? "" : "s"} will also be
                  created, on the standard default password. Delete the spreadsheet from your
                  computer once the import has finished — it contains Aadhaar numbers.
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 p-5 border-t" style={{ borderColor: "var(--border)" }}>
          {result && result.error_count > 0 && (
            <button className="btn-secondary inline-flex items-center gap-2" disabled={busy !== null}
                    onClick={downloadErrors}>
              <DownloadSimple size={16} weight="bold" />
              {busy === "errors" ? "Preparing…" : "Download error report"}
            </button>
          )}
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" disabled={!canImport || busy !== null}
                  data-testid="bulk-confirm" onClick={confirmImport}>
            {busy === "import" ? "Importing…" : `Import ${result?.ready_count ?? 0} farmers`}
          </button>
        </div>
      </div>
    </div>
  );
}

function ErrorTable({ errors }: { errors: BulkRowError[] }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto max-h-72 overflow-y-auto">
        <table className="seri-table">
          <thead><tr><th>Row</th><th>Farmer</th><th>What to fix</th></tr></thead>
          <tbody>
            {errors.map((e) => (
              <tr key={e.row}>
                <td className="font-mono text-xs">{e.row}</td>
                <td>{e.name}</td>
                <td className="text-xs">
                  <ul className="list-disc pl-4">
                    {e.errors.map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
