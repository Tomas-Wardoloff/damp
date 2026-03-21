"use client";

import Link from "next/link";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { formatApiDateTime } from "@/lib/api";

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
  SANA: "#16a34a",
  MASTITIS: "#ef4444",
  CELO: "#60a5fa",
  FEBRIL: "#f59e0b",
  DIGESTIVO: "#f97316",
};

function normalizeDisplayedStatus(status: string | null): string | null {
  if (!status) return null;
  if (status === "SUBCLINICA" || status === "CLINICA") return "MASTITIS";
  return status;
}

function getColor(status: string | null): string {
  const normalized = normalizeDisplayedStatus(status);
  if (!normalized) return "#94a3b8";
  return STATUS_COLORS[normalized] || "#94a3b8";
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

function formatStatus(status: string | null): string {
  const normalized = normalizeDisplayedStatus(status);
  if (!normalized) return "Sin datos";

  const labels: Record<string, string> = {
    SANA: "Sana",
    MASTITIS: "Mastitis",
    CELO: "Celo",
    FEBRIL: "Febril",
    DIGESTIVO: "Digestivo",
  };

  return labels[normalized] || normalized;
}

function formatPercentage(value: number | null): string {
  if (typeof value !== "number") return "sin dato";
  return `${(value * 100).toFixed(1)}%`;
}

function getConfidenceColor(value: number | null): string {
  if (typeof value !== "number") return "#334155";
  const clamped = Math.max(0, Math.min(1, value));
  const hue = clamped * 120;
  return `hsl(${hue} 78% 42%)`;
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
        const hasConfidence = typeof point.confidence === "number";
        const confidenceColor = getConfidenceColor(point.confidence);
        const certaintyText = hasConfidence
          ? `${(Number(point.confidence) * 100).toFixed(1)}%`
          : "Sin datos";
        const helpText = `Certeza (%)\nMuestra qué tan segura es la evaluación.\nSe calcula con las mediciones de las últimas 8 horas y su consistencia.\nUn valor alto indica señales claras; uno bajo, señales mezcladas.\n\nEstado primario\nEs el estado más probable según el análisis de esas mediciones.\n\nEstado secundario\nEs la segunda opción más probable y funciona como alternativa cercana.`;
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
              <div className="relative text-sm min-w-55 space-y-3">
                <span className="absolute left-0 top-0 z-10 inline-flex items-center group">
                  <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-slate-300 bg-slate-100 text-[11px] font-semibold text-slate-700 cursor-help">
                    ?
                  </span>
                  <span className="pointer-events-none absolute left-0 top-full z-9999 mt-2 w-72 rounded-md bg-slate-900 px-3 py-2 text-[11px] font-normal leading-relaxed text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 whitespace-pre-line">
                    {helpText}
                  </span>
                </span>

                <div className="flex items-center justify-between gap-2">
                  <strong className="pl-6">Vaca #{point.cowId}</strong>
                  <span
                    className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
                    style={{ backgroundColor: color }}
                  >
                    {formatStatus(point.healthStatus)}
                  </span>
                </div>

                <div className="flex w-full items-center justify-between rounded-md border border-slate-200 bg-slate-50/80 px-2 ">
                  <p className="text-sm font-extrabold text-slate-700">Certeza</p>
                  <p className="text-sm font-semibold" style={{ color: confidenceColor }}>
                    {certaintyText}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Evaluación</p>
                  <div className="flex items-center justify-between gap-2 rounded-md border border-slate-200 px-2 py-1.5">
                    <span className="text-slate-600">Estado primario</span>
                    <span className="font-semibold text-slate-900">
                      {formatStatus(point.primaryStatus)} ({formatPercentage(point.primaryConfidence)})
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2 rounded-md border border-slate-200 px-2 py-1.5">
                    <span className="text-slate-600">Estado secundario</span>
                    <span className="font-medium text-slate-800">
                      {formatStatus(point.secondaryStatus)} ({formatPercentage(point.secondaryConfidence)})
                    </span>
                  </div>
                </div>

                <div className="space-y-1 text-xs text-slate-500">
                  <div>
                    Última lectura: {formatApiDateTime(point.timestamp)}
                  </div>
                  <div>
                    Último análisis:{" "}
                    {point.healthCreatedAt
                      ? formatApiDateTime(point.healthCreatedAt)
                      : "Sin análisis"}
                  </div>
                </div>

                <div className="pt-1">
                  <Link
                    href={`/animal/${point.cowId}`}
                    className="inline-flex items-center rounded-md border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 transition-colors"
                  >
                    Ver detalle
                  </Link>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
