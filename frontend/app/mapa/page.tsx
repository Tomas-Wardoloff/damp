"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Activity, Clock3, MapPin } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { fetchDashboardData, parseApiDateMs } from "@/lib/api";
import type { HerdMapPoint } from "@/components/dashboard/HerdGeoMapClient";

const HerdGeoMapClient = dynamic(
  () => import("@/components/dashboard/HerdGeoMapClient").then((m) => m.HerdGeoMapClient),
  { ssr: false },
);

const DEFAULT_REFRESH_SECONDS = Number(
  process.env.NEXT_PUBLIC_MAP_REFRESH_SECONDS || "10",
);

const STATUS_COLORS: Record<string, string> = {
  SANA: "#16a34a",
  MASTITIS: "#dc2626",
  CELO: "#ec4899",
  FEBRIL: "#eab308",
  DIGESTIVO: "#f97316",
};

const STATUS_BRIEF: Record<string, string[]> = {
  SANA: [
    "todo en rango normal",
  ],
  MASTITIS: [
    "temperatura alta",
    "movimiento bajo",
    "variabilidad cardíaca baja",
  ],
  CELO: [
    "movimiento muy alto",
    "actividad nocturna marcada",
    "temperatura cercana a normal",
  ],
  FEBRIL: [
    "temperatura alta",
    "movimiento casi normal",
  ],
  DIGESTIVO: [
    "rumia muy baja",
    "movimiento bajo",
    "temperatura moderada",
  ],
};

function normalizeDisplayedStatus(status: string | null): string | null {
  if (!status) return null;
  if (status === "SUBCLINICA" || status === "CLINICA") return "MASTITIS";
  return status;
}

function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    SANA: "SANA",
    MASTITIS: "MASTITIS",
    CELO: "CELO",
    FEBRIL: "FEBRIL",
    DIGESTIVO: "DIGESTIVO",
  };
  return labels[status] || status;
}

