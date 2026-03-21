"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { IterationCcwIcon, Activity, ArrowLeft } from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { BiometricCards } from "@/components/animal/BiometricCards"
import { BiometricChart } from "@/components/animal/BiometricChart"
import { DiagnosisPanel } from "@/components/animal/DiagnosisPanel"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { fetchAnimalDetail } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { CowStatus } from "@/types"

export default function AnimalDetail() {
  const router = useRouter()
  const params = useParams()
  const id = params.id as string

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [data, setData] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function loadAnimal() {
      setIsLoading(true)
      try {
        const result = await fetchAnimalDetail(id)
        if (result) {
          setData(result)
        }
      } catch (err) {
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }
    loadAnimal()
  }, [id])

  if (isLoading) {
    return (
      <div className="flex flex-col h-screen text-on-surface bg-surface items-center justify-center gap-4">
        <Activity className="w-8 h-8 animate-spin text-primary" />
        <p className="font-mono text-label-md">Sincronizando biometría...</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col h-screen text-on-surface bg-surface items-center justify-center gap-4">
        <p className="font-mono text-label-md text-tertiary">Error: Animal no encontrado.</p>
        <Button variant="secondary" onClick={() => router.back()}>Volver al Dashboard</Button>
      </div>
    )
  }

  const { animal, chartData, healthStatus, prediction } = data

  function formatTimeInSystem(dateString: string) {
    if (!dateString) return "Desconocido";
    const start = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - start.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays < 30) return `${diffDays} días`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths < 12) return `${diffMonths} meses`;
    return `${Math.floor(diffMonths / 12)} años`;
  }
  function getStressLevel(rmssd: number, sdnn: number) {
    if (rmssd < 20 || sdnn < 30) return { value: "Elevado", status: "high" as const };
    if (rmssd < 40 || sdnn < 50) return { value: "Moderado", status: "warning" as const };
    return { value: "Normal", status: "normal" as const };
  }

  const isCritical = animal.status === "critical"
  const biometricsStatus = isCritical ? ("critical" as const) : animal.status === "warning" ? ("warning" as const) : ("normal" as const)

  const biometrics = {
    temperature: {
      value: typeof animal.temperature === 'number' ? animal.temperature.toFixed(1) : animal.temperature,
      status: (animal.temperature >= 38.0 && animal.temperature <= 39.2) ? "normal" as const : "high" as const
    },
    heartRate: {
      value: animal.heartRate,
      status: (animal.heartRate >= 48 && animal.heartRate <= 84) ? "normal" as const : "high" as const
    },
    distance: {
      value: animal.distance,
      status: "normal" as const
    },
    stress: getStressLevel(animal.rmssd || 0, animal.sdnn || 0),
    rumination: {
      value: animal.rumination ? "Con rumia" : "Sin rumia",
      status: animal.rumination ? "normal" as const : "high" as const
    },
    vocalization: {
      value: animal.vocalization ? "Detectada" : "No detectada",
      status: animal.vocalization ? "high" as const : "normal" as const
    }
  }

  // If backend returned less than 2 data points, we can't draw a line very well. Use fake history if needed.
  const displayChartData = chartData.length > 0 ? chartData : []

  // AI Diagnosis Logic with new model payload format (primary + secondary)
  const primaryLabel = prediction?.primary?.status || healthStatus?.primary_status || "SANA"
  const primaryConf = prediction?.primary?.confidence ?? healthStatus?.primary_confidence ?? healthStatus?.confidence ?? 0
  const secondaryLabel = prediction?.secondary?.status || healthStatus?.secondary_status || null
  const secondaryConf = prediction?.secondary?.confidence ?? healthStatus?.secondary_confidence ?? null

  let effectiveLabel = primaryLabel
  let effectiveConf = primaryConf
  if (secondaryLabel && secondaryConf !== null && secondaryConf > effectiveConf) {
    effectiveLabel = secondaryLabel
    effectiveConf = secondaryConf
  }

  const labelLower = String(effectiveLabel).toLowerCase()

  let conditionStr = `Predicción principal: ${effectiveLabel}`
  if (secondaryLabel) {
    conditionStr += ` | secundaria: ${secondaryLabel}`
  }

  const confPercent = Math.round((effectiveConf || 0) * 100)
  let recomStr = "Mantener monitoreo y seguir el protocolo de rutina."

  if (labelLower.includes("mastitis") || labelLower.includes("clinica")) {
    recomStr = "Prioridad alta: revisión veterinaria y chequeo de ubre inmediato."
  } else if (labelLower.includes("subclinica") || labelLower.includes("febril") || labelLower.includes("digestivo")) {
    recomStr = "Monitoreo intensivo: repetir control y confirmar evolución en próximas horas."
  } else if (labelLower.includes("celo")) {
    recomStr = "Evento reproductivo detectado: confirmar con observación de conducta."
  }

  return (
    <div className="flex flex-col h-screen overflow-y-auto text-on-surface bg-surface">
      <PageHeader
        title={`Vaca #${animal.id} - ${animal.breed}`}
        description={`Registrada hace: ${formatTimeInSystem(animal.registrationDate)} | Ultima Act: ${animal.lastUpdated}`}
      />

      <div className="p-6 max-w-7xl mx-auto w-full flex flex-col gap-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          className="w-fit -ml-2 text-on-surface-variant hover:text-on-surface"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver al Dashboard
        </Button>

        <div className="flex items-center justify-between bg-surface-container-low p-4 rounded-lg border border-outline-variant/50">
          <div className="flex items-center gap-3">
            <span className="text-body-md font-medium text-on-surface-variant">Estado actual:</span>
            <StatusBadge status={animal.status} pulse={animal.status !== 'sana'} />
          </div>
          <Button variant="primary" className="gap-2 w-fit">
            <IterationCcwIcon className="w-4 h-4" />
            Realizar Analisis
          </Button>
        </div>
        <section>
          <BiometricCards biometrics={biometrics} />
        </section>

        <section className="mt-2">
          <BiometricChart
            data={displayChartData}
            metricName="Temperatura Corporal"
            normalRange={[38.0, 39.2]}
          />
        </section>

        <section className="mt-4">
          {!healthStatus ? (
            <div className="bg-surface-container-low p-6 rounded-lg border border-dashed border-outline-variant/40 flex flex-col items-center justify-center gap-1 text-center py-12">
              <span className="text-on-surface-variant font-mono text-label-md uppercase tracking-widest">
                Datos Insuficientes
              </span>
              <p className="text-on-surface-variant text-body-sm max-w-md mt-1 opacity-70">
                El modelo predictivo de IA requiere un mínimo de 5 lecturas recientes para procesar y emitir un diagnóstico confiable.
              </p>
            </div>
          ) : (
            <DiagnosisPanel
              status={healthStatus.status as CowStatus}
              confidence={healthStatus.confidence}
            />
          )}
        </section>
      </div>
    </div>
  )
}