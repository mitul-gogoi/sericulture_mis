"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { LabelledBarChart } from "./charts";

/**
 * District choropleth, drawn as inline SVG straight from a GeoJSON file.
 *
 * Deliberately NOT a Leaflet map: a tile basemap would need to reach OpenStreetMap, and
 * the State Data Center box (and government client machines) may have no internet. Plain
 * SVG polygons need no network, no tile server and no extra dependency.
 *
 * The boundary file is NOT bundled — drop a FeatureCollection of Assam districts at
 * `frontend/public/geo/assam-districts.json`. Until then this renders the ranked-bar
 * fallback rather than an error, so the dashboard is never broken by a missing file.
 */

export interface DistrictStat {
  district_id: string;
  district_name: string;
  submitted: number;
  total: number;
  pct: number;
}

// Sequential ramp — one hue, light to dark. Luminance verified strictly monotonic.
const RAMP = ["#EAF2EC", "#C6DCCB", "#9BC2A5", "#6BA47C", "#3E7C54", "#2D5134"];
const NO_DATA = "#E6E4DF";

function rampColor(pct: number): string {
  if (pct <= 0) return RAMP[0];
  const i = Math.min(RAMP.length - 1, Math.floor((pct / 100) * RAMP.length));
  return RAMP[i];
}

