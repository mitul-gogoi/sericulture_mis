"use client";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { District, SericultureCircle, Caste, Religion, EducationLevel } from "@/lib/types";

export interface FarmerReportFilters {
  gender: string; education_level_id: string; caste_id: string; religion_id: string;
  district_id: string; seri_circle_id: string; experience_min: string; experience_max: string;
  has_bank_details: string; is_active: string; has_fig: string;
}

export function FarmerFilterPanel({
  qInput, setQInput, filters, setFilters, onSubmit,
  districts, educationLevels, castes, religions, filterCircles, role,
}: {
  qInput: string; setQInput: (v: string) => void;
  filters: FarmerReportFilters; setFilters: (v: FarmerReportFilters) => void;
  onSubmit: (e: React.FormEvent) => void;
  districts: District[]; educationLevels: EducationLevel[]; castes: Caste[]; religions: Religion[];
  filterCircles: SericultureCircle[]; role?: string;
}) {
  return (
    <form onSubmit={onSubmit} className="card p-4 mb-4">
      <div className="flex items-center gap-3 mb-3">
        <MagnifyingGlass size={18} color="#5C635B" />
        <input data-testid="search-farmers" className="input flex-1 max-w-md" placeholder="Search by name, mobile or code" value={qInput} onChange={(e) => setQInput(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div><label className="label-tag">Gender</label>
          <select className="input mt-1" value={filters.gender} onChange={(e) => setFilters({ ...filters, gender: e.target.value })}>
            <option value="">Any</option><option>Male</option><option>Female</option><option>Other</option>
          </select></div>
        <div><label className="label-tag">Education level</label>
          <select className="input mt-1" value={filters.education_level_id} onChange={(e) => setFilters({ ...filters, education_level_id: e.target.value })}>
            <option value="">Any</option>
            {educationLevels.map((e) => <option key={e.id} value={e.id}>{e.education_level_name}</option>)}
          </select></div>
        <div><label className="label-tag">Caste</label>
          <select className="input mt-1" value={filters.caste_id} onChange={(e) => setFilters({ ...filters, caste_id: e.target.value })}>
            <option value="">Any</option>
            {castes.map((c) => <option key={c.id} value={c.id}>{c.caste_name}</option>)}
          </select></div>
        <div><label className="label-tag">Religion</label>
          <select className="input mt-1" value={filters.religion_id} onChange={(e) => setFilters({ ...filters, religion_id: e.target.value })}>
            <option value="">Any</option>
            {religions.map((r) => <option key={r.id} value={r.id}>{r.religion_name}</option>)}
          </select></div>
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
        <div><label className="label-tag">Experience min (yrs)</label>
          <input type="number" min={0} className="input mt-1" value={filters.experience_min} onChange={(e) => setFilters({ ...filters, experience_min: e.target.value })} /></div>
        <div><label className="label-tag">Experience max (yrs)</label>
          <input type="number" min={0} className="input mt-1" value={filters.experience_max} onChange={(e) => setFilters({ ...filters, experience_max: e.target.value })} /></div>
        <div><label className="label-tag">Bank details</label>
          <select className="input mt-1" value={filters.has_bank_details} onChange={(e) => setFilters({ ...filters, has_bank_details: e.target.value })}>
            <option value="">Any</option><option value="true">With bank details</option><option value="false">Without bank details</option>
          </select></div>
        <div><label className="label-tag">Status</label>
          <select className="input mt-1" value={filters.is_active} onChange={(e) => setFilters({ ...filters, is_active: e.target.value })}>
            <option value="">Any</option><option value="true">Active</option><option value="false">Inactive</option>
          </select></div>
        {role !== "FIG_PRESIDENT" && (
          <div><label className="label-tag">FIG Membership</label>
            <select className="input mt-1" value={filters.has_fig} onChange={(e) => setFilters({ ...filters, has_fig: e.target.value })}>
              <option value="">Any</option><option value="true">FIG Member</option><option value="false">Solo</option>
            </select></div>
        )}
      </div>
      <div className="flex justify-end mt-3">
        <button type="submit" data-testid="farmers-search-btn" className="btn-primary">Search</button>
      </div>
    </form>
  );
}
