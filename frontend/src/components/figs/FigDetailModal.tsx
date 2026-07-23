"use client";
import { X, PencilSimple, Power } from "@phosphor-icons/react";
import { FigDetailView } from "./FigDetailView";
import { FigEditForm, type FigEditFormState } from "./FigEditForm";
import { FigMembersPanel } from "./FigMembersPanel";
import { FigPresidentPanel, type PresForm } from "./FigPresidentPanel";
import type { FigDetail, District, SericultureCircle, SilkTypeActivityProduct, Farmer } from "@/lib/types";

export function FigDetailModal({
  detail, staps, districts, allCircles,
  editingFig, editForm, setEditForm, onEditClick, onSaveEdit, onCancelEdit,
  canEditDetails, canToggleActive, canManageMembership, onToggleActive, onClose,
  memberFarmer, setMemberFarmer, detailUnassignedFarmers, onAddMember,
  presForm, setPresForm, onSetPresident, resetPassword, setResetPassword, onResetPassword,
}: {
  detail: FigDetail; staps: SilkTypeActivityProduct[]; districts: District[]; allCircles: SericultureCircle[];
  editingFig: boolean; editForm: FigEditFormState | null; setEditForm: (f: FigEditFormState) => void;
  onEditClick: () => void; onSaveEdit: () => void; onCancelEdit: () => void;
  canEditDetails: boolean; canToggleActive: boolean; canManageMembership: boolean;
  onToggleActive: () => void; onClose: () => void;
  memberFarmer: string; setMemberFarmer: (v: string) => void; detailUnassignedFarmers: Farmer[]; onAddMember: () => void;
  presForm: PresForm; setPresForm: (f: PresForm) => void; onSetPresident: () => void;
  resetPassword: string; setResetPassword: (v: string) => void; onResetPassword: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(26,29,26,0.45)" }}>
      <div className="card w-full max-w-2xl sm:max-w-3xl lg:max-w-4xl xl:max-w-5xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b" style={{ borderColor: "var(--border)" }}>
          <div><h3 className="font-heading text-xl font-bold">{detail.fig_name}</h3>
            <div className="text-xs label-tag flex items-center gap-2 mt-1">{detail.fig_code} {!detail.is_active && <span className="badge badge-error">Inactive</span>}</div></div>
          <div className="flex items-center gap-2">
            {canEditDetails && (
              <button onClick={onEditClick} className="btn-secondary px-3 py-1.5 text-sm inline-flex items-center gap-1"><PencilSimple size={14} weight="bold" />Edit</button>
            )}
            {canToggleActive && (
              <button onClick={onToggleActive} className="btn-secondary px-3 py-1.5 text-sm inline-flex items-center gap-1">
                <Power size={14} weight="bold" />{detail.is_active ? "Deactivate" : "Activate"}
              </button>
            )}
            <button onClick={onClose}><X size={20} /></button>
          </div>
        </div>
        <div className="p-5">
          {!editingFig && <FigDetailView detail={detail} staps={staps} districts={districts} allCircles={allCircles} />}
          {editingFig && editForm && (
            <FigEditForm detail={detail} editForm={editForm} setEditForm={setEditForm} staps={staps}
                        districts={districts} allCircles={allCircles} onCancel={onCancelEdit} onSave={onSaveEdit} />
          )}
          <FigMembersPanel members={detail.members} canManage={canManageMembership}
                          detailUnassignedFarmers={detailUnassignedFarmers} memberFarmer={memberFarmer}
                          setMemberFarmer={setMemberFarmer} onAddMember={onAddMember} />
          {canManageMembership && (
            <FigPresidentPanel members={detail.members} presForm={presForm} setPresForm={setPresForm}
                              onSetPresident={onSetPresident} resetPassword={resetPassword}
                              setResetPassword={setResetPassword} onResetPassword={onResetPassword} />
          )}
        </div>
      </div>
    </div>
  );
}