function toNumber(value: unknown): number | null {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export default function MapaRodeoPage() {
  const [points, setPoints] = useState<HerdMapPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null);
  const [refreshSeconds, setRefreshSeconds] = useState(DEFAULT_REFRESH_SECONDS);

  const loadMapData = useCallback(async () => {
    try {
      const data = await fetchDashboardData();
      const animals = data.animals;

      const nowMs = Date.now();

      const mappedPoints: HerdMapPoint[] = animals
        .filter((a: any) => {
          const lat = toNumber(a.latitud);
          const lng = toNumber(a.longitud);
          // Note: fetchDashboardData already formats lastUpdated, but for the map we might want raw TS comparison if possible.
          // However, for this MVP, if it's in the summary, it's the latest.
          return lat !== null && lng !== null;
        })
        .map((a: any) => {
          const status = a.status?.toUpperCase() || "SANA";
          const normalizedStatus = normalizeDisplayedStatus(status);

          return {
            cowId: Number(a.id),
            lat: Number(a.latitud),
            lng: Number(a.longitud),
            timestamp: a.lastUpdated,
            healthStatus: normalizedStatus,
            confidence: null, // Summary currently doesn't provide confidence
            healthCreatedAt: a.lastUpdated,
            primaryStatus: status,
            primaryConfidence: null,
            secondaryStatus: null,
            secondaryConfidence: null,
          };
        });

      setPoints(mappedPoints);
      setLastFetchTime(new Date());
    } catch (error) {
      console.error("Error loading herd map data:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    loadMapData();
  }, [loadMapData]);

  useEffect(() => {
    const safeRefresh = Number.isFinite(refreshSeconds) && refreshSeconds > 0
      ? refreshSeconds
      : DEFAULT_REFRESH_SECONDS;
    const intervalId = setInterval(() => {
      loadMapData();
    }, safeRefresh * 1000);

    return () => clearInterval(intervalId);
  }, [loadMapData, refreshSeconds]);

  const statusLegend = useMemo(
    () => [
      { key: "SANA", color: STATUS_COLORS.SANA },
      { key: "MASTITIS", color: STATUS_COLORS.MASTITIS },
      { key: "CELO", color: STATUS_COLORS.CELO },
      { key: "FEBRIL", color: STATUS_COLORS.FEBRIL },
      { key: "DIGESTIVO", color: STATUS_COLORS.DIGESTIVO },
    ],
    [],
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden text-on-surface bg-surface">
      <PageHeader />

      <div className="flex-1 p-6 flex flex-col gap-4 overflow-hidden">
        <section className="glass-panel rounded-xl border border-outline-variant/30 p-4 flex flex-wrap gap-4 items-center justify-between">
          <div className="flex items-center gap-3">
            <MapPin className="w-5 h-5 text-primary" />
            <div>
              <p className="text-label-sm text-on-surface-variant">Animales en mapa</p>
              <p className="text-body-md font-semibold">{points.length} posiciones activas</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="relative inline-flex items-center group">
              <Clock3 className="w-4 h-4 text-on-surface-variant" />
              <span className="pointer-events-none absolute bottom-full left-1/2 z-9999 mb-2 w-72 -translate-x-1/2 rounded-md bg-slate-900 px-3 py-2 text-[11px] font-normal leading-relaxed text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100">
                Este valor define cada cuántos segundos se recarga el mapa y se consulta la última lectura disponible de cada vaca.
              </span>
            </span>
            <label htmlFor="refresh-seconds" className="text-label-sm text-on-surface-variant">
              Actualización (seg)
            </label>
            <input
              id="refresh-seconds"
              type="number"
              min={3}
              max={300}
              step={1}
              value={refreshSeconds}
              onChange={(event) => {
                const nextValue = Number(event.target.value);
                if (Number.isFinite(nextValue) && nextValue > 0) {
                  setRefreshSeconds(nextValue);
                }
              }}
              className="w-24 rounded-md border border-outline-variant/40 bg-surface-container px-3 py-2 text-body-md"
            />
            <span className="text-label-sm text-on-surface-variant">
              {lastFetchTime
                ? `Última actualización: ${lastFetchTime.toLocaleTimeString()}`
                : "Sin datos aún"}
            </span>
          </div>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4 min-h-0 flex-1">
          <div className="rounded-xl border border-outline-variant/30 overflow-hidden bg-surface-container min-h-105">
            {isLoading ? (
              <div className="h-full flex items-center justify-center gap-3 text-on-surface-variant">
                <Activity className="w-6 h-6 animate-spin text-primary" />
                <span className="text-label-md">Cargando mapa...</span>
              </div>
            ) : points.length === 0 ? (
              <div className="h-full flex items-center justify-center text-on-surface-variant text-label-md">
                No hay lecturas con latitud/longitud disponibles.
              </div>
            ) : (
              <HerdGeoMapClient points={points} />
            )}
          </div>

          <aside className="glass-panel rounded-xl border border-outline-variant/30 p-4 overflow-y-auto">
            <h3 className="text-headline-md mb-4">Leyenda de estados</h3>
            <p className="text-body-md text-on-surface-variant mb-3">
              El color de cada punto representa el último análisis guardado para ese animal.
            </p>
            <ul className="space-y-2">
              {statusLegend.map((item) => (
                <li key={item.key} className="list-none">
                  <details className="rounded-md border border-outline-variant/30 bg-surface-container p-2">
                    <summary className="flex items-center gap-3 cursor-pointer list-none">
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-body-md font-medium">{formatStatusLabel(item.key)}</span>
                    </summary>
                    <ul className="mt-2 pl-4 list-disc space-y-1 text-label-sm text-on-surface-variant">
                      {STATUS_BRIEF[item.key].map((detail) => (
                        <li key={`${item.key}-${detail}`}>{detail}</li>
                      ))}
                    </ul>
                  </details>
                </li>
              ))}
              <li className="list-none flex items-center gap-3 px-2 py-1">
                <span className="w-3 h-3 rounded-full bg-slate-400" />
                <span className="text-body-md">sin datos</span>
              </li>
            </ul>
          </aside>
        </section>
      </div>
    </div>
  );
}
