"use client";
import { stapOptgroups } from "./stapOptgroups";
import { sdoCdcName } from "@/lib/sdoCdc";
import { AssetRowsEditor, type AssetRow } from "@/components/AssetRowsEditor";
import { AssetsList } from "@/components/AssetsList";
import type { FigDetail, District, SericultureCircle, SubdivisionCdc, SilkTypeActivityProduct, AssetType, AssetInstance } from "@/lib/types";

export interface FigEditFormState {
  fig_name: string; stap_id: string; formation_date: string; meeting_venue: string;
  village_name: string; panchayat_name: string; post_office: string; police_station: string;
  pin_code: string; address: string;
}

export function FigEditForm({
  detail, editForm, setEditForm, staps, districts, allCircles, subdivisionCdcs, onCancel, onSave,
  assetTypes, editAssets, editNewAssets, setEditNewAssets, onDeleteAsset,
}: {
  detail: FigDetail; editForm: FigEditFormState; setEditForm: (f: FigEditFormState) => void;
  staps: SilkTypeActivityProduct[]; districts: District[]; allCircles: SericultureCircle[]; subdivisionCdcs: SubdivisionCdc[];
  onCancel: () => void; onSave: () => void;
  assetTypes: AssetType[]; editAssets: AssetInstance[];
  editNewAssets: AssetRow[]; setEditNewAssets: (rows: AssetRow[]) => void; onDeleteAsset: (assetId: string) => void;
}) {
  return (
    <div className="mb-5 border-b pb-5" style={{ borderColor: "var(--border)" }}>
      <h4 className="font-heading font-bold mb-3">Edit FIG</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="col-span-full"><label className="label-tag">FIG Name</label><input className="input mt-1" value={editForm.fig_name} onChange={(e) => setEditForm({ ...editForm, fig_name: e.target.value })} /></div>
        <div><label className="label-tag">FIG Formation Date</label><input type="date" className="input mt-1" value={editForm.formation_date} onChange={(e) => setEditForm({ ...editForm, formation_date: e.target.value })} /></div>
        <div><label className="label-tag">Primary silk type / activity / product</label>
          <select className="input mt-1" value={editForm.stap_id} onChange={(e) => setEditForm({ ...editForm, stap_id: e.target.value })}>
            {stapOptgroups(staps).map(([label, group]) => (
              <optgroup key={label} label={label}>
                {group.map((s) => <option key={s.id} value={s.id}>{s.activity_name} · {s.product_name}</option>)}
              </optgroup>
            ))}
          </select></div>
        <div><label className="label-tag">District</label>
          <input disabled className="input mt-1" value={districts.find((d) => d.id === detail.district_id)?.district_name || ""} /></div>
        <div><label className="label-tag">Sericulture Circle</label>
          <input disabled className="input mt-1" value={allCircles.find((c) => c.id === detail.seri_circle_id)?.circle_name || ""} /></div>
        <div><label className="label-tag">Sub-division Office (SDO)/ CDC Office</label>
          <input disabled className="input mt-1" value={sdoCdcName(detail.seri_circle_id, allCircles, subdivisionCdcs)} /></div>
        <div className="col-span-full"><label className="label-tag">Address line</label><input className="input mt-1" value={editForm.address} onChange={(e) => setEditForm({ ...editForm, address: e.target.value })} /></div>
        <div className="col-span-full"><label className="label-tag">Village/ Town/ City</label><input className="input mt-1" value={editForm.village_name} onChange={(e) => setEditForm({ ...editForm, village_name: e.target.value })} /></div>
        <div><label className="label-tag">Panchayat</label><input className="input mt-1" value={editForm.panchayat_name} onChange={(e) => setEditForm({ ...editForm, panchayat_name: e.target.value })} /></div>
        <div><label className="label-tag">Post Office</label><input className="input mt-1" value={editForm.post_office} onChange={(e) => setEditForm({ ...editForm, post_office: e.target.value })} /></div>
        <div><label className="label-tag">Police Station</label><input className="input mt-1" value={editForm.police_station} onChange={(e) => setEditForm({ ...editForm, police_station: e.target.value })} /></div>
        <div><label className="label-tag">PIN Code</label><input className="input mt-1" value={editForm.pin_code} onChange={(e) => setEditForm({ ...editForm, pin_code: e.target.value })} /></div>
        <div><label className="label-tag">Meeting venue</label><input className="input mt-1" value={editForm.meeting_venue} onChange={(e) => setEditForm({ ...editForm, meeting_venue: e.target.value })} /></div>
      </div>
      <div className="border-t pt-4 mt-4" style={{ borderColor: "var(--border)" }}>
        <label className="label-tag">Existing Assets (Self-Declared)</label>
        {editAssets.length > 0 && (
          <div className="mt-2 mb-3">
            <AssetsList assets={editAssets} onDelete={onDeleteAsset} />
          </div>
        )}
        <p className="text-xs mt-1 mb-2" style={{ color: "var(--text-muted)" }}>
          Add another existing asset — for a newly self-procured item, with a real procurement date.
          Individually-owned assets are recorded against each farmer instead.
        </p>
        <AssetRowsEditor value={editNewAssets} onChange={setEditNewAssets} assetTypes={assetTypes} ownerKind="FIG" />
      </div>
      <div className="flex justify-end gap-2 mt-3">
        <button className="btn-secondary" onClick={onCancel}>Cancel</button>
        <button className="btn-primary" onClick={onSave}>Save</button>
      </div>
    </div>
  );
}
