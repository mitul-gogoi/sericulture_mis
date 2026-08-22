"use client";
import { X } from "@phosphor-icons/react";
import { ViewField } from "@/components/ViewField";
import { LandsList } from "@/components/LandsList";
import { AssetsList } from "@/components/AssetsList";
import { lacName } from "@/lib/lac";
import type { Farmer, District, SericultureCircle, Lac, Caste, Religion, EducationLevel, Activity, SilkTypeActivityProduct, Land, AssetInstance } from "@/lib/types";

/** Registration is activity-level, so several STAP ids collapse to one line here — a farmer
 *  doing Eri Rearing holds both its output rows and should read as one activity, not two. */
function stapActivityLabels(stapIds: string[], staps: SilkTypeActivityProduct[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of stapIds) {
    const s = staps.find((x) => x.id === id);
    if (!s || seen.has(s.activity_id)) continue;
    seen.add(s.activity_id);
    out.push(`${s.silk_type_name} · ${s.activity_name}`);
  }
  return out.sort((a, b) => a.localeCompare(b));
}

export function FarmerViewModal({
  viewing, onClose, viewCircles, lacs, viewLands, viewAssets,
  districts, castes, religions, educationLevels, activities, staps,
  canResetPassword, resetPassword, setResetPassword, onResetPassword,
}: {
  viewing: Farmer; onClose: () => void;
  viewCircles: SericultureCircle[]; lacs: Lac[]; viewLands: Land[]; viewAssets: AssetInstance[];
  districts: District[]; castes: Caste[]; religions: Religion[]; educationLevels: EducationLevel[];
  activities: Activity[]; staps: SilkTypeActivityProduct[];
  canResetPassword?: boolean; resetPassword?: string; setResetPassword?: (v: string) => void; onResetPassword?: () => void;
}) {
  const casteName = (id?: string | null) => castes.find((c) => c.id === id)?.caste_name || "—";
  const religionName = (id?: string | null) => religions.find((r) => r.id === id)?.religion_name || "—";
  const educationLevelName = (id?: string | null) => educationLevels.find((e) => e.id === id)?.education_level_name || "—";
  const districtName = (id?: string | null) => districts.find((d) => d.id === id)?.district_name || "—";
  const circleName = (id?: string | null) => viewCircles.find((c) => c.id === id)?.circle_name || "—";
  const activityName = (id: string) => activities.find((a) => a.id === id)?.activity_name || id;
  const fileName = (path?: string | null) => path ? path.split("/").pop() : "—";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-2xl sm:max-w-3xl lg:max-w-4xl xl:max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">Farmer details · {viewing.farmer_code}</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <ViewField label="First name" value={viewing.first_name} />
          <ViewField label="Middle name" value={viewing.middle_name} />
          <ViewField label="Last name" value={viewing.last_name} />
          <ViewField label="Gender" value={viewing.gender} />
          <ViewField label="Date of birth" value={viewing.date_of_birth ? viewing.date_of_birth.slice(0, 10) : null} />
          <ViewField label="Mobile" value={viewing.mobile_no} />
          <ViewField label="Aadhaar" value={viewing.aadhaar_masked} />
          <ViewField label="PAN number" value={viewing.pan_no} />
          <ViewField label="Farmer type" value={viewing.farmer_type} />
          <ViewField label="Education level" value={educationLevelName(viewing.education_level_id)} />
          <ViewField label="Caste" value={casteName(viewing.caste_id)} />
          <ViewField label="Religion" value={religionName(viewing.religion_id)} />
          <ViewField label="Family members (male)" value={viewing.family_member_male} />
          <ViewField label="Family members (female)" value={viewing.family_member_female} />
          <ViewField label="District" value={districtName(viewing.district_id)} />
          <ViewField label="Sericulture Circle" value={circleName(viewing.seri_circle_id)} />
          <ViewField label="LAC" value={lacName(viewing.seri_circle_id, viewCircles, lacs)} />
          <div className="col-span-full"><ViewField label="Village" value={viewing.village_name} /></div>
          <ViewField label="Panchayat" value={viewing.gaon_panchayat} />
          <ViewField label="Development Block" value={viewing.development_block} />
          <ViewField label="Post Office" value={viewing.post_office} />
          <ViewField label="PIN Code" value={viewing.pin_code} />
          <div className="col-span-full">
            <div className="label-tag mb-2">Land Details</div>
            <LandsList lands={viewLands} />
          </div>
          <div className="col-span-full">
            <div className="label-tag mb-2">Assets</div>
            <AssetsList assets={viewAssets} />
          </div>
          <div className="col-span-full">
            <ViewField label="Silk type / activity" value={
              stapActivityLabels(viewing.stap_ids || [], staps).join(", ") || null
            } />
          </div>
          <ViewField label="Experience (years)" value={viewing.experience_years} />
          <div className="col-span-full">
            <ViewField label="Farmer experience in activities" value={
              (viewing.experience_activity_ids && viewing.experience_activity_ids.length > 0)
                ? viewing.experience_activity_ids.map((id) => activityName(id)).join(", ") : null
            } />
          </div>
          <ViewField label="Photo" value={fileName(viewing.photo_path)} />
          <ViewField label="Bank passbook" value={fileName(viewing.passbook_path)} />
          <ViewField label="Account Number" value={viewing.account_number} />
          <ViewField label="Bank Name" value={viewing.bank_name} />
          <ViewField label="Branch Name" value={viewing.branch_name} />
          <ViewField label="IFSC Code" value={viewing.ifsc_code} />
          <ViewField label="Status" value={viewing.is_active ? <span className="badge badge-success">Active</span> : <span className="badge badge-muted">Inactive</span>} />
          {canResetPassword && (
            <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
              <div className="label-tag mb-2">Reset Password</div>
              <p className="text-xs mb-2" style={{ color: "var(--text-muted)" }}>
                Resets this farmer's login password (mobile: {viewing.mobile_no}) if they forgot it.
              </p>
              <div className="flex gap-2">
                <input placeholder="New password" type="password" className="input flex-1"
                       value={resetPassword} onChange={(e) => setResetPassword?.(e.target.value)} />
                <button onClick={onResetPassword} disabled={!resetPassword} className="btn-primary">Reset</button>
              </div>
            </div>
          )}
          <div className="col-span-full flex justify-end gap-2 mt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>Close</button>
          </div>
        </div>
      </div>
    </div>
  );
}
