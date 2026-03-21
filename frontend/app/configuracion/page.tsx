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

  async function handleSave() {
    setIsSaving(true);
    setMessage("");

    const payload = {
      enabled,
      cycle_minutes: Math.max(1, Math.floor(cycleMinutes)),
    };

    const updated = await updateHealthSchedulerConfig(payload);
    if (!updated) {
      setMessage("No se pudo guardar la configuracion del scheduler.");
      setIsSaving(false);
      return;
    }

    setEnabled(Boolean(updated.enabled));
    setCycleMinutes(Number(updated.cycle_minutes) || payload.cycle_minutes);
    setLastUpdatedAt(updated.updated_at || null);

    const runtimeInfo = await getHealthSchedulerRuntime();
    setRuntime(runtimeInfo as SchedulerRuntime | null);

    setMessage("Configuracion guardada.");
    setIsSaving(false);
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden text-on-surface bg-surface">
      <PageHeader />

      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-3xl space-y-4">
          <section className="glass-panel rounded-xl border border-outline-variant/30 p-5">
            <h2 className="text-headline-md mb-2">Scheduler de Health Check</h2>
            <p className="text-body-md text-on-surface-variant">
              Define cada cuanto tiempo total queres actualizar a todas las vacas. El backend distribuye
              automaticamente las consultas para no dispararlas todas juntas.
            </p>
          </section>

          <section className="glass-panel rounded-xl border border-outline-variant/30 p-5 space-y-5">
            {isLoading ? (
              <div className="flex items-center gap-3 text-on-surface-variant">
                <Activity className="w-5 h-5 animate-spin text-primary" />
                Cargando configuracion...
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-label-sm text-on-surface-variant">Estado del cron</p>
                    <p className="text-body-md">Activar/pausar ejecucion automatica</p>
                  </div>
                  <label className="inline-flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(event) => setEnabled(event.target.checked)}
                      className="h-5 w-5"
                    />
                    <span className="text-body-md font-semibold">{enabled ? "ACTIVO" : "PAUSADO"}</span>
                  </label>
                </div>

                <div>
                  <label htmlFor="cycle-minutes" className="text-label-sm text-on-surface-variant">
                    Ventana total de actualizacion (minutos)
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
                      Ejemplo: 60 min = repartir updates de todas las vacas dentro de 1 hora.
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
                  {isSaving ? "Guardando..." : "Guardar configuracion"}
                </button>

                <div className="pt-3 border-t border-outline-variant/30 space-y-2 text-body-md text-on-surface-variant">
                  <p>
                    Ultima configuracion: {lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleString() : "N/A"}
                  </p>
                  <p>
                    Scheduler corriendo: {runtime?.running ? "SI" : "NO"}
                  </p>
                  <p>
                    Proximo espaciado estimado por vaca: {perCowHint}
                  </p>
                  <p>
                    Ultima ejecucion del cron: {runtime?.last_execution_at ? new Date(runtime.last_execution_at).toLocaleString() : "N/A"}
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
