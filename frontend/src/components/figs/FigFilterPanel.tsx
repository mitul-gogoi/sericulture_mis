"use client";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { stapOptgroups } from "./stapOptgroups";
import type { District, SericultureCircle, SilkTypeActivityProduct } from "@/lib/types";

export interface FigReportFilters {
  stap_id: string; district_id: string; seri_circle_id: string;
  formation_date_from: string; formation_date_to: string; is_active: string;
}

export function FigFilterPanel({
  qInput, setQInput, filters, setFilters, onSubmit, staps, districts, filterCircles, role,
}: {
  qInput: string; setQInput: (v: string) => void;
  filters: FigReportFilters; setFilters: (v: FigReportFilters) => void;
  onSubmit: (e: React.FormEvent) => void;
  staps: SilkTypeActivityProduct[]; districts: District[]; filterCircles: SericultureCircle[]; role?: string;
}) {
  return (
    <form onSubmit={onSubmit} className="card p-4 mb-4">
      <div className="flex items-center gap-3 mb-3">
        <MagnifyingGlass size={18} color="#5C635B" />
        <input data-testid="search-figs" className="input flex-1 max-w-md" placeholder="Search by FIG code, FIG name, member code or mobile" value={qInput} onChange={(e) => setQInput(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div><label className="label-tag">Silk type / activity / product</label>
          <select className="input mt-1" value={filters.stap_id} onChange={(e) => setFilters({ ...filters, stap_id: e.target.value })}>
            <option value="">Any</option>
            {stapOptgroups(staps).map(([label, group]) => (
              <optgroup key={label} label={label}>
                {group.map((s) => <option key={s.id} value={s.id}>{s.activity_name} · {s.product_name}</option>)}
              </optgroup>
            ))}
          </select></div>
        {role === "STATE_ADMIN" && (
          <div><label className="label-tag">District</label>
            <select className="input mt-1" value={filters.district_id} onChange={(e) => setFilters({ ...filters, district_id: e.target.value, seri_circle_id: "" })}>
              <option value="">Any</option>
              {districts.map((d) => <option key={d.id} value={d.id}>{d.district_name}</option>)}
            </select></div>
        )}
        <div><label className="label-tag">Sericulture Circle</label>
          <select className="input mt-1" value={filters.seri_circle_id} onChange={(e) => setFilters({ ...filters, seri_circle_id: e.target.value })}>
            <option value="">Any</option>
            {filterCircles.map((c) => <option key={c.id} value={c.id}>{c.circle_name}</option>)}
          </select></div>
        <div><label className="label-tag">Formation date from</label>
          <input type="date" className="input mt-1" value={filters.formation_date_from} onChange={(e) => setFilters({ ...filters, formation_date_from: e.target.value })} /></div>
        <div><label className="label-tag">Formation date to</label>
          <input type="date" className="input mt-1" value={filters.formation_date_to} onChange={(e) => setFilters({ ...filters, formation_date_to: e.target.value })} /></div>
        <div><label className="label-tag">Status</label>
          <select className="input mt-1" value={filters.is_active} onChange={(e) => setFilters({ ...filters, is_active: e.target.value })}>
            <option value="">Any</option><option value="true">Active</option><option value="false">Inactive</option>
          </select></div>
      </div>
      <div className="flex justify-end mt-3">
        <button type="submit" data-testid="figs-search-btn" className="btn-primary">Search</button>
      </div>
    </form>
  );
}
