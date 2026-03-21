"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Clock3, Save } from "lucide-react";

import { PageHeader } from "@/components/layout/PageHeader";
import {
  getHealthSchedulerConfig,
  getHealthSchedulerRuntime,
  updateHealthSchedulerConfig,
} from "@/lib/api";

type SchedulerRuntime = {
  running: boolean;
  last_execution_at: string | null;
  current_per_cow_seconds: number | null;
};

export default function ConfiguracionPage() {
  const [enabled, setEnabled] = useState(true);
  const [cycleMinutes, setCycleMinutes] = useState(60);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<SchedulerRuntime | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string>("");

  const loadConfig = useCallback(async () => {
    try {
      const [config, runtimeInfo] = await Promise.all([
        getHealthSchedulerConfig(),
        getHealthSchedulerRuntime(),
      ]);

      if (config) {
        setEnabled(Boolean(config.enabled));
        setCycleMinutes(Number(config.cycle_minutes) || 60);
        setLastUpdatedAt(config.updated_at || null);
      }
      setRuntime(runtimeInfo as SchedulerRuntime | null);
    } catch (error) {
      console.error("Error loading scheduler config:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const perCowHint = useMemo(() => {
    if (!runtime?.current_per_cow_seconds) return "-";
    const seconds = Number(runtime.current_per_cow_seconds);
    if (!Number.isFinite(seconds)) return "-";
    const minutes = Math.floor(seconds / 60);
    const remSeconds = seconds % 60;
    return `${minutes}m ${remSeconds}s`;
  }, [runtime]);

  const runningLabel = runtime?.running ? "Sí" : "No";
  const cycleSummary =
    cycleMinutes === 1
      ? "El sistema renovará los datos cada 1 minuto."
      : `El sistema renovará los datos cada ${cycleMinutes} minutos.`;

  async function handleSave() {
    setIsSaving(true);
    setMessage("");

    const payload = {
      enabled,
      cycle_minutes: Math.max(1, Math.floor(cycleMinutes)),
    };

    const updated = await updateHealthSchedulerConfig(payload);
    if (!updated) {
      setMessage("No se pudo guardar la configuración de actualización automática.");
      setIsSaving(false);
      return;
    }

    setEnabled(Boolean(updated.enabled));
    setCycleMinutes(Number(updated.cycle_minutes) || payload.cycle_minutes);
    setLastUpdatedAt(updated.updated_at || null);

    const runtimeInfo = await getHealthSchedulerRuntime();
    setRuntime(runtimeInfo as SchedulerRuntime | null);

    setMessage("Configuración guardada correctamente.");
    setIsSaving(false);
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden text-on-surface bg-surface">
      <PageHeader />

      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-3xl space-y-4">
          <section className="glass-panel rounded-xl border border-outline-variant/30 p-5">
            <h2 className="text-headline-md mb-2">Configuración de actualización automática</h2>
            <p className="text-body-md text-on-surface-variant">
              Elegí cada cuánto tiempo querés que se actualice el estado de salud de tus vacas.
              El sistema se encarga solo de revisar y refrescar la información.
            </p>
          </section>

          <section className="glass-panel rounded-xl border border-outline-variant/30 p-5 space-y-5">
            {isLoading ? (
              <div className="flex items-center gap-3 text-on-surface-variant">
                <Activity className="w-5 h-5 animate-spin text-primary" />
                Cargando configuración...
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-label-sm text-on-surface-variant">Actualización automática</p>
                    <p className="text-body-md">Activar o pausar ejecución automática</p>
                  </div>
                  <label className="inline-flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(event) => setEnabled(event.target.checked)}
                      className="h-5 w-5"
                    />
                    <span className="text-body-md font-semibold">{enabled ? "Activo" : "Pausado"}</span>
                  </label>
                </div>

                <div>
                  <label htmlFor="cycle-minutes" className="text-label-sm text-on-surface-variant">
                    Cada cuánto actualizar (minutos)
                  </label>
                  <div className="mt-2 flex items-center gap-3">
                    <Clock3 className="w-4 h-4 text-on-surface-variant" />
                    <input
                      id="cycle-minutes"
                      type="number"
                      min={1}
                      max={10080}
                      step={1}
                      value={cycleMinutes}
                      onChange={(event) => {
                        const value = Number(event.target.value);
                        if (Number.isFinite(value) && value > 0) {
                          setCycleMinutes(value);
                        }
                      }}
                      className="w-32 rounded-md border border-outline-variant/40 bg-surface-container px-3 py-2 text-body-md"
                    />
                    <span className="text-body-md text-on-surface-variant">
                      {cycleSummary}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="btn-primary gap-2 disabled:opacity-70"
                >
                  <Save className="w-4 h-4" />
                  {isSaving ? "Guardando..." : "Guardar configuración"}
                </button>

                <div className="pt-3 border-t border-outline-variant/30 space-y-2 text-body-md text-on-surface-variant">
                  <p>
                    Última configuración: {lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleString() : "Sin datos"}
                  </p>
                  <p>
                    Actualización automática activa: {runningLabel}
                  </p>
                  <p>
                    Tiempo estimado por vaca: {perCowHint}
                  </p>
                  <p>
                    Última actualización: {runtime?.last_execution_at ? new Date(runtime.last_execution_at).toLocaleString() : "Sin datos"}
                  </p>
                  {message ? <p className="text-primary font-semibold">{message}</p> : null}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
