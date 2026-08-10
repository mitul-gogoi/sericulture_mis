"use client";
import { X } from "@phosphor-icons/react";
import { stapOptgroups } from "./stapOptgroups";
import { sdoCdcName } from "@/lib/sdoCdc";
import { AssetRowsEditor, type AssetRow } from "@/components/AssetRowsEditor";
import type { District, SericultureCircle, SubdivisionCdc, SilkTypeActivityProduct, Farmer, AssetType } from "@/lib/types";

export interface FigCreateForm {
  fig_name: string; stap_id: string; seri_circle_id: string; district_id: string; formation_date: string;
  meeting_venue: string; village_name: string; panchayat_name: string; post_office: string;
  police_station: string; pin_code: string; address: string;
  member_ids: string[]; president_farmer_id: string;
  assets: AssetRow[];
}

export function FigRegisterModal({
  form, setForm, onClose, onSubmit, isStateAdmin, userDistrictId, minMembers,
  districts, circles, subdivisionCdcs, staps, unassignedFarmers, assetTypes,
}: {
  form: FigCreateForm; setForm: (f: FigCreateForm) => void; onClose: () => void; onSubmit: (e: React.FormEvent) => void;
  isStateAdmin: boolean; userDistrictId?: string | null; minMembers: number;
  districts: District[]; circles: SericultureCircle[]; subdivisionCdcs: SubdivisionCdc[]; staps: SilkTypeActivityProduct[]; unassignedFarmers: Farmer[];
  assetTypes: AssetType[];
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-2xl sm:max-w-3xl lg:max-w-4xl xl:max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">Register FIG</h3><button onClick={onClose}><X size={20} /></button>
        </div>
        <form onSubmit={onSubmit} className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="col-span-full"><label className="label-tag">FIG Name</label><input required data-testid="fig-name" className="input mt-1" value={form.fig_name} onChange={(e) => setForm({ ...form, fig_name: e.target.value })} /></div>
          <div><label className="label-tag">FIG Formation Date</label><input type="date" required className="input mt-1" value={form.formation_date} onChange={(e) => setForm({ ...form, formation_date: e.target.value })} /></div>
          <div><label className="label-tag">Primary silk type / activity / product</label>
            <select required className="input mt-1" value={form.stap_id} onChange={(e) => setForm({ ...form, stap_id: e.target.value })}>
              <option value="">Select</option>
              {stapOptgroups(staps).map(([label, group]) => (
                <optgroup key={label} label={label}>
                  {group.map((s) => <option key={s.id} value={s.id}>{s.activity_name} · {s.product_name}</option>)}
                </optgroup>
              ))}
            </select></div>
          {isStateAdmin ? (
            <div><label className="label-tag">District</label>
              <select required className="input mt-1" value={form.district_id} onChange={(e) => setForm({ ...form, district_id: e.target.value, seri_circle_id: "", member_ids: [], president_farmer_id: "" })}>
                <option value="">Select</option>{districts.map((d) => <option key={d.id} value={d.id}>{d.district_name}</option>)}
              </select></div>
          ) : (
            <div><label className="label-tag">District</label>
              <input disabled className="input mt-1" value={districts.find((d) => d.id === userDistrictId)?.district_name || ""} /></div>
          )}
          <div><label className="label-tag">Sericulture Circle</label>
            <select required className="input mt-1" value={form.seri_circle_id} onChange={(e) => setForm({ ...form, seri_circle_id: e.target.value })}>
              <option value="">Select</option>{circles.map((c) => <option key={c.id} value={c.id}>{c.circle_name}</option>)}
            </select></div>
          <div><label className="label-tag">Sub-division Office (SDO)/ CDC Office</label>
            <input disabled className="input mt-1" value={sdoCdcName(form.seri_circle_id, circles, subdivisionCdcs)} /></div>
          <div className="col-span-full"><label className="label-tag">Address line</label><input className="input mt-1" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
          <div className="col-span-full"><label className="label-tag">Village/ Town/ City</label><input className="input mt-1" value={form.village_name} onChange={(e) => setForm({ ...form, village_name: e.target.value })} /></div>
          <div><label className="label-tag">Panchayat</label><input className="input mt-1" value={form.panchayat_name} onChange={(e) => setForm({ ...form, panchayat_name: e.target.value })} /></div>
          <div><label className="label-tag">Post Office</label><input className="input mt-1" value={form.post_office} onChange={(e) => setForm({ ...form, post_office: e.target.value })} /></div>
          <div><label className="label-tag">Police Station</label><input className="input mt-1" value={form.police_station} onChange={(e) => setForm({ ...form, police_station: e.target.value })} /></div>
          <div><label className="label-tag">PIN Code</label><input className="input mt-1" value={form.pin_code} onChange={(e) => setForm({ ...form, pin_code: e.target.value })} /></div>
          <div><label className="label-tag">Meeting venue</label><input className="input mt-1" value={form.meeting_venue} onChange={(e) => setForm({ ...form, meeting_venue: e.target.value })} /></div>

          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <label className="label-tag">Existing Assets (Self-Declared)</label>
            <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>
              Optional — FIG-level shared assets (Chawki Rearing Centre, CFC, etc.) this FIG already owns.
              Individually-owned assets are recorded against each farmer instead.
            </p>
            <AssetRowsEditor value={form.assets} onChange={(next) => setForm({ ...form, assets: next })} assetTypes={assetTypes} ownerKind="FIG" />
          </div>

          <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
            <label className="label-tag">Add members (minimum {minMembers} required)</label>
            <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>Only registered farmers who aren't already in a FIG are listed.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-40 overflow-y-auto p-3 border rounded" style={{ borderColor: "var(--border)" }}>
              {unassignedFarmers.map((f) => (
                <label key={f.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.member_ids.includes(f.id)} onChange={(e) => {
                    const next = e.target.checked ? [...form.member_ids, f.id] : form.member_ids.filter((x) => x !== f.id);
                    const presStillIn = next.includes(form.president_farmer_id);
                    setForm({ ...form, member_ids: next, president_farmer_id: presStillIn ? form.president_farmer_id : "" });
                  }} />
                  {f.first_name} {f.last_name} · {f.mobile_no}
                </label>
              ))}
              {unassignedFarmers.length === 0 && <div className="col-span-full text-sm text-center py-2" style={{ color: "var(--text-muted)" }}>
                {form.district_id || userDistrictId ? "No unassigned farmers in this district" : "Select a district first"}
              </div>}
            </div>
          </div>

          {form.member_ids.length > 0 && (
            <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
              <label className="label-tag">Set president (optional)</label>
              <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>
                The president's login is the same account created at farmer registration — no separate password to set here.
              </p>
              <select className="input mt-2" value={form.president_farmer_id} onChange={(e) => setForm({ ...form, president_farmer_id: e.target.value })}>
                <option value="">Choose member</option>
                {form.member_ids.map((fid) => {
                  const fr = unassignedFarmers.find((x) => x.id === fid);
                  return <option key={fid} value={fid}>{fr?.first_name} {fr?.last_name}</option>;
                })}
              </select>
            </div>
          )}

          <div className="col-span-full flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={onClose}>Cancel</button><button type="submit" data-testid="submit-fig" className="btn-primary">Create</button></div>
        </form>
      </div>
    </div>
  );
}
