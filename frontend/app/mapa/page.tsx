"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Activity, Clock3, MapPin } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import { getLatestHealthByHistory, getLatestReadings } from "@/lib/api";
import type { HerdMapPoint } from "@/components/dashboard/HerdGeoMapClient";

const HerdGeoMapClient = dynamic(
  () => import("@/components/dashboard/HerdGeoMapClient").then((m) => m.HerdGeoMapClient),
  { ssr: false },
);

const DEFAULT_REFRESH_SECONDS = Number(
  process.env.NEXT_PUBLIC_MAP_REFRESH_SECONDS || "10",
);

const STATUS_COLORS: Record<string, string> = {
  SANA: "#22c55e",
  SUBCLINICA: "#f59e0b",
  CLINICA: "#ef4444",
  MASTITIS: "#dc2626",
  CELO: "#3b82f6",
  FEBRIL: "#f97316",
  DIGESTIVO: "#eab308",
};

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
      const latestReadings = await getLatestReadings();

      const validReadings = latestReadings.filter((reading) => {
        const lat = toNumber(reading?.latitud);
        const lng = toNumber(reading?.longitud);
        return lat !== null && lng !== null;
      });

      const uniqueCowIds = Array.from(
        new Set(validReadings.map((reading) => Number(reading.cow_id)).filter(Boolean)),
      );

      const healthMap = new Map<
        number,
        {
          effectiveStatus: string | null;
          effectiveConfidence: number | null;
          primaryStatus: string | null;
          primaryConfidence: number | null;
          secondaryStatus: string | null;
          secondaryConfidence: number | null;
          createdAt: string | null;
        }
      >();
      const chunkSize = 8;

      for (let i = 0; i < uniqueCowIds.length; i += chunkSize) {
        const chunk = uniqueCowIds.slice(i, i + chunkSize);
        const chunkResults = await Promise.all(
          chunk.map(async (cowId) => {
            const latestHealth = await getLatestHealthByHistory(cowId);
            const primaryStatus = latestHealth?.primary_status || latestHealth?.status || null;
            const primaryConfidence =
              typeof latestHealth?.primary_confidence === "number"
                ? latestHealth.primary_confidence
                : typeof latestHealth?.confidence === "number"
                  ? latestHealth.confidence
                  : null;
            const secondaryStatus = latestHealth?.secondary_status || null;
            const secondaryConfidence =
              typeof latestHealth?.secondary_confidence === "number"
                ? latestHealth.secondary_confidence
                : null;

            let effectiveStatus = primaryStatus;
            let effectiveConfidence = primaryConfidence;
            if (
              secondaryStatus &&
              secondaryConfidence !== null &&
              (primaryConfidence === null || secondaryConfidence > primaryConfidence)
            ) {
              effectiveStatus = secondaryStatus;
              effectiveConfidence = secondaryConfidence;
            }

            return {
              cowId,
              effectiveStatus,
              effectiveConfidence,
              primaryStatus,
              primaryConfidence,
              secondaryStatus,
              secondaryConfidence,
              createdAt: latestHealth?.created_at || null,
            };
          }),
        );

        chunkResults.forEach((item) => {
          healthMap.set(item.cowId, {
            effectiveStatus: item.effectiveStatus,
            effectiveConfidence: item.effectiveConfidence,
            primaryStatus: item.primaryStatus,
            primaryConfidence: item.primaryConfidence,
            secondaryStatus: item.secondaryStatus,
            secondaryConfidence: item.secondaryConfidence,
            createdAt: item.createdAt,
          });
        });
      }

      const mappedPoints: HerdMapPoint[] = validReadings
        .map((reading) => {
          const cowId = Number(reading.cow_id);
          const lat = toNumber(reading.latitud);
          const lng = toNumber(reading.longitud);

          if (!Number.isFinite(cowId) || lat === null || lng === null) {
            return null;
          }

          const health = healthMap.get(cowId);

          return {
            cowId,
            lat,
            lng,
            timestamp: String(reading.timestamp),
            healthStatus: health?.effectiveStatus || null,
            confidence: health?.effectiveConfidence ?? null,
            healthCreatedAt: health?.createdAt ?? null,
            primaryStatus: health?.primaryStatus ?? null,
            primaryConfidence: health?.primaryConfidence ?? null,
            secondaryStatus: health?.secondaryStatus ?? null,
            secondaryConfidence: health?.secondaryConfidence ?? null,
          };
        })
        .filter((point): point is HerdMapPoint => point !== null);

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
      { key: "SUBCLINICA", color: STATUS_COLORS.SUBCLINICA },
      { key: "CLINICA", color: STATUS_COLORS.CLINICA },
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
            <Clock3 className="w-4 h-4 text-on-surface-variant" />
            <label htmlFor="refresh-seconds" className="text-label-sm text-on-surface-variant">
              Refresh (seg)
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
                ? `Ultima actualizacion: ${lastFetchTime.toLocaleTimeString()}`
                : "Sin datos aun"}
            </span>
          </div>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4 min-h-0 flex-1">
          <div className="rounded-xl border border-outline-variant/30 overflow-hidden bg-surface-container min-h-[420px]">
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
              El color de cada punto representa la ultima prediccion guardada para ese animal.
            </p>
            <div className="space-y-3">
              {statusLegend.map((item) => (
                <div key={item.key} className="flex items-center gap-3">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-body-md">{item.key}</span>
                </div>
              ))}
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-slate-400" />
                <span className="text-body-md">SIN DATOS</span>
              </div>
            </div>
          </aside>
        </section>
      </div>
    </div>
  );
}