/** Boundary files in the wild disagree on which property holds the district name. */
const NAME_KEYS = ["district", "DISTRICT", "NAME_2", "dtname", "DTNAME", "name", "NAME", "Dist_Name", "district_name"];
function featureName(props: Record<string, unknown> | null): string {
  if (!props) return "";
  for (const k of NAME_KEYS) {
    const v = props[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

/** Loose match — boundary files vary on case, spacing and "Kamrup Metro" vs "Kamrup Metropolitan". */
const normalise = (s: string) => s.toLowerCase().replace(/[^a-z]/g, "");

type Ring = [number, number][];
function ringsOf(geometry: any): Ring[] {
  if (!geometry) return [];
  if (geometry.type === "Polygon") return geometry.coordinates as Ring[];
  if (geometry.type === "MultiPolygon") return (geometry.coordinates as Ring[][][]).flat() as unknown as Ring[];
  return [];
}

export function AssamMap({ stats }: { stats: DistrictStat[] }) {
  const [geo, setGeo] = useState<any | null>(null);
  const [failed, setFailed] = useState(false);
  const [hover, setHover] = useState<{ name: string; x: number; y: number; stat?: DistrictStat } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    fetch("/geo/assam-districts.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => { if (alive) setGeo(d); })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, []);

  const statByName = useMemo(() => {
    const m = new Map<string, DistrictStat>();
    stats.forEach((s) => m.set(normalise(s.district_name), s));
    return m;
  }, [stats]);

  const shapes = useMemo(() => {
    const features = geo?.features;
    if (!Array.isArray(features) || features.length === 0) return null;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const f of features) {
      for (const ring of ringsOf(f.geometry)) {
        for (const [lng, lat] of ring) {
          if (lng < minX) minX = lng; if (lng > maxX) maxX = lng;
          if (lat < minY) minY = lat; if (lat > maxY) maxY = lat;
        }
      }
    }
    if (!isFinite(minX)) return null;

    // Equirectangular with a cos(lat) correction so the state is not horizontally stretched.
    const W = 1000;
    const kx = Math.cos(((minY + maxY) / 2) * Math.PI / 180);
    const spanX = (maxX - minX) * kx || 1;
    const spanY = (maxY - minY) || 1;
    const H = Math.round((W * spanY) / spanX);
    const px = (lng: number) => ((lng - minX) * kx / spanX) * W;
    const py = (lat: number) => H - ((lat - minY) / spanY) * H;

    const out = features.map((f: any, i: number) => {
      const name = featureName(f.properties);
      const stat = statByName.get(normalise(name));
      const d = ringsOf(f.geometry)
        .map((ring) => ring.map(([lng, lat], j) => `${j === 0 ? "M" : "L"}${px(lng).toFixed(1)},${py(lat).toFixed(1)}`).join("") + "Z")
        .join(" ");
      return { key: `${name || "feature"}-${i}`, name, stat, d };
    });
    return { width: W, height: H, features: out };
  }, [geo, statByName]);

  // A boundary file that does not match the district master looks exactly like missing
  // data unless it is called out, so surface the count rather than silently greying out.
  const unmatched = shapes ? shapes.features.filter((f) => !f.stat).map((f) => f.name || "(unnamed)") : [];

  if (failed || (geo && !shapes)) {
    return (
      <>
        <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
          District boundary file not installed — showing a ranked list instead. Add a GeoJSON
          FeatureCollection at <code>public/geo/assam-districts.json</code> to enable the map.
        </p>
        <RankedDistricts stats={stats} />
      </>
    );
  }

  if (!shapes) {
    return <div className="text-sm text-center py-10" style={{ color: "var(--text-muted)" }}>Loading map…</div>;
  }

  return (
    <div ref={wrapRef} className="relative">
      <svg viewBox={`0 0 ${shapes.width} ${shapes.height}`} className="w-full h-auto" role="img"
           aria-label="Assam districts shaded by monthly submission rate">
        {shapes.features.map((f) => (
          <path
            key={f.key} d={f.d}
            fill={f.stat ? rampColor(f.stat.pct) : NO_DATA}
            stroke="#FFFFFF" strokeWidth={1.2} strokeLinejoin="round"
            style={{ cursor: f.stat ? "pointer" : "default", transition: "fill 0.2s" }}
            onMouseEnter={(e) => {
              const box = wrapRef.current?.getBoundingClientRect();
              setHover({ name: f.name, stat: f.stat, x: e.clientX - (box?.left ?? 0), y: e.clientY - (box?.top ?? 0) });
            }}
            onMouseMove={(e) => {
              const box = wrapRef.current?.getBoundingClientRect();
              setHover((h) => (h ? { ...h, x: e.clientX - (box?.left ?? 0), y: e.clientY - (box?.top ?? 0) } : h));
            }}
            onMouseLeave={() => setHover(null)}
          />
        ))}
      </svg>

      {hover && (
        <div className="card absolute pointer-events-none z-10" style={{
          left: Math.min(hover.x + 12, (wrapRef.current?.clientWidth ?? 400) - 190),
          top: hover.y + 12, padding: "8px 10px", boxShadow: "var(--elev-2)", minWidth: 160,
        }}>
          <div className="text-xs font-bold">{hover.name || "Unknown district"}</div>
          {hover.stat ? (
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              {hover.stat.submitted} of {hover.stat.total} FIGs submitted
              <span className="font-bold ml-1" style={{ color: "var(--text)" }}>({hover.stat.pct}%)</span>
            </div>
          ) : (
            <div className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>No matching district record</div>
          )}
        </div>
      )}

      <div className="flex items-center gap-3 mt-4 flex-wrap">
        <span className="label-tag">Submission rate</span>
        <div className="flex items-center gap-1">
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>0%</span>
          {RAMP.map((c) => <span key={c} style={{ width: 26, height: 10, background: c, display: "inline-block" }} />)}
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>100%</span>
        </div>
        <span className="inline-flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
          <span style={{ width: 12, height: 10, background: NO_DATA, display: "inline-block" }} /> no data
        </span>
      </div>

      {unmatched.length > 0 && (
        <p className="text-xs mt-2" style={{ color: "var(--warning)" }}>
          {unmatched.length} boundary {unmatched.length === 1 ? "shape" : "shapes"} did not match a district
          record ({unmatched.slice(0, 3).join(", ")}{unmatched.length > 3 ? "…" : ""}) — the boundary file may
          predate the current district list.
        </p>
      )}
    </div>
  );
}

/** Fallback and companion view — a map cannot be read numerically. */
export function RankedDistricts({ stats, limit = 10 }: { stats: DistrictStat[]; limit?: number }) {
  const rows = [...stats].sort((a, b) => a.pct - b.pct).slice(0, limit).map((d) => ({
    name: d.district_name,
    value: d.pct,
    sub: `${d.submitted}/${d.total}`,
    color: rampColor(d.pct),
  }));
  return <LabelledBarChart data={rows} unit="%" height={22} />;
}
