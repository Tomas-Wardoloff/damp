"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/layout/PageHeader";
import { getClinicalHistory, parseApiDateMs } from "@/lib/api";

type ClinicalPoint = {
  created_at: string;
  status: string;
  confidence: number | null;
};

type CowHistory = {
  cow_id: number;
  total_points: number;
  transitions: number;
  stable: boolean;
  latest_status: string;
  points: ClinicalPoint[];
};

type ClinicalHistoryResponse = {
  days: number;
  from_date: string;
  to_date: string;
  page: number;
  size: number;
  total_cows: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  cow_code: string | null;
  cows: CowHistory[];
};

const STATUS_TO_LEVEL: Record<string, number> = {
  SANA: 0,
  DIGESTIVO: 1,
  FEBRIL: 2,
  CELO: 3,
  MASTITIS: 4,
};

const LEVEL_TO_STATUS: Record<number, string> = {
  0: "SANA",
  1: "DIGESTIVO",
  2: "FEBRIL",
  3: "CELO",
  4: "MASTITIS",
};

function normalizeStatus(status: string | null | undefined): string {
  if (!status) return "SANA";
  return String(status).toUpperCase();
}

function formatStatus(status: string): string {
  const labels: Record<string, string> = {
    SANA: "Sana",
    MASTITIS: "Mastitis",
    CELO: "Celo",
    FEBRIL: "Febril",
    DIGESTIVO: "Digestivo",
  };
  return labels[status] || status;
}

function statusColor(status: string): string {
  const palette: Record<string, string> = {
    SANA: "#16a34a",
    MASTITIS: "#dc2626",
    CELO: "#ec4899",
    FEBRIL: "#eab308",
    DIGESTIVO: "#f97316",
  };
  return palette[status] || "#94a3b8";
}

