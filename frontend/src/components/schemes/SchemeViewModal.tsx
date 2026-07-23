"use client";
import { X } from "@phosphor-icons/react";
import type { Scheme } from "@/lib/types";

export function SchemeViewModal({
  scheme, onClose, activityName, districtName, silkTypeName, assetTypeName, casteName, religionName, educationLevelName,
}: {
  scheme: Scheme; onClose: () => void;
  activityName: (id: string) => string; districtName: (id: string) => string; silkTypeName: (id: string) => string;
  assetTypeName: (id?: string | null) => string | null; casteName: (id: string) => string;
  religionName: (id: string) => string; educationLevelName: (id: string) => string;
}) {
  const viewing = scheme;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-2xl max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="font-heading text-xl font-bold">{viewing.scheme_name}</h3>
          <button onClick={onClose}><X size={20} /></button>
        </div>
        <div className="p-5 grid grid-cols-2 gap-4 text-sm">
          <div className="col-span-2">{viewing.description || "—"}</div>
          <div><span className="label-tag">Beneficiary Kind</span><div>{viewing.beneficiary_kind}</div></div>
          <div><span className="label-tag">Support Type</span><div>{viewing.support_type}</div></div>
          <div><span className="label-tag">Budget</span><div>₹{(viewing.total_budget_rs || 0).toLocaleString()}</div></div>
          <div><span className="label-tag">Asset Granted</span><div>{assetTypeName(viewing.grants_asset_type_id) || "None"}</div></div>
          <div className="col-span-2"><span className="label-tag">Districts</span>
            <div>{viewing.target_all_districts ? "All districts" : (viewing.target_district_ids || []).map(districtName).join(", ") || "—"}</div></div>
          <div className="col-span-2"><span className="label-tag">Silk Types</span>
            <div>{(viewing.target_silk_type_ids || []).map(silkTypeName).join(", ") || "All"}</div></div>
          {viewing.beneficiary_kind === "FARMER" && (
            <>
              <div><span className="label-tag">Genders</span><div>{(viewing.target_genders || []).join(", ") || "All"}</div></div>
              <div><span className="label-tag">Farmer Types</span><div>{(viewing.target_farmer_types || []).join(", ") || "All"}</div></div>
              <div><span className="label-tag">Caste</span><div>{(viewing.target_caste_ids || []).map(casteName).join(", ") || "All"}</div></div>
              <div><span className="label-tag">Religion</span><div>{(viewing.target_religion_ids || []).map(religionName).join(", ") || "All"}</div></div>
              <div className="col-span-2"><span className="label-tag">Education Level</span>
                <div>{(viewing.target_education_level_ids || []).map(educationLevelName).join(", ") || "All"}</div></div>
              <div className="col-span-2"><span className="label-tag">PWD Only</span><div>{viewing.target_pwd_only ? "Yes" : "No"}</div></div>
            </>
          )}
          <div className="col-span-2"><span className="label-tag">Activities</span>
            <div>{(viewing.activity_ids || []).map(activityName).join(", ") || "All"}</div></div>
          <div><span className="label-tag">Notified</span><div>{viewing.notified_at ? new Date(viewing.notified_at).toLocaleString() : "Not yet published"}</div></div>
        </div>
      </div>
    </div>
  );
}
