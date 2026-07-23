"use client";
import { MapContainer, TileLayer, Polygon, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";

const icon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41],
});

function Click({ onAdd }: { onAdd: (p: { latitude: number; longitude: number }) => void }) {
  useMapEvents({ click(e) { onAdd({ latitude: e.latlng.lat, longitude: e.latlng.lng }); } });
  return null;
}

const MAP_CENTER: [number, number] = [26.1445, 91.7362];
const POLYGON_STYLE = { color: "#2D5134", fillColor: "#D9A036", fillOpacity: 0.35 };

export default function GpsMap({ points, onAdd }: { points: { latitude: number; longitude: number }[]; onAdd: (p: { latitude: number; longitude: number }) => void }) {
  return (
    <div style={{ height: 420 }} className="border rounded overflow-hidden">
      <MapContainer center={MAP_CENTER} zoom={13} style={{ width: "100%", height: "100%" }}>
        <TileLayer attribution="© OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Click onAdd={onAdd} />
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
  );
}
