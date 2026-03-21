"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Stethoscope, Activity, ArrowLeft } from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { BiometricCards } from "@/components/animal/BiometricCards"
import { BiometricChart } from "@/components/animal/BiometricChart"
import { DiagnosisPanel } from "@/components/animal/DiagnosisPanel"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { fetchAnimalDetail } from "@/lib/api"
import { Button } from "@/components/ui/Button"
// Keep mock generator just for filling chart if DB has no historical data yet
import { generateBiometricData } from "@/lib/mock-data"

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
        <p className="font-mono text-label-md text-tertiary">Error: Animal no encontrado en el servidor.</p>
        <Button variant="secondary" onClick={() => router.back()}>Volver al Dashboard</Button>
      </div>
    )
  }

  const { animal, chartData, healthStatus } = data
  const isCritical = animal.status === "critical"
  const biometricsStatus = isCritical ? "high" as const : "normal" as const

  const biometrics = {
    temperature: { value: animal.temperature, status: biometricsStatus },
    heartRate: { value: animal.heartRate, status: biometricsStatus },
    distance: { value: animal.distance, status: biometricsStatus },
    rumination: { value: animal.rumination, status: isCritical ? ("low" as const) : ("normal" as const) }
  }

  // If backend returned less than 2 data points, we can't draw a line very well. Use fake history if needed.
  const displayChartData = chartData.length > 1 ? chartData : generateBiometricData()

  // AI Diagnosis Logic default fallbacks if API doesn't provide nice strings
  let conditionStr = "Parámetros estables. Funciones biológicas dentro de los márgenes previstos."
  let confPercent = 94
  let recomStr = "Mantener monitoreo pasivo. No requiere intervención inmediata."

  if (isCritical) {
    conditionStr = healthStatus?.condition || "Alerta Roja. Probabilidad alta de Mastitis Clínica."
    confPercent = healthStatus?.confidence || 87
    recomStr = healthStatus?.recommendation || "Contactar veterinario. Identificar cuarto mamario afectado e iniciar protocolo de aislamiento."
  } else if (animal.status === "warning") {
    conditionStr = healthStatus?.condition || "Anomalía leve detectada. Posible estrés térmico o pre-clínico."
    confPercent = healthStatus?.confidence || 76
    recomStr = healthStatus?.recommendation || "Elevar prioridad de observación durante el ordeñe. Verificar ingesta de agua."
  }

  return (
    <div className="flex flex-col h-screen overflow-y-auto text-on-surface bg-surface">
      <PageHeader
        title={`Animal #${animal.id}`}
        description={`Última act: ${animal.lastUpdated}`}
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
            {animal.status && <StatusBadge status={animal.status as "healthy" | "warning" | "critical"} pulse={animal.status !== 'healthy'} />}
          </div>
          <Button variant="primary" className="gap-2 w-fit">
            <Stethoscope className="w-4 h-4" />
            REGISTRAR INTERVENCIÓN
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
            color={isCritical ? "var(--color-tertiary)" : "var(--color-secondary)"}
          />
        </section>

        <section className="mt-4">
          <DiagnosisPanel
            condition={conditionStr}
            confidence={confPercent}
            recommendation={recomStr}
          />
        </section>
      </div>
    </div>
  )
}
