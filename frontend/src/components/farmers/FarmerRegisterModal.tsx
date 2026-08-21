"use client";
import { X } from "@phosphor-icons/react";
import FileUpload from "@/components/FileUpload";
import { LandRowsEditor, type LandRow } from "@/components/LandRowsEditor";
import { AssetRowsEditor, type AssetRow } from "@/components/AssetRowsEditor";
import { StapGroupPicker } from "./StapGroupPicker";
import { sdoCdcName } from "@/lib/sdoCdc";
import type { District, SericultureCircle, SubdivisionCdc, Caste, Religion, EducationLevel, Activity, AssetType, SilkTypeActivityProduct, Farmer } from "@/lib/types";

const stapLabel = (s: SilkTypeActivityProduct) => `${s.silk_type_name} · ${s.activity_name} · ${s.product_name}`;

export interface FarmerForm {
  first_name: string; middle_name: string; last_name: string; gender: string; date_of_birth: string;
  mobile_no: string; aadhaar_no: string; pan_no: string;
  district_id: string; seri_circle_id: string; village_name: string; gaon_panchayat: string; development_block: string;
  post_office: string; pin_code: string;
  stap_ids: string[]; primary_stap_id: string; experience_activity_ids: string[];
  farmer_type: string; education_level_id: string; experience_years: number;
  caste_id: string; religion_id: string; family_member_male: number; family_member_female: number;
  photo_path: string | null;
  account_number: string; bank_name: string; branch_name: string; ifsc_code: string; passbook_path: string | null;
  lands: LandRow[]; assets: AssetRow[];
}

function SectionHeading({ children, first }: { children: React.ReactNode; first?: boolean }) {
  return (
    <div className={first ? "col-span-full" : "col-span-full border-t pt-4"} style={first ? undefined : { borderColor: "var(--border)" }}>
      <h4 className="font-heading text-sm font-bold">{children}</h4>
    </div>
  );
}

