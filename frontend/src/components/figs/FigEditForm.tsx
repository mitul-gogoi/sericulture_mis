"use client";
import { FigActivityPicker } from "./FigActivityPicker";
import { lacName } from "@/lib/lac";
import { AssetRowsEditor, type AssetRow } from "@/components/AssetRowsEditor";
import { AssetsList } from "@/components/AssetsList";
import { FigDocumentsStep } from "@/components/figs/FigDocumentsStep";
import type { FigDetail, District, SericultureCircle, Lac, SilkTypeActivityProduct, AssetType, AssetInstance } from "@/lib/types";

export interface FigEditFormState {
  fig_name: string; silk_type_id: string; activity_ids: string[];
  formation_date: string; meeting_venue: string;
  village_name: string; panchayat_name: string; post_office: string;
  pin_code: string; address: string;
  minutes_path: string | null; group_photo_path: string | null;
}

export function FigEditForm({
  detail, editForm, setEditForm, staps, districts, allCircles, lacs, onCancel, onSave,
  assetTypes, editAssets, editNewAssets, setEditNewAssets, onDeleteAsset,
}: {
  detail: FigDetail; editForm: FigEditFormState; setEditForm: (f: FigEditFormState) => void;
  staps: SilkTypeActivityProduct[]; districts: District[]; allCircles: SericultureCircle[]; lacs: Lac[];
  onCancel: () => void; onSave: () => void;
  assetTypes: AssetType[]; editAssets: AssetInstance[];
  editNewAssets: AssetRow[]; setEditNewAssets: (rows: AssetRow[]) => void; onDeleteAsset: (assetId: string) => void;
}) {
  // The picker only offers activities the FIG's own members perform, so it needs their
  // farmer records — the same rule the server re-checks on save.
  const memberFarmers = (detail.members || [])
    .filter((m) => m.is_active && m.farmer)
    .map((m) => m.farmer!);
  return (
    <div className="mb-5 border-b pb-5" style={{ borderColor: "var(--border)" }}>
      <h4 className="font-heading font-bold mb-3">Edit FIG</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="col-span-full"><h4 className="font-heading text-sm font-bold">FIG details</h4></div>
        <div className="col-span-full"><label className="label-tag">FIG Name</label><input className="input mt-1" value={editForm.fig_name} onChange={(e) => setEditForm({ ...editForm, fig_name: e.target.value })} /></div>
        <div><label className="label-tag">FIG Formation Date</label><input type="date" className="input mt-1" value={editForm.formation_date} onChange={(e) => setEditForm({ ...editForm, formation_date: e.target.value })} /></div>
        <div className="col-span-full"><label className="label-tag">Primary silk type / activity</label>
          <div className="mt-1">
            <FigActivityPicker staps={staps} members={memberFarmers}
                               silkTypeId={editForm.silk_type_id} activityIds={editForm.activity_ids}
                               onChange={(silk, acts) => setEditForm({ ...editForm, silk_type_id: silk, activity_ids: acts })} />
          </div></div>
        <div className="col-span-full border-t pt-4" style={{ borderColor: "var(--border)" }}>
          <h4 className="font-heading text-sm font-bold">Location</h4></div>
        <div><label className="label-tag">District</label>
          <input disabled className="input mt-1" value={districts.find((d) => d.id === detail.district_id)?.district_name || ""} /></div>
        <div><label className="label-tag">Sericulture Circle</label>
          <input disabled className="input mt-1" value={allCircles.find((c) => c.id === detail.seri_circle_id)?.circle_name || ""} /></div>
        <div><label className="label-tag">LAC</label>
          <input disabled className="input mt-1" value={lacName(detail.seri_circle_id, allCircles, lacs)} /></div>
        <div className="col-span-full"><label className="label-tag">Address line</label><input className="input mt-1" value={editForm.address} onChange={(e) => setEditForm({ ...editForm, address: e.target.value })} /></div>
        <div className="col-span-full"><label className="label-tag">Village/ Town/ City</label><input className="input mt-1" value={editForm.village_name} onChange={(e) => setEditForm({ ...editForm, village_name: e.target.value })} /></div>
        <div><label className="label-tag">Panchayat</label><input className="input mt-1" value={editForm.panchayat_name} onChange={(e) => setEditForm({ ...editForm, panchayat_name: e.target.value })} /></div>
        <div><label className="label-tag">Post Office</label><input className="input mt-1" value={editForm.post_office} onChange={(e) => setEditForm({ ...editForm, post_office: e.target.value })} /></div>
        <div><label className="label-tag">PIN Code</label><input className="input mt-1" value={editForm.pin_code} onChange={(e) => setEditForm({ ...editForm, pin_code: e.target.value })} /></div>
        <div><label className="label-tag">Meeting venue</label><input className="input mt-1" value={editForm.meeting_venue} onChange={(e) => setEditForm({ ...editForm, meeting_venue: e.target.value })} /></div>
      </div>
      <div className="border-t pt-4 mt-4" style={{ borderColor: "var(--border)" }}>
        <h4 className="font-heading text-sm font-bold mb-3">FIG documents</h4>
        <FigDocumentsStep
          figName={detail.fig_name} figCode={detail.fig_code}
          districtId={detail.district_id} seriCircleId={detail.seri_circle_id}
          value={{ minutes_path: editForm.minutes_path, group_photo_path: editForm.group_photo_path }}
          onChange={(d) => setEditForm({ ...editForm, ...d })}
        />
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
