"use client";
import FileUpload from "@/components/FileUpload";
import { fileViewerUrl } from "@/lib/fileUrl";
import { Paperclip } from "@phosphor-icons/react";

export interface FigDocuments {
  minutes_path: string | null;
  group_photo_path: string | null;
}

/**
 * Step 2 of FIG registration, reused by FIG Edit.
 *
 * These uploads deliberately happen AFTER the FIG exists: the storage folder is named
 * after the FIG's real code, which is only known once it has been created. Uploading
 * during step 1 would file every document under "Unknown/Unknown/Unknown FIG".
 */
export function FigDocumentsStep({
  figName, figCode, districtId, seriCircleId, value, onChange,
}: {
  figName: string;
  figCode: string;
  districtId: string;
  seriCircleId: string;
  value: FigDocuments;
  onChange: (next: FigDocuments) => void;
}) {
  // What the upload endpoint names the folder after — see _build_folder's fig_registration branch.
  const identifier = figCode ? `${figName} (${figCode})` : figName;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
      <div className="col-span-full">
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Attach the founding paperwork for this FIG. You can also add or replace these later
          from the FIG&apos;s Edit screen.
        </p>
      </div>

      <div>
        <label className="label-tag block mb-2">Founding minutes of the first FIG meeting</label>
        <FileUpload
          label="Upload minutes" testId="fig-minutes-upload"
          value={value.minutes_path}
          onChange={(p) => onChange({ ...value, minutes_path: p })}
          category="fig_registration" districtId={districtId} seriCircleId={seriCircleId}
          farmerIdentifier={identifier}
        />
        {value.minutes_path && (
          <a href={fileViewerUrl(value.minutes_path)} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1 text-xs mt-2" style={{ color: "var(--primary)" }}>
            <Paperclip size={12} weight="bold" /> Open
          </a>
        )}
      </div>

      <div>
        <label className="label-tag block mb-2">Group photo of the FIG</label>
        <FileUpload
          label="Upload group photo" testId="fig-photo-upload"
          value={value.group_photo_path}
          onChange={(p) => onChange({ ...value, group_photo_path: p })}
          accept=".jpg,.jpeg,.png,.webp"
          category="fig_registration" districtId={districtId} seriCircleId={seriCircleId}
          farmerIdentifier={identifier}
        />
        {value.group_photo_path && (
          <a href={fileViewerUrl(value.group_photo_path)} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1 text-xs mt-2" style={{ color: "var(--primary)" }}>
            <Paperclip size={12} weight="bold" /> Open
          </a>
        )}
      </div>
    </div>
  );
}

/** A FIG is only complete once both documents are attached. */
export function figDocumentsPending(fig: { minutes_path?: string | null; group_photo_path?: string | null }): boolean {
  return !fig.minutes_path || !fig.group_photo_path;
}