export default function HistorialClinicoPage() {
  const PAGE_SIZE = 3;
  const [days, setDays] = useState(7);
  const [page, setPage] = useState(1);
  const [cowCodeInput, setCowCodeInput] = useState("");
  const [cowCode, setCowCode] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [data, setData] = useState<ClinicalHistoryResponse | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);
      const response = await getClinicalHistory({
        days,
        page,
        size: PAGE_SIZE,
        cowCode,
      });
      if (isMounted) {
        if (response && response.total_pages > 0 && page > response.total_pages) {
          setPage(response.total_pages);
          return;
        }
        setData(response as ClinicalHistoryResponse | null);
        setIsLoading(false);
      }
    }

    load();
    return () => {
      isMounted = false;
    };
  }, [days, page, cowCode]);

  const cows = useMemo(() => {
    if (!data?.cows) return [];
    return [...data.cows].sort((a, b) => a.cow_id - b.cow_id);
  }, [data]);

  return (
    <div className="flex flex-col h-screen overflow-hidden text-on-surface bg-surface">
      <PageHeader />

      <div className="flex-1 p-6 overflow-y-auto space-y-5">
        <section className="glass-panel rounded-xl border border-outline-variant/30 p-4 flex flex-wrap items-center gap-3 justify-between">
          <div>
            <p className="text-body-md font-semibold">Rango de análisis</p>
            <p className="text-label-sm text-on-surface-variant">
              Elegí cuántos días hacia atrás querés ver (1 a 30 días).
            </p>
          </div>

          <div className="flex items-center gap-2">
            {[1, 7, 30].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setDays(value);
                  setPage(1);
                }}
                className={
                  value === days
                    ? "rounded-md border border-primary bg-primary/20 px-3 py-1.5 text-sm font-semibold text-primary"
                    : "rounded-md border border-outline-variant/30 bg-surface-container px-3 py-1.5 text-sm text-on-surface-variant"
                }
              >
                {value} día{value === 1 ? "" : "s"}
              </button>
            ))}
          </div>
        </section>

        <section className="glass-panel rounded-xl border border-outline-variant/30 p-4 flex flex-wrap items-end gap-3 justify-between">
          <div>
            <p className="text-body-md font-semibold">Filtro por código</p>
            <p className="text-label-sm text-on-surface-variant">
              Buscá una vaca por código (ej: 7, 007, Vaca #7).
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={cowCodeInput}
              onChange={(event) => setCowCodeInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  setCowCode(cowCodeInput.trim());
                  setPage(1);
                }
              }}
              placeholder="Código de vaca"
              className="w-48 rounded-md border border-outline-variant/40 bg-surface-container px-3 py-2 text-sm text-on-surface"
            />
            <button
              type="button"
              onClick={() => {
                setCowCode(cowCodeInput.trim());
                setPage(1);
              }}
              className="rounded-md border border-primary bg-primary/20 px-3 py-2 text-sm font-semibold text-primary"
            >
              Filtrar
            </button>
            <button
              type="button"
              onClick={() => {
                setCowCodeInput("");
                setCowCode("");
                setPage(1);
              }}
              className="rounded-md border border-outline-variant/30 bg-surface-container px-3 py-2 text-sm text-on-surface-variant"
            >
              Limpiar
            </button>
          </div>
        </section>

        {isLoading ? (
          <div className="rounded-xl border border-outline-variant/30 p-8 text-center text-on-surface-variant">
            Cargando historial clínico...
          </div>
        ) : cows.length === 0 ? (
          <div className="rounded-xl border border-outline-variant/30 p-8 text-center text-on-surface-variant">
            No hay vacas con historial clínico para los filtros seleccionados.
          </div>
        ) : (
          <section className="space-y-4">
            {cows.map((cow) => {
              const chartData = cow.points.map((point) => {
                const normalized = normalizeStatus(point.status);
                const parsedMs = parseApiDateMs(point.created_at);
                return {
                  x: parsedMs === null
                    ? "N/A"
                    : new Date(parsedMs).toLocaleString([], {
                      month: "2-digit",
                      day: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    }),
                  y: STATUS_TO_LEVEL[normalized] ?? 0,
                  status: normalized,
                  confidence: point.confidence,
                };
              });

              const latestStatus = normalizeStatus(cow.latest_status);
              const latestColor = statusColor(latestStatus);

              return (
                <article
                  key={cow.cow_id}
                  className="rounded-xl border border-outline-variant/30 bg-surface-container p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div>
                      <h3 className="text-body-lg font-semibold">Vaca #{cow.cow_id}</h3>
                      <p className="text-label-sm text-on-surface-variant">
                        {cow.total_points} registros, {cow.transitions} cambios de estado
                      </p>
                    </div>

                    <div className="flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold"
                      style={{ backgroundColor: `${latestColor}22`, color: latestColor }}>
                      Estado actual: {formatStatus(latestStatus)}
                    </div>
                  </div>

                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 8, right: 20, left: 0, bottom: 0 }}>
                        <CartesianGrid stroke="rgba(148,163,184,0.2)" strokeDasharray="4 4" />
                        <XAxis dataKey="x" tick={{ fill: "#94a3b8", fontSize: 11 }} minTickGap={24} />
                        <YAxis
                          type="number"
                          domain={[0, 4]}
                          ticks={[0, 1, 2, 3, 4]}
                          tickFormatter={(value) => formatStatus(LEVEL_TO_STATUS[value] || "SANA")}
                          tick={{ fill: "#94a3b8", fontSize: 11 }}
                        />
                        <Tooltip
                          contentStyle={{
                            background: "#0f172a",
                            border: "1px solid rgba(148,163,184,0.3)",
                            borderRadius: 8,
                            color: "#e2e8f0",
                          }}
                          formatter={(value, _, item) => {
                            const status = item?.payload?.status || "SANA";
                            const confidence = item?.payload?.confidence;
                            const confText = typeof confidence === "number"
                              ? ` | certeza ${(confidence * 100).toFixed(1)}%`
                              : "";
                            return [`${formatStatus(status)}${confText}`, "Estado"];
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="y"
                          stroke={latestColor}
                          strokeWidth={2.5}
                          dot={{ r: 3 }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <p className="mt-2 text-label-sm text-on-surface-variant">
                    {cow.stable
                      ? "Se mantuvo estable durante el período seleccionado."
                      : "Mostró cambios de estado durante el período seleccionado."}
                  </p>
                </article>
              );
            })}

            <div className="glass-panel rounded-xl border border-outline-variant/30 p-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-label-sm text-on-surface-variant">
                Página {data?.page ?? page} de {data?.total_pages ?? 0} | {data?.total_cows ?? 0} vacas
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  disabled={!data?.has_prev}
                  className="rounded-md border border-outline-variant/30 bg-surface-container px-3 py-1.5 text-sm text-on-surface-variant disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Anterior
                </button>
                <button
                  type="button"
                  onClick={() => setPage((prev) => prev + 1)}
                  disabled={!data?.has_next}
                  className="rounded-md border border-outline-variant/30 bg-surface-container px-3 py-1.5 text-sm text-on-surface-variant disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Siguiente
                </button>
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
