"use client";
import { X } from "@phosphor-icons/react";
import FileUpload from "@/components/FileUpload";
import { LandRowsEditor, type LandRow } from "@/components/LandRowsEditor";
import { LandsList } from "@/components/LandsList";
import { AssetRowsEditor, type AssetRow } from "@/components/AssetRowsEditor";
import { AssetsList } from "@/components/AssetsList";
import { StapGroupPicker } from "./StapGroupPicker";
import { sdoCdcName } from "@/lib/sdoCdc";
import type { Farmer, SericultureCircle, SubdivisionCdc, Caste, Religion, EducationLevel, Activity, AssetType, SilkTypeActivityProduct, Land, AssetInstance } from "@/lib/types";


export interface FarmerEditForm {
  first_name: string; middle_name: string; last_name: string; gender: string; date_of_birth: string;
  mobile_no: string; aadhaar_no: string; pan_no: string;
  seri_circle_id: string; village_name: string; gaon_panchayat: string; development_block: string;
  post_office: string; pin_code: string;
  stap_ids: string[]; experience_activity_ids: string[];
  farmer_type: string; education_level_id: string; experience_years: number;
  caste_id: string; religion_id: string; family_member_male: number; family_member_female: number;
  photo_path: string | null;
  account_number: string; bank_name: string; branch_name: string; ifsc_code: string; passbook_path: string | null;
}

/** Same section shape as FarmerRegisterModal — the two carry the same field set and would be
 *  confusing to navigate if they diverged. */
function SectionHeading({ children, first }: { children: React.ReactNode; first?: boolean }) {
  return (
    <div className={first ? "col-span-full" : "col-span-full border-t pt-4"} style={first ? undefined : { borderColor: "var(--border)" }}>
      <h4 className="font-heading text-sm font-bold">{children}</h4>
    </div>
  );
}

