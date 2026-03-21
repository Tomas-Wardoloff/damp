"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { IterationCcwIcon, Activity, ArrowLeft, Calendar, Tag, Clock } from "lucide-react"
import { PageHeader } from "@/components/layout/PageHeader"
import { BiometricCards } from "@/components/animal/BiometricCards"
import { BiometricChart } from "@/components/animal/BiometricChart"
import { DiagnosisPanel } from "@/components/animal/DiagnosisPanel"
import { StatusBadge } from "@/components/ui/StatusBadge"
import { fetchAnimalDetail } from "@/lib/api"
import { Button } from "@/components/ui/Button"
import { CowStatus } from "@/types"
import CowHealthViewer, { SingleCowViewer, mapBackendStatusTo3D } from "@/lib/CowHealthViewer"



function formatTimeInSystem(dateStr: string) {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMonths = (now.getFullYear() - date.getFullYear()) * 12 + (now.getMonth() - date.getMonth());
  if (diffMonths === 0) return "Menos de 1 mes";
  if (diffMonths === 1) return "1 mes";
  return `${diffMonths} meses`;
}

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

  const { animal, chartData, healthStatus, healthHistory, prediction } = data

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
    rmssd: {
      value: animal.rmssd ?? 0,
      status: "normal" as const
    },
    sdnn: {
      value: animal.sdnn ?? 0,
      status: "normal" as const
    },
    location: {
      value: `${animal.latitude ?? "N/A"}, ${animal.longitude ?? "N/A"}`,
      status: "normal" as const
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
  let altLabel = secondaryLabel
  let altConf = secondaryConf
  if (secondaryLabel && secondaryConf !== null && secondaryConf > effectiveConf) {
    effectiveLabel = secondaryLabel
    effectiveConf = secondaryConf
    altLabel = primaryLabel
    altConf = primaryConf
  }

  const isSick = animal.status?.toLowerCase() !== "sana" && animal.status?.toLowerCase() !== "sin datos";

  let trendMsg = null;
  if (isSick && effectiveConf < 0.8 && healthHistory && healthHistory.length > 0) {
    const sortedHistory = [...healthHistory].sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    // skip the first if it matches current timestamp, just look at past 
    const pastRecords = sortedHistory.slice(1);
    const recentRecords = pastRecords.slice(0, 5); // look at the last 5 previous readings
    
    const hadStateRecently = recentRecords.some(r => r.status.toLowerCase() === effectiveLabel.toLowerCase());
    
    const prevRecord = pastRecords.length > 0 ? pastRecords[0] : null;
    let prevConf = 0;
    if (prevRecord && prevRecord.status.toLowerCase() === effectiveLabel.toLowerCase()) {
      prevConf = prevRecord.confidence || 0;
    }

    if (hadStateRecently) {
      if (effectiveConf > prevConf) {
        trendMsg = `Hay registros previos de ${effectiveLabel}, posiblemente agravándose o recayendo.`;
      } else {
        trendMsg = `Posiblemente abandonando o recuperándose del cuadro de ${effectiveLabel}.`;
      }
    } else {
      trendMsg = `No hay registros recientes, posiblemente entrando en nuevo cuadro de ${effectiveLabel}.`;
    }
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

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-2">
          <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/50 flex items-center gap-4">
            <div className="p-2 rounded-md bg-primary-container/20 text-primary">
              <Tag className="w-5 h-5" />
            </div>
            <div>
              <p className="text-label-sm text-on-surface-variant uppercase tracking-wider">Raza</p>
              <p className="text-body-md font-medium text-on-surface">{animal.breed}</p>
            </div>
          </div>
          <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/50 flex items-center gap-4">
            <div className="p-2 rounded-md bg-primary-container/20 text-primary">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <p className="text-label-sm text-on-surface-variant uppercase tracking-wider">Ingresada</p>
              <p className="text-body-md font-medium text-on-surface">
                {new Date(animal.registrationDate).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/50 flex items-center gap-4">
            <div className="p-2 rounded-md bg-primary-container/20 text-primary">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <p className="text-label-sm text-on-surface-variant uppercase tracking-wider">Edad</p>
              <p className="text-body-md font-medium text-on-surface">{animal.ageMonths} meses</p>
            </div>
          </div>
        </div>

        <div className={`flex flex-col md:flex-row md:items-center justify-between p-5 rounded-xl border transition-colors gap-4 ${
          isSick 
            ? "bg-tertiary/10 border-tertiary/40 shadow-lg shadow-tertiary/10" 
            : "bg-surface-container-low border-outline-variant/50"
        }`}>
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-4">
              <span className={`font-bold ${
                isSick ? "text-xl text-tertiary" : "text-body-md text-on-surface-variant"
              }`}>
                Estado actual:
              </span>
              <StatusBadge 
                status={animal.status} 
                className={isSick ? "px-4 py-2 text-base scale-110 origin-left border-tertiary/60" : ""} 
                pulse={isSick}
              />
            </div>

            {isSick && (
              <div className="flex flex-col gap-1.5 mt-1 border-l-2 border-tertiary/50 pl-3">
                <p className="text-body-md text-on-surface flex items-center gap-2">
                  <span className="font-semibold">Certeza del modelo:</span> {(effectiveConf * 100).toFixed(1)}%
                  {effectiveConf >= 0.8 ? (
                    <span className="text-tertiary text-[10px] font-bold uppercase tracking-wider bg-tertiary/20 px-2 py-0.5 rounded-sm">
                      Seguro - Requiere Acción
                    </span>
                  ) : null}
                </p>
                
                {altLabel && altConf !== null && altLabel.toLowerCase() !== "sana" && (
                  <p className="text-label-sm text-on-surface-variant flex items-center gap-1.5 mt-0.5">
                    <span className="font-semibold">Evaluación alternativa:</span> 
                    El modelo considera posible {altLabel} ({(altConf * 100).toFixed(1)}%)
                  </p>
                )}

                {trendMsg && (
                  <p className="text-label-md text-on-surface-variant flex items-center gap-1.5 mt-1">
                    <Activity className="w-4 h-4 text-tertiary" />
                    <span className="font-medium text-tertiary">Análisis de evolución:</span> {trendMsg}
                  </p>
                )}
              </div>
            )}
          </div>
          
          <div className="flex flex-col items-end gap-3 min-w-fit">
            <p className="text-label-sm text-on-surface-variant max-w-[150px] text-right">
              Aviso: Datos basados en los últimos 5 minutos.
            </p>
            <div className="flex items-center gap-3">
              <Button variant="primary" className="gap-2 w-fit">
                <IterationCcwIcon className="w-4 h-4" />
                Actualizar
              </Button>
              {isSick && (
                <Button 
                  variant="secondary" 
                  className="gap-2 w-fit bg-surface border-tertiary/30 hover:bg-tertiary/10 text-tertiary" 
                  onClick={() => {
                    document.getElementById('diagnosis-panel')?.scrollIntoView({ behavior: 'smooth' });
                  }}
                >
                  Ver más detalles
                </Button>
              )}
            </div>
          </div>
        </div>
        <section>
          <BiometricCards biometrics={biometrics} />
        </section>
        <div>
          <SingleCowViewer status={mapBackendStatusTo3D(prediction?.status)} />
        </div>
        <section className="mt-2">
          <BiometricChart
            data={displayChartData}
            metricName="Temperatura Corporal"
            normalRange={[38.0, 39.2]}
          />
        </section>
        <section id="diagnosis-panel" className="mt-4 scroll-mt-6">
          <DiagnosisPanel
            status={effectiveLabel as CowStatus}
            confidence={effectiveConf}
          />
        </section>
      </div>
    </div>
  )
}