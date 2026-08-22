"use client";
import { ViewField } from "@/components/ViewField";
import { figActivityLabel } from "./figActivities";
import { sdoCdcName } from "@/lib/sdoCdc";
import { fileViewerUrl } from "@/lib/fileUrl";
import { Paperclip } from "@phosphor-icons/react";
import type { FigDetail, District, SericultureCircle, SubdivisionCdc, SilkTypeActivityProduct } from "@/lib/types";

export function FigDetailView({ detail, staps, districts, allCircles, subdivisionCdcs }: {
  detail: FigDetail; staps: SilkTypeActivityProduct[]; districts: District[]; allCircles: SericultureCircle[]; subdivisionCdcs: SubdivisionCdc[];
}) {
  const docLink = (path?: string | null) => path ? (
    <a href={fileViewerUrl(path)} target="_blank" rel="noopener noreferrer"
       className="inline-flex items-center gap-1" style={{ color: "var(--primary)" }}>
      <Paperclip size={14} weight="bold" /> Open
    </a>
  ) : <span className="badge badge-warning">Not uploaded</span>;
  const president = detail.members?.find((m) => m.role === "President");
  return (
    <div className="mb-5 border-b pb-5" style={{ borderColor: "var(--border)" }}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="col-span-full"><ViewField label="FIG Name" value={detail.fig_name} /></div>
        <ViewField label="FIG Formation Date" value={detail.formation_date?.slice(0, 10)} />
        <ViewField label="Primary silk type / activity" value={figActivityLabel(detail.silk_type_id, detail.activity_ids, staps)} />
        <ViewField label="District" value={districts.find((d) => d.id === detail.district_id)?.district_name} />
        <ViewField label="Sericulture Circle" value={allCircles.find((c) => c.id === detail.seri_circle_id)?.circle_name} />
        <ViewField label="Sub-division Office (SDO)/ CDC Office" value={sdoCdcName(detail.seri_circle_id, allCircles, subdivisionCdcs)} />
        <div className="col-span-full"><ViewField label="Address line" value={detail.address} /></div>
        <div className="col-span-full"><ViewField label="Village/ Town/ City" value={detail.village_name} /></div>
        <ViewField label="Panchayat" value={detail.panchayat_name} />
        <ViewField label="Post Office" value={detail.post_office} />
        <ViewField label="PIN Code" value={detail.pin_code} />
        <ViewField label="Meeting Venue" value={detail.meeting_venue} />
        <ViewField label="Total Members" value={detail.total_members} />
        <ViewField label="FIG President" value={president?.farmer ? `${president.farmer.first_name} ${president.farmer.last_name} (${president.farmer.farmer_code})` : null} />
        <ViewField label="President Mobile Number" value={president?.farmer?.mobile_no} />
        <ViewField label="Status" value={detail.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>} />
        <ViewField label="Founding minutes" value={docLink(detail.minutes_path)} />
        <ViewField label="FIG group photo" value={docLink(detail.group_photo_path)} />
      </div>
    </div>
  );
}
