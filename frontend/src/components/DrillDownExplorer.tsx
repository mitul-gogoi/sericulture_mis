"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CaretRight, CircleDashed } from "@phosphor-icons/react";
import api from "@/lib/api";
import { fyOptions } from "@/lib/fiscal";
import type { AnalyticsLevel, AnalyticsResponse } from "@/lib/types";

export interface Crumb { level: AnalyticsLevel; id: string; name: string }

/** Most levels' parent-scoping query param is simply `${level}_id` — sericulture_circle is the
 *  one exception, since its wire-level id param is `seri_circle_id`, not `sericulture_circle_id`. */
const LEVEL_ID_PARAM: Partial<Record<AnalyticsLevel, string>> = { sericulture_circle: "seri_circle_id" };

export interface DrillDownColumn<T> {
  key: string;
  label: string;
  render: (row: T) => React.ReactNode;
  className?: string;
}

export interface DimensionOption { id: string; label: string }

export interface DimensionConfig {
  label: string;
  paramName: string;
  options: DimensionOption[];
  initialId?: string;
  /** Whether to show the Month/Fiscal-year filter row alongside the dimension select.
   *  Defaults to true. Set false for point-in-time data (e.g. current stock) that has
   *  no period concept at all — the backend for those endpoints doesn't accept month/
   *  fiscal_year params, so this must stay false rather than silently sending them. */
  showPeriodFilter?: boolean;
}

export interface DrillDownExplorerProps<T extends { id: string; name: string }> {
  title: string;
  description: string;
  endpoint: string;
  levels: AnalyticsLevel[];
  /** Either a fixed column list, or a builder invoked with the fetched rows — use the
   *  latter when columns depend on data shape unknown until fetch time (e.g. a dynamic
   *  set of source-type names that only State Admin's Master Data config determines). */
  columns: DrillDownColumn<T>[] | ((rows: T[]) => DrillDownColumn<T>[]);
  dimension?: DimensionConfig;
  lockedRoot?: Crumb;
  rootLabel?: string;
  /** Seeds the breadcrumb path on first render — used for deep-linking from the
   *  Dashboard straight to (e.g.) a specific district's block-level breakdown, so the
   *  user lands with data already showing instead of an empty top-level view. */
  initialPath?: Crumb[];
}

export function DrillDownExplorer<T extends { id: string; name: string }>(props: DrillDownExplorerProps<T>) {
  const { title, description, endpoint, levels, columns, dimension, lockedRoot, rootLabel = "Assam", initialPath } = props;
  const [path, setPath] = useState<Crumb[]>(initialPath ?? []);
  const [dimId, setDimId] = useState(dimension?.initialId ?? "");
  const [month, setMonth] = useState("");
  const [fy, setFy] = useState("");

  const showPeriodFilter = !!dimension && (dimension.showPeriodFilter ?? true);

  const effectivePath = lockedRoot ? [lockedRoot, ...path] : path;
  const currentLevelIndex = Math.min(effectivePath.length, levels.length - 1);
  const currentLevel = levels[currentLevelIndex];
  const canDrillDeeper = currentLevelIndex < levels.length - 1;

  const parentParam: Record<string, string> = {};
  if (effectivePath.length > 0) {
    const last = effectivePath[effectivePath.length - 1];
    parentParam[LEVEL_ID_PARAM[last.level] ?? `${last.level}_id`] = last.id;
  }

  const { data, isLoading } = useQuery<AnalyticsResponse<T>>({
    queryKey: ["analytics", endpoint, effectivePath.map((c) => c.id).join("/"), dimId, month, fy],
    queryFn: async () => (await api.get(endpoint, {
      params: {
        level: currentLevel,
        ...parentParam,
        ...(dimension ? { [dimension.paramName]: dimId, ...(showPeriodFilter ? (fy ? { fiscal_year: fy } : month ? { month } : {}) : {}) } : {}),
      },
    })).data,
    enabled: !dimension || !!dimId,
  });

  const rows = data?.rows ?? [];
  const resolvedColumns = typeof columns === "function" ? columns(rows) : columns;

  const drillInto = (row: T) => {
    if (!canDrillDeeper) return;
    setPath([...path, { level: currentLevel, id: row.id, name: row.name }]);
  };

  return (
    <div>
      <div className="mb-5">
        <h1 className="font-heading text-3xl font-extrabold">{title}</h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>{description}</p>
      </div>

      {dimension && (
        <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap">
          <label className="label-tag">{dimension.label}</label>
          <select className="input max-w-xs" value={dimId} onChange={(e) => setDimId(e.target.value)}>
            <option value="">Select {dimension.label.toLowerCase()}</option>
            {dimension.options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
          {showPeriodFilter && (
            <>
              <label className="label-tag">Month</label>
              <input type="month" className="input max-w-xs" value={month} onChange={(e) => { setMonth(e.target.value); setFy(""); }} />
              <label className="label-tag">or fiscal year</label>
              <select className="input max-w-xs" value={fy} onChange={(e) => { setFy(e.target.value); setMonth(""); }}>
                <option value="">Select</option>
                {fyOptions().map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </>
          )}
        </div>
      )}

      <div className="flex items-center gap-1 mb-4 text-sm flex-wrap">
        <button onClick={() => setPath([])} className="font-semibold"
                style={{ color: path.length === 0 ? "inherit" : "var(--primary)" }}>
          {lockedRoot ? lockedRoot.name : rootLabel}
        </button>
        {path.map((c, i) => (
          <span key={c.id} className="flex items-center gap-1">
            <CaretRight size={12} />
            <button onClick={() => setPath(path.slice(0, i + 1))} className="font-semibold"
                    style={{ color: i === path.length - 1 ? "inherit" : "var(--primary)" }}>
              {c.name}
            </button>
          </span>
        ))}
      </div>

      {dimension && !dimId ? (
        <div className="card p-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          Select a {dimension.label.toLowerCase()} to view data.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="seri-table">
            <thead><tr>{resolvedColumns.map((c) => <th key={c.key} className={c.className}>{c.label}</th>)}</tr></thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={resolvedColumns.length} className="text-center py-8" style={{ color: "var(--text-muted)" }}>
                  <CircleDashed size={16} className="animate-spin inline mr-2" />Loading…
                </td></tr>
              )}
              {!isLoading && rows.map((row) => (
                <tr key={row.id} onClick={() => drillInto(row)}
                    className={canDrillDeeper ? "cursor-pointer hover:opacity-80" : undefined}>
                  {resolvedColumns.map((c) => <td key={c.key} className={c.className}>{c.render(row)}</td>)}
                </tr>
              ))}
              {!isLoading && rows.length === 0 && (
                <tr><td colSpan={resolvedColumns.length} className="text-center py-8" style={{ color: "var(--text-muted)" }}>No data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