export function FarmerRegisterModal({
  form, setForm, onClose, onSubmit, isStateAdmin,
  districts, circles, subdivisionCdcs, educationLevels, castes, religions, activities, staps, assetTypes,
  lastFarmer,
}: {
  form: FarmerForm; setForm: (f: FarmerForm) => void; onClose: () => void; onSubmit: (e: React.FormEvent) => void;
  isStateAdmin: boolean;
  districts: District[]; circles: SericultureCircle[]; subdivisionCdcs: SubdivisionCdc[]; educationLevels: EducationLevel[]; castes: Caste[];
  religions: Religion[]; activities: Activity[]; staps: SilkTypeActivityProduct[]; assetTypes: AssetType[];
  /** Most recently registered farmer, used only by the "Copy address from …" shortcut. */
  lastFarmer?: Farmer | null;
}) {
  // A DA registering a whole village retypes the same seven location fields for every
  // farmer. One click lifts them off the previous registration; every field stays editable.
  const copyAddress = () => {
    if (!lastFarmer) return;
    const sameDistrict = !isStateAdmin || !form.district_id || form.district_id === lastFarmer.district_id;
    setForm({
      ...form,
      ...(sameDistrict ? { seri_circle_id: lastFarmer.seri_circle_id || "" } : {}),
      village_name: lastFarmer.village_name || "",
      gaon_panchayat: lastFarmer.gaon_panchayat || "",
      development_block: lastFarmer.development_block || "",
      post_office: lastFarmer.post_office || "",
      pin_code: lastFarmer.pin_code || "",
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-2xl sm:max-w-3xl lg:max-w-4xl xl:max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">Register farmer</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={onSubmit} className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

          {/* ---- 1. Personal details ---- */}
          <SectionHeading first>Personal details</SectionHeading>
          <div><label className="label-tag">First name</label><input data-testid="farmer-first-name" required className="input mt-1" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></div>
          <div><label className="label-tag">Middle name</label><input className="input mt-1" value={form.middle_name} onChange={(e) => setForm({ ...form, middle_name: e.target.value })} /></div>
          <div><label className="label-tag">Last name</label><input required className="input mt-1" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div>
          <div><label className="label-tag">Gender</label>
            {/* Blank first option on purpose: gender feeds scheme eligibility, so the form must
                not silently submit "Male" for a farmer nobody actually classified. */}
            <select required className="input mt-1" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
              <option value="">Select</option>
              <option>Male</option><option>Female</option><option>Other</option>
            </select></div>
          <div><label className="label-tag">Date of birth</label><input type="date" className="input mt-1" value={form.date_of_birth} onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })} /></div>
          <div><label className="label-tag">Mobile</label><input data-testid="farmer-mobile" required className="input mt-1" value={form.mobile_no} onChange={(e) => setForm({ ...form, mobile_no: e.target.value })} /></div>
          <div><label className="label-tag">Aadhaar</label><input className="input mt-1" data-testid="farmer-aadhaar" inputMode="numeric" maxLength={14} placeholder="12-digit Aadhaar" value={form.aadhaar_no} onChange={(e) => setForm({ ...form, aadhaar_no: e.target.value })} /></div>
          <div><label className="label-tag">PAN number</label><input className="input mt-1" value={form.pan_no} onChange={(e) => setForm({ ...form, pan_no: e.target.value })} /></div>

          {/* ---- 2. Location ---- */}
          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <h4 className="font-heading text-sm font-bold">Location</h4>
              {lastFarmer && (
                <button type="button" data-testid="copy-address" className="text-xs underline" style={{ color: "var(--text-muted)" }} onClick={copyAddress}>
                  Copy address from {lastFarmer.first_name} {lastFarmer.last_name}
                </button>
              )}
            </div>
          </div>
          {isStateAdmin && (
            <div><label className="label-tag">District</label>
              <select required className="input mt-1" value={form.district_id} onChange={(e) => setForm({ ...form, district_id: e.target.value, seri_circle_id: "" })}>
                <option value="">Select</option>
                {districts.map((d) => <option key={d.id} value={d.id}>{d.district_name}</option>)}
              </select></div>
          )}
          <div><label className="label-tag">Sericulture Circle</label>
            <select required className="input mt-1" value={form.seri_circle_id} onChange={(e) => setForm({ ...form, seri_circle_id: e.target.value })}>
              <option value="">Select</option>
              {circles.map((c) => <option key={c.id} value={c.id}>{c.circle_name}</option>)}
            </select></div>
          <div><label className="label-tag">Sub-division Office (SDO)/ CDC Office</label>
            <input disabled className="input mt-1" value={sdoCdcName(form.seri_circle_id, circles, subdivisionCdcs)} /></div>
          <div className="col-span-full"><label className="label-tag">Village</label><input required className="input mt-1" value={form.village_name} onChange={(e) => setForm({ ...form, village_name: e.target.value })} /></div>
          <div><label className="label-tag">Panchayat</label><input className="input mt-1" value={form.gaon_panchayat} onChange={(e) => setForm({ ...form, gaon_panchayat: e.target.value })} /></div>
          <div><label className="label-tag">Development Block</label><input className="input mt-1" value={form.development_block} onChange={(e) => setForm({ ...form, development_block: e.target.value })} /></div>
          <div><label className="label-tag">Post Office</label><input className="input mt-1" value={form.post_office} onChange={(e) => setForm({ ...form, post_office: e.target.value })} /></div>
          <div><label className="label-tag">PIN Code</label><input className="input mt-1" value={form.pin_code} onChange={(e) => setForm({ ...form, pin_code: e.target.value })} /></div>

          {/* ---- 3. Socio-economic ---- */}
          <SectionHeading>Socio-economic details</SectionHeading>
          <div><label className="label-tag">Farmer type</label>
            <select className="input mt-1" value={form.farmer_type} onChange={(e) => setForm({ ...form, farmer_type: e.target.value })}>
              <option>Small</option><option>Marginal</option><option>Medium</option><option>Large</option>
            </select></div>
          <div><label className="label-tag">Education level</label>
            <select className="input mt-1" value={form.education_level_id} onChange={(e) => setForm({ ...form, education_level_id: e.target.value })}>
              <option value="">Select</option>
              {educationLevels.map((e) => <option key={e.id} value={e.id}>{e.education_level_name}</option>)}
            </select></div>
          <div><label className="label-tag">Experience (years)</label><input type="number" min={0} className="input mt-1" value={form.experience_years} onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })} /></div>
          <div><label className="label-tag">Caste</label>
            <select className="input mt-1" value={form.caste_id} onChange={(e) => setForm({ ...form, caste_id: e.target.value })}>
              <option value="">Select</option>
              {castes.map((c) => <option key={c.id} value={c.id}>{c.caste_name}</option>)}
            </select></div>
          <div><label className="label-tag">Religion</label>
            <select className="input mt-1" value={form.religion_id} onChange={(e) => setForm({ ...form, religion_id: e.target.value })}>
              <option value="">Select</option>
              {religions.map((r) => <option key={r.id} value={r.id}>{r.religion_name}</option>)}
            </select></div>
          <div><label className="label-tag">Family members (male)</label><input type="number" min={0} className="input mt-1" value={form.family_member_male} onChange={(e) => setForm({ ...form, family_member_male: Number(e.target.value) })} /></div>
          <div><label className="label-tag">Family members (female)</label><input type="number" min={0} className="input mt-1" value={form.family_member_female} onChange={(e) => setForm({ ...form, family_member_female: Number(e.target.value) })} /></div>

          {/* ---- 4. Sericulture activity ---- */}
          <SectionHeading>Sericulture activity</SectionHeading>
          <div className="col-span-full">
            <label className="label-tag">Silk type / activity / product</label>
            <div className="mt-2">
              <StapGroupPicker staps={staps} selected={form.stap_ids} onChange={(next) =>
                setForm({ ...form, stap_ids: next, primary_stap_id: next.includes(form.primary_stap_id) ? form.primary_stap_id : next[0] || "" })
              } />
            </div>
          </div>
          {form.stap_ids.length > 0 && (
            <div className="col-span-full"><label className="label-tag">Primary silk type / activity / product</label>
              <select required className="input mt-1" value={form.primary_stap_id} onChange={(e) => setForm({ ...form, primary_stap_id: e.target.value })}>
                {form.stap_ids.map((sid) => {
                  const s = staps.find((x) => x.id === sid);
                  return <option key={sid} value={sid}>{s ? stapLabel(s) : sid}</option>;
                })}
              </select></div>
          )}
          <div className="col-span-full">
            <label className="label-tag">Farmer experience in activities</label>
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-40 overflow-y-auto p-3 border rounded" style={{ borderColor: "var(--border)" }}>
              {activities.map((a) => (
                <label key={a.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.experience_activity_ids.includes(a.id)} onChange={(e) => {
                    const next = e.target.checked
                      ? [...form.experience_activity_ids, a.id]
                      : form.experience_activity_ids.filter((x) => x !== a.id);
                    setForm({ ...form, experience_activity_ids: next });
                  }} />
                  {a.activity_name}
                </label>
              ))}
            </div>
          </div>

          {/* ---- 5. Land ---- */}
          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <h4 className="font-heading text-sm font-bold mb-1">Land details</h4>
            <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>Optional — a farmer may have one or more land parcels; GPS boundary is added later by the FIG President.</p>
            <LandRowsEditor value={form.lands} onChange={(next) => setForm({ ...form, lands: next })} />
          </div>

          {/* ---- 6. Assets ---- */}
          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <h4 className="font-heading text-sm font-bold mb-1">Existing Assets (Self-Declared)</h4>
            <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>
              Optional — durable assets (rearing house, mountage, reeling machine, etc.) this farmer already owns.
              FIG-level shared assets (CFC, CRC) are recorded against the FIG instead.
            </p>
            <AssetRowsEditor value={form.assets} onChange={(next) => setForm({ ...form, assets: next })} assetTypes={assetTypes} ownerKind="FARMER" />
          </div>

          {/* ---- 7. Bank & documents ---- */}
          <SectionHeading>Bank &amp; documents</SectionHeading>
          <div className="col-span-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="label-tag block mb-2">Photo</label>
              <FileUpload label="Upload photo" testId="farmer-photo-upload" value={form.photo_path}
                          onChange={(p) => setForm({ ...form, photo_path: p })} accept=".jpg,.jpeg,.png,.webp"
                          category="farmer_photo" districtId={form.district_id} seriCircleId={form.seri_circle_id}
                          farmerIdentifier={form.mobile_no} />
            </div>
            <div>
              <label className="label-tag block mb-2">Bank passbook</label>
              <FileUpload label="Upload passbook" testId="farmer-passbook-upload" value={form.passbook_path}
                          onChange={(p) => setForm({ ...form, passbook_path: p })}
                          category="farmer_passbook" districtId={form.district_id} seriCircleId={form.seri_circle_id}
                          farmerIdentifier={form.mobile_no} />
            </div>
            <div><label className="label-tag">Account Number</label><input className="input mt-1" value={form.account_number}
                  onChange={(e) => setForm({ ...form, account_number: e.target.value })} /></div>
            <div><label className="label-tag">Bank Name</label><input className="input mt-1" value={form.bank_name}
                  onChange={(e) => setForm({ ...form, bank_name: e.target.value })} /></div>
            <div><label className="label-tag">Branch Name</label><input className="input mt-1" value={form.branch_name}
                  onChange={(e) => setForm({ ...form, branch_name: e.target.value })} /></div>
            <div><label className="label-tag">IFSC Code</label><input className="input mt-1" value={form.ifsc_code}
                  onChange={(e) => setForm({ ...form, ifsc_code: e.target.value })} /></div>
          </div>

          <div className="col-span-full flex justify-end gap-2 mt-2">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" data-testid="submit-farmer" className="btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  );
}
