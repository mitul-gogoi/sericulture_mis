"use client";
import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polygon, Marker, Circle, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
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

function Click({ onAdd }: { onAdd: (p: { latitude: number; longitude: number }) => void }) {
  useMapEvents({ click(e) { onAdd({ latitude: e.latlng.lat, longitude: e.latlng.lng }); } });
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

export default function GpsMap({ points, onAdd }: { points: { latitude: number; longitude: number }[]; onAdd: (p: { latitude: number; longitude: number }) => void }) {
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
      <div className="flex items-center gap-2 mb-2">
        <button type="button" className="btn-secondary inline-flex items-center gap-1 text-sm"
                onClick={locate} disabled={locating || !navigator.geolocation} data-testid="gps-locate-me">
          <GpsFix size={16} weight="bold" />{locating ? "Locating…" : "Locate me"}
        </button>
        {current && <span className="text-xs" style={{ color: "var(--text-muted)" }}>Accuracy: ~{Math.round(current.accuracy)}m</span>}
      </div>
      <div style={{ height: 420 }} className="border rounded overflow-hidden">
        <MapContainer center={MAP_CENTER} zoom={13} style={{ width: "100%", height: "100%" }}>
          <TileLayer attribution="© OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Click onAdd={onAdd} />
          <FlyToLocation location={current} />
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
