"use client";
import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Polygon, Marker, Circle, useMap } from "react-leaflet";
import L from "leaflet";
// Leaflet's stylesheet used to be @imported in globals.css, which made every one of
// the ~44 pages block on it — including the 40-odd with no map. Importing it here
// scopes it to the routes that actually render a map, and serves it from the local
// package rather than the unpkg CDN.
import "leaflet/dist/leaflet.css";
import { GpsFix } from "@phosphor-icons/react";
import { toast } from "sonner";

const icon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41],
});

// Stock Leaflet marker images are blue-only, so the "current location" pin is a
// self-contained inline-SVG divIcon instead of a second external image asset.
// className must be cleared — Leaflet's default .leaflet-div-icon styling adds
// a white box/border around divIcon content otherwise.
const redIcon = new L.DivIcon({
  html: `<svg width="25" height="41" viewBox="0 0 25 41" xmlns="http://www.w3.org/2000/svg">
    <path d="M12.5 0C5.6 0 0 5.6 0 12.5c0 9.4 12.5 28.5 12.5 28.5S25 21.9 25 12.5C25 5.6 19.4 0 12.5 0z" fill="#A13B35" stroke="#7A2C27" stroke-width="1"/>
    <circle cx="12.5" cy="12.5" r="5" fill="#FFFFFF"/>
  </svg>`,
  className: "",
  iconSize: [25, 41], iconAnchor: [12, 41],
});

const LONG_PRESS_MS = 550;
const MOVE_TOLERANCE_PX = 15;

// Unified via Pointer Events (not separate touch/mouse listeners) so a "press and
// hold" gesture behaves identically whether it's a finger or a mouse — a quick
// tap or a quick click must never add a point, only a genuine sustained hold does.
function LongPress({ onAdd }: { onAdd: (p: { latitude: number; longitude: number }) => void }) {
  const map = useMap();
  const onAddRef = useRef(onAdd);
  useEffect(() => { onAddRef.current = onAdd; }, [onAdd]);

  useEffect(() => {
    const container = map.getContainer();
    let timer: ReturnType<typeof setTimeout> | null = null;
    let startPos: L.Point | null = null;
    let lastPos: L.Point | null = null;
    let fired = false;
    let unmounted = false;
    let activePointerId: number | null = null;
    const activePointers = new Set<number>();

    const clearTimer = () => { if (timer) { clearTimeout(timer); timer = null; } };

    function onPointerDown(e: PointerEvent) {
      activePointers.add(e.pointerId);
      if (activePointers.size !== 1) { clearTimer(); return; } // 2nd pointer down mid-gesture = pinch, never a candidate
      clearTimer();
      fired = false;
      activePointerId = e.pointerId;
      startPos = lastPos = L.point(e.clientX, e.clientY);
      timer = setTimeout(() => {
        timer = null;
        if (unmounted || !startPos || !lastPos) return;
        if (lastPos.distanceTo(startPos) > MOVE_TOLERANCE_PX) return;
        const latlng = map.mouseEventToLatLng({ clientX: lastPos.x, clientY: lastPos.y } as unknown as MouseEvent);
        fired = true;
        onAddRef.current({ latitude: latlng.lat, longitude: latlng.lng });
        toast.success(`Point added at ${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}`);
      }, LONG_PRESS_MS);
    }

    function onPointerMove(e: PointerEvent) {
      if (!timer || e.pointerId !== activePointerId) return;
      lastPos = L.point(e.clientX, e.clientY);
      if (startPos && lastPos.distanceTo(startPos) > MOVE_TOLERANCE_PX) clearTimer();
    }

    function onPointerUp(e: PointerEvent) {
      activePointers.delete(e.pointerId);
      if (e.pointerId !== activePointerId) return;
      clearTimer();
      if (fired) { e.preventDefault(); fired = false; }
      activePointerId = null;
    }

    function onPointerCancel(e: PointerEvent) {
      activePointers.delete(e.pointerId);
      if (e.pointerId === activePointerId) { clearTimer(); fired = false; activePointerId = null; }
    }

    function onContextMenu(e: Event) { if (L.Browser.mobile) e.preventDefault(); }

    L.DomEvent.on(container, "pointerdown", onPointerDown as L.DomEvent.EventHandlerFn);
    L.DomEvent.on(container, "pointermove", onPointerMove as L.DomEvent.EventHandlerFn);
    L.DomEvent.on(container, "pointerup", onPointerUp as L.DomEvent.EventHandlerFn);
    L.DomEvent.on(container, "pointercancel", onPointerCancel as L.DomEvent.EventHandlerFn);
    L.DomEvent.on(container, "contextmenu", onContextMenu as L.DomEvent.EventHandlerFn);

    return () => {
      unmounted = true;
      clearTimer();
      L.DomEvent.off(container, "pointerdown", onPointerDown as L.DomEvent.EventHandlerFn);
      L.DomEvent.off(container, "pointermove", onPointerMove as L.DomEvent.EventHandlerFn);
      L.DomEvent.off(container, "pointerup", onPointerUp as L.DomEvent.EventHandlerFn);
      L.DomEvent.off(container, "pointercancel", onPointerCancel as L.DomEvent.EventHandlerFn);
      L.DomEvent.off(container, "contextmenu", onContextMenu as L.DomEvent.EventHandlerFn);
    };
  }, [map]);

  return null;
}