export function FarmerEditModal({
  editing, editForm, setEditForm, onClose, onSubmit,
  editCircles, subdivisionCdcs, educationLevels, castes, religions, activities, staps, assetTypes,
  editLands, editAssets, editNewLands, setEditNewLands, editNewAssets, setEditNewAssets,
  onDeleteLand, onDeleteAsset, aadhaarDirty, setAadhaarDirty,
}: {
  editing: Farmer; editForm: FarmerEditForm; setEditForm: (f: FarmerEditForm) => void;
  onClose: () => void; onSubmit: (e: React.FormEvent) => void;
  editCircles: SericultureCircle[]; subdivisionCdcs: SubdivisionCdc[]; educationLevels: EducationLevel[]; castes: Caste[]; religions: Religion[];
  activities: Activity[]; staps: SilkTypeActivityProduct[]; assetTypes: AssetType[];
  editLands: Land[]; editAssets: AssetInstance[];
  editNewLands: LandRow[]; setEditNewLands: (rows: LandRow[]) => void;
  editNewAssets: AssetRow[]; setEditNewAssets: (rows: AssetRow[]) => void;
  onDeleteLand: (landId: string) => void; onDeleteAsset: (assetId: string) => void;
  aadhaarDirty: boolean; setAadhaarDirty: (v: boolean) => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-2xl sm:max-w-3xl lg:max-w-4xl xl:max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">Edit farmer · {editing.farmer_code}</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={onSubmit} className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

          {/* ---- 1. Personal details ---- */}
          <SectionHeading first>Personal details</SectionHeading>
          <div><label className="label-tag">First name</label><input required className="input mt-1" value={editForm.first_name} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} /></div>
          <div><label className="label-tag">Middle name</label><input className="input mt-1" value={editForm.middle_name} onChange={(e) => setEditForm({ ...editForm, middle_name: e.target.value })} /></div>
          <div><label className="label-tag">Last name</label><input required className="input mt-1" value={editForm.last_name} onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })} /></div>
          <div><label className="label-tag">Gender</label>
            <select required className="input mt-1" value={editForm.gender} onChange={(e) => setEditForm({ ...editForm, gender: e.target.value })}>
              <option value="">Select</option>
              <option>Male</option><option>Female</option><option>Other</option>
            </select></div>
          <div><label className="label-tag">Date of birth</label><input type="date" className="input mt-1" value={editForm.date_of_birth} onChange={(e) => setEditForm({ ...editForm, date_of_birth: e.target.value })} /></div>
          <div><label className="label-tag">Mobile</label><input required className="input mt-1" value={editForm.mobile_no} onChange={(e) => setEditForm({ ...editForm, mobile_no: e.target.value })} /></div>
          {/* Shows the mask until the field is focused; typing then replaces it with visible
              digits. While untouched, farmers/page.tsx strips aadhaar_no from the PATCH body
              entirely, so an unrelated edit can never overwrite the stored number. */}
          <div><label className="label-tag">Aadhaar</label>
            <input
              className="input mt-1" data-testid="farmer-aadhaar-edit"
              inputMode="numeric" maxLength={14}
              placeholder={aadhaarDirty ? "12-digit Aadhaar" : undefined}
              value={aadhaarDirty ? editForm.aadhaar_no : (editing.aadhaar_masked ?? "")}
              onFocus={() => { if (!aadhaarDirty) { setAadhaarDirty(true); setEditForm({ ...editForm, aadhaar_no: "" }); } }}
              onChange={(e) => setEditForm({ ...editForm, aadhaar_no: e.target.value })}
            />
            {aadhaarDirty ? (
              <button type="button" className="text-xs mt-1 underline" style={{ color: "var(--text-muted)" }}
                onClick={() => { setAadhaarDirty(false); setEditForm({ ...editForm, aadhaar_no: "" }); }}>
                Keep existing Aadhaar
              </button>
            ) : (
              <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Click to enter a new 12-digit number</div>
            )}
          </div>
          <div><label className="label-tag">PAN number</label><input className="input mt-1" value={editForm.pan_no} onChange={(e) => setEditForm({ ...editForm, pan_no: e.target.value })} /></div>

          {/* ---- 2. Location ---- */}
          <SectionHeading>Location</SectionHeading>
          <div><label className="label-tag">Sericulture Circle</label>
            <select required className="input mt-1" value={editForm.seri_circle_id} onChange={(e) => setEditForm({ ...editForm, seri_circle_id: e.target.value })}>
              <option value="">Select</option>
              {editCircles.map((c) => <option key={c.id} value={c.id}>{c.circle_name}</option>)}
            </select></div>
          <div><label className="label-tag">Sub-division Office (SDO)/ CDC Office</label>
            <input disabled className="input mt-1" value={sdoCdcName(editForm.seri_circle_id, editCircles, subdivisionCdcs)} /></div>
          <div className="col-span-full"><label className="label-tag">Village</label><input required className="input mt-1" value={editForm.village_name} onChange={(e) => setEditForm({ ...editForm, village_name: e.target.value })} /></div>
          <div><label className="label-tag">Panchayat</label><input className="input mt-1" value={editForm.gaon_panchayat} onChange={(e) => setEditForm({ ...editForm, gaon_panchayat: e.target.value })} /></div>
          <div><label className="label-tag">Development Block</label><input className="input mt-1" value={editForm.development_block} onChange={(e) => setEditForm({ ...editForm, development_block: e.target.value })} /></div>
          <div><label className="label-tag">Post Office</label><input className="input mt-1" value={editForm.post_office} onChange={(e) => setEditForm({ ...editForm, post_office: e.target.value })} /></div>
          <div><label className="label-tag">PIN Code</label><input className="input mt-1" value={editForm.pin_code} onChange={(e) => setEditForm({ ...editForm, pin_code: e.target.value })} /></div>

          {/* ---- 3. Socio-economic ---- */}
          <SectionHeading>Socio-economic details</SectionHeading>
          <div><label className="label-tag">Farmer type</label>
            <select className="input mt-1" value={editForm.farmer_type} onChange={(e) => setEditForm({ ...editForm, farmer_type: e.target.value })}>
              <option>Small</option><option>Medium</option><option>Large</option>
            </select></div>
          <div><label className="label-tag">Education level</label>
            <select className="input mt-1" value={editForm.education_level_id} onChange={(e) => setEditForm({ ...editForm, education_level_id: e.target.value })}>
              <option value="">Select</option>
              {educationLevels.map((e) => <option key={e.id} value={e.id}>{e.education_level_name}</option>)}
            </select></div>
          <div><label className="label-tag">Caste</label>
            <select className="input mt-1" value={editForm.caste_id} onChange={(e) => setEditForm({ ...editForm, caste_id: e.target.value })}>
              <option value="">Select</option>
              {castes.map((c) => <option key={c.id} value={c.id}>{c.caste_name}</option>)}
            </select></div>
          <div><label className="label-tag">Religion</label>
            <select className="input mt-1" value={editForm.religion_id} onChange={(e) => setEditForm({ ...editForm, religion_id: e.target.value })}>
              <option value="">Select</option>
              {religions.map((r) => <option key={r.id} value={r.id}>{r.religion_name}</option>)}
            </select></div>
          <div><label className="label-tag">Family members (male)</label><input type="number" min={0} className="input mt-1" value={editForm.family_member_male} onChange={(e) => setEditForm({ ...editForm, family_member_male: Number(e.target.value) })} /></div>
          <div><label className="label-tag">Family members (female)</label><input type="number" min={0} className="input mt-1" value={editForm.family_member_female} onChange={(e) => setEditForm({ ...editForm, family_member_female: Number(e.target.value) })} /></div>

          {/* ---- 4. Sericulture activity ---- */}
          <SectionHeading>Sericulture activity</SectionHeading>
          <div className="col-span-full">
            <label className="label-tag">Silk type / activity</label>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              What this farmer produces — required before they can submit monthly yield.
            </p>
            <div className="mt-2">
              <StapGroupPicker staps={staps} selected={editForm.stap_ids}
                onChange={(next) => setEditForm({ ...editForm, stap_ids: next })} />
            </div>
          </div>

          {/* ---- 5. Experience ---- */}
          <SectionHeading>Experience</SectionHeading>
          <div><label className="label-tag">Experience (years)</label><input type="number" min={0} className="input mt-1" value={editForm.experience_years} onChange={(e) => setEditForm({ ...editForm, experience_years: Number(e.target.value) })} /></div>
          <div className="col-span-full">
            <label className="label-tag">Farmer experience in activities</label>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              Activities they have prior experience in — used for scheme eligibility.
            </p>
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-40 overflow-y-auto p-3 border rounded" style={{ borderColor: "var(--border)" }}>
              {activities.map((a) => (
                <label key={a.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={editForm.experience_activity_ids.includes(a.id)} onChange={(e) => {
                    const next = e.target.checked
                      ? [...editForm.experience_activity_ids, a.id]
                      : editForm.experience_activity_ids.filter((x) => x !== a.id);
                    setEditForm({ ...editForm, experience_activity_ids: next });
                  }} />
                  {a.activity_name}
                </label>
              ))}
            </div>
          </div>

          {/* ---- 6. Land ---- */}
          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <h4 className="font-heading text-sm font-bold mb-1">Land details</h4>
            {editLands.length > 0 && (
              <div className="mt-2 mb-3">
                <LandsList lands={editLands} onDelete={onDeleteLand} />
              </div>
            )}
            <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>Add another land parcel — GPS boundary is added later by the FIG President.</p>
            <LandRowsEditor value={editNewLands} onChange={setEditNewLands} />
          </div>

          {/* ---- 7. Assets ---- */}
          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <h4 className="font-heading text-sm font-bold mb-1">Existing Assets (Self-Declared)</h4>
            {editAssets.length > 0 && (
              <div className="mt-2 mb-3">
                <AssetsList assets={editAssets} onDelete={onDeleteAsset} />
              </div>
            )}
            <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>
              Add another existing asset. FIG-level shared assets (CFC, CRC) are recorded against the FIG instead.
            </p>
            <AssetRowsEditor value={editNewAssets} onChange={setEditNewAssets} assetTypes={assetTypes} ownerKind="FARMER" />
          </div>

          {/* ---- 8. Bank & documents ---- */}
          <SectionHeading>Bank &amp; documents</SectionHeading>
          <div className="col-span-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="label-tag block mb-2">Photo</label>
              <FileUpload label="Upload photo" testId="farmer-edit-photo-upload" value={editForm.photo_path}
                          onChange={(p) => setEditForm({ ...editForm, photo_path: p })} accept=".jpg,.jpeg,.png,.webp"
                          category="farmer_photo" districtId={editing.district_id} seriCircleId={editForm.seri_circle_id}
                          farmerIdentifier={editForm.mobile_no || editing.farmer_code} />
            </div>
            <div>
              <label className="label-tag block mb-2">Bank passbook</label>
              <FileUpload label="Upload passbook" testId="farmer-edit-passbook-upload" value={editForm.passbook_path}
                          onChange={(p) => setEditForm({ ...editForm, passbook_path: p })}
                          category="farmer_passbook" districtId={editing.district_id} seriCircleId={editForm.seri_circle_id}
                          farmerIdentifier={editForm.mobile_no || editing.farmer_code} />
            </div>
            <div><label className="label-tag">Account Number</label><input className="input mt-1" value={editForm.account_number}
                  onChange={(e) => setEditForm({ ...editForm, account_number: e.target.value })} /></div>
            <div><label className="label-tag">Bank Name</label><input className="input mt-1" value={editForm.bank_name}
                  onChange={(e) => setEditForm({ ...editForm, bank_name: e.target.value })} /></div>
            <div><label className="label-tag">Branch Name</label><input className="input mt-1" value={editForm.branch_name}
                  onChange={(e) => setEditForm({ ...editForm, branch_name: e.target.value })} /></div>
            <div><label className="label-tag">IFSC Code</label><input className="input mt-1" value={editForm.ifsc_code}
                  onChange={(e) => setEditForm({ ...editForm, ifsc_code: e.target.value })} /></div>
          </div>

          <div className="col-span-full flex justify-end gap-2 mt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" data-testid="submit-farmer-edit" className="btn-primary">Save changes</button>
          </div>
        </form>
      </div>
    </div>
  );
}
