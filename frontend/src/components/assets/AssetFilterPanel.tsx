"use client";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { District, SericultureCircle, AssetType } from "@/lib/types";

export interface AssetReportFilters {
  owner_type: string; asset_type_id: string; status: string; verification_status: string;
  confidence: string; gps_status: string; district_id: string; seri_circle_id: string;
}

export function AssetFilterPanel({
  qInput, setQInput, filters, setFilters, onSubmit,
  districts, assetTypes, filterCircles, role,
}: {
  qInput: string; setQInput: (v: string) => void;
  filters: AssetReportFilters; setFilters: (v: AssetReportFilters) => void;
  onSubmit: (e: React.FormEvent) => void;
  districts: District[]; assetTypes: AssetType[]; filterCircles: SericultureCircle[]; role?: string;
}) {
  return (
    <form onSubmit={onSubmit} className="card p-4 mb-4">
      <div className="flex items-center gap-3 mb-3">
        <MagnifyingGlass size={18} color="#5C635B" />
        <input data-testid="search-assets" className="input flex-1 max-w-md" placeholder="Search by owner code, mobile or name" value={qInput} onChange={(e) => setQInput(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {role === "STATE_ADMIN" && (
          <div><label className="label-tag">District</label>
            <select className="input mt-1" value={filters.district_id} onChange={(e) => setFilters({ ...filters, district_id: e.target.value, seri_circle_id: "" })}>
              <option value="">Any</option>
              {districts.map((d) => <option key={d.id} value={d.id}>{d.district_name}</option>)}
            </select></div>
        )}
        {role !== "FIG_PRESIDENT" && (
          <div><label className="label-tag">Sericulture Circle</label>
            <select className="input mt-1" value={filters.seri_circle_id} onChange={(e) => setFilters({ ...filters, seri_circle_id: e.target.value })}>
              <option value="">Any</option>
              {filterCircles.map((c) => <option key={c.id} value={c.id}>{c.circle_name}</option>)}
            </select></div>
        )}
        <div><label className="label-tag">Owner Type</label>
          <select className="input mt-1" value={filters.owner_type} onChange={(e) => setFilters({ ...filters, owner_type: e.target.value })}>
            <option value="">Any</option><option value="FARMER">Farmer</option><option value="FIG">FIG</option>
          </select></div>
        <div><label className="label-tag">Asset Type</label>
          <select className="input mt-1" value={filters.asset_type_id} onChange={(e) => setFilters({ ...filters, asset_type_id: e.target.value })}>
            <option value="">Any</option>
            {assetTypes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select></div>
        <div><label className="label-tag">Status</label>
          <select className="input mt-1" value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">Any</option>
            <option value="FUNCTIONAL">Functional</option><option value="UNDER_REPAIR">Under Repair</option>
            <option value="NON_FUNCTIONAL">Non-Functional</option><option value="DECOMMISSIONED">Decommissioned</option>
          </select></div>
        <div><label className="label-tag">Verification Status</label>
          <select className="input mt-1" value={filters.verification_status} onChange={(e) => setFilters({ ...filters, verification_status: e.target.value })}>
            <option value="">Any</option>
            <option value="UNVERIFIED">Unverified</option><option value="CIRCLE_VERIFIED">Verified</option><option value="DISPUTED">Disputed</option>
          </select></div>
        <div><label className="label-tag">Confidence Mode</label>
          <select className="input mt-1" value={filters.confidence} onChange={(e) => setFilters({ ...filters, confidence: e.target.value })}>
            <option value="">Any</option>
            <option value="FARMER_SELF_DECLARED">Self-declared</option>
            <option value="CIRCLE_OFFICER_RECOLLECTION">Official Visit</option>
            <option value="DOCUMENTARY_EVIDENCE_SEEN">Documentary Evidence</option>
          </select></div>
        <div><label className="label-tag">GPS Status</label>
          <select className="input mt-1" value={filters.gps_status} onChange={(e) => setFilters({ ...filters, gps_status: e.target.value })}>
            <option value="">Any</option>
            <option value="Not Submitted">Not Submitted</option><option value="Pending">Pending</option>
            <option value="Verified">Verified</option><option value="Failed">Failed</option>
          </select></div>
      </div>
      <div className="flex justify-end mt-3">
        <button type="submit" data-testid="assets-search-btn" className="btn-primary">Search</button>
      </div>
    </form>
  );
}