type CurrentLocation = { lat: number; lng: number; accuracy: number };

function FlyToLocation({ location }: { location: CurrentLocation | null }) {
  const map = useMap();
  useEffect(() => {
    if (location) map.flyTo([location.lat, location.lng], 17);
  }, [location, map]);
  if (!location) return null;
  return (
    <>
      <Marker position={[location.lat, location.lng]} icon={redIcon} />
      <Circle center={[location.lat, location.lng]} radius={location.accuracy}
              pathOptions={{ color: "#A13B35", fillColor: "#A13B35", fillOpacity: 0.15 }} />
    </>
  );
}

const MAP_CENTER: [number, number] = [26.1445, 91.7362];
const POLYGON_STYLE = { color: "#2D5134", fillColor: "#D9A036", fillOpacity: 0.35 };

export default function GpsMap({ points, onAdd, readOnly = false }: { points: { latitude: number; longitude: number }[]; onAdd: (p: { latitude: number; longitude: number }) => void; readOnly?: boolean }) {
  const [current, setCurrent] = useState<CurrentLocation | null>(null);
  const [locating, setLocating] = useState(false);

  const locate = () => {
    if (!navigator.geolocation) { toast.error("Geolocation is not supported by this browser"); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCurrent({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy });
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        if (err.code === err.PERMISSION_DENIED) toast.error("Location permission denied — enable it in your browser settings");
        else if (err.code === err.POSITION_UNAVAILABLE) toast.error("Could not determine your location");
        else toast.error("Location request timed out — try again");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  return (
    <div>
      {!readOnly && (
        <div className="flex items-center gap-2 mb-2">
          <button type="button" className="btn-secondary inline-flex items-center gap-1 text-sm"
                  onClick={locate} disabled={locating || !navigator.geolocation} data-testid="gps-locate-me">
            <GpsFix size={16} weight="bold" />{locating ? "Locating…" : "Locate me"}
          </button>
          {current && <span className="text-xs" style={{ color: "var(--text-muted)" }}>Accuracy: ~{Math.round(current.accuracy)}m</span>}
        </div>
      )}
      <div className="gps-map-wrap" style={{ height: 420 }}>
        <style>{`
          .gps-map-wrap .leaflet-container, .gps-map-wrap .leaflet-tile {
            -webkit-touch-callout: none;
          }
        `}</style>
        <MapContainer center={MAP_CENTER} zoom={13} tapHold={false} style={{ width: "100%", height: "100%" }} className="border rounded overflow-hidden">
          <TileLayer attribution="© OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {!readOnly && <LongPress onAdd={onAdd} />}
          {!readOnly && <FlyToLocation location={current} />}
          {points.map((p) => {
            const pos: [number, number] = [p.latitude, p.longitude];
            return (
              <Marker key={`${p.latitude.toFixed(6)},${p.longitude.toFixed(6)}`} position={pos} icon={icon} />
            );
          })}
          {points.length >= 3 && (
            <Polygon positions={points.map((p) => [p.latitude, p.longitude])} pathOptions={POLYGON_STYLE} />
          )}
        </MapContainer>
      </div>
    </div>
  );
}
