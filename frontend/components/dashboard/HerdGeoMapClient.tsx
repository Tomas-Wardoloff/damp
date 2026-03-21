"use client";

import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";

export type HerdMapPoint = {
  cowId: number;
  lat: number;
  lng: number;
  timestamp: string;
  healthStatus: string | null;
  confidence: number | null;
  healthCreatedAt: string | null;
  primaryStatus: string | null;
  primaryConfidence: number | null;
  secondaryStatus: string | null;
  secondaryConfidence: number | null;
};

interface HerdGeoMapClientProps {
  points: HerdMapPoint[];
}

const STATUS_COLORS: Record<string, string> = {
  SANA: "#22c55e",
  SUBCLINICA: "#f59e0b",
  CLINICA: "#ef4444",
  MASTITIS: "#dc2626",
  CELO: "#3b82f6",
  FEBRIL: "#f97316",
  DIGESTIVO: "#eab308",
};

function getColor(status: string | null): string {
  if (!status) return "#94a3b8";
  return STATUS_COLORS[status] || "#94a3b8";
}

function getCenter(points: HerdMapPoint[]): [number, number] {
  if (points.length === 0) return [-34.6037, -58.3816];

  const sum = points.reduce(
    (acc, point) => {
      return { lat: acc.lat + point.lat, lng: acc.lng + point.lng };
    },
    { lat: 0, lng: 0 },
  );

  return [sum.lat / points.length, sum.lng / points.length];
}

export function HerdGeoMapClient({ points }: HerdGeoMapClientProps) {
  const center = getCenter(points);

  return (
    <MapContainer
      center={center}
      zoom={14}
      minZoom={4}
      maxZoom={19}
      scrollWheelZoom
      className="h-full w-full rounded-xl"
    >
      <TileLayer
        attribution='Tiles &copy; Esri'
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
      />

      {points.map((point) => {
        const color = getColor(point.healthStatus);
        return (
          <CircleMarker
            key={`${point.cowId}-${point.timestamp}`}
            center={[point.lat, point.lng]}
            radius={8}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.8,
              weight: 2,
            }}
          >
            <Popup>
              <div className="text-sm">
                <div><strong>Vaca #{point.cowId}</strong></div>
                <div>Estado: {point.healthStatus || "SIN DATOS"}</div>
                <div>
                  Confianza:{" "}
                  {point.confidence === null
                    ? "N/A"
                    : `${(point.confidence * 100).toFixed(1)}%`}
                </div>
                <div>
                  Primario: {point.primaryStatus || "N/A"}
                  {point.primaryConfidence === null ? "" : ` (${(point.primaryConfidence * 100).toFixed(1)}%)`}
                </div>
                <div>
                  Secundario: {point.secondaryStatus || "N/A"}
                  {point.secondaryConfidence === null ? "" : ` (${(point.secondaryConfidence * 100).toFixed(1)}%)`}
                </div>
                <div>
                  Ult. prediccion:{" "}
                  {point.healthCreatedAt
                    ? new Date(point.healthCreatedAt).toLocaleString()
                    : "SIN PREDICCION"}
                </div>
                <div>Lat: {point.lat.toFixed(6)}</div>
                <div>Lng: {point.lng.toFixed(6)}</div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
