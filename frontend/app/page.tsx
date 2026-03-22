"use client"

import { useState, useEffect } from "react"
import { SummaryMetrics } from "@/components/dashboard/SummaryMetrics"
import { HerdMap } from "@/components/dashboard/HerdMap"
import { useRouter } from "next/navigation"
import { PageHeader } from "@/components/layout/PageHeader"
import { fetchDashboardDataPaged } from "@/lib/api"
import { type Animal } from "@/components/animal/AnimalCard"
import { Activity } from "lucide-react"

export default function Dashboard() {
  const PAGE_SIZE = 25
  const router = useRouter()

  const [animals, setAnimals] = useState<Animal[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [totalAnimals, setTotalAnimals] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)
  const [summary, setSummary] = useState<Record<string, number>>({})

  useEffect(() => {
    async function loadData() {
      setIsLoading(true)
      try {
        const data = await fetchDashboardDataPaged({ page, size: PAGE_SIZE })

        if (!data) {
          setAnimals([])
          setSummary({})
          setTotalAnimals(0)
          setTotalPages(0)
          setHasNext(false)
          setHasPrev(false)
          return
        }

        setAnimals(data.animals.length === 0 ? [] : data.animals)
        setSummary(data.summary || {})
        setTotalAnimals(data.total)
        setTotalPages(data.total_pages)
        setHasNext(data.has_next)
        setHasPrev(data.has_prev)

        if (data.total_pages > 0 && page > data.total_pages) {
          setPage(data.total_pages)
          return
        }

        setLastFetchTime(new Date())
      } catch (err) {
        console.error(err)
      } finally {
        setIsLoading(false)
      }
    }
    loadData()

    // Optional: Refresh periodically
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [page])

  const countBySummary = (status: string) => {
    const exact = summary[status]
    if (typeof exact === "number") return exact
    const underscored = summary[status.replace(/\s+/g, "_")]
    if (typeof underscored === "number") return underscored
    return 0
  }

  const metrics = {
    total: totalAnimals,
    sana: countBySummary("sana"),
    mastitis: countBySummary("mastitis") + countBySummary("subclinica") + countBySummary("clinica"),
    celo: countBySummary("celo"),
    febril: countBySummary("febril"),
    digestivo: countBySummary("digestivo"),
    sinDatos: countBySummary("sin datos"),
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden text-on-surface bg-surface">
      <PageHeader />

      <div className="flex-1 flex overflow-hidden">
        {/* Main Content */}
        <div className="flex-3 flex flex-col p-6 gap-6 overflow-hidden">
          <SummaryMetrics metrics={metrics} className="shrink-0" />

          {isLoading && animals.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4 text-on-surface-variant">
                <Activity className="w-8 h-8 animate-spin text-primary" />
                <p className="font-mono text-label-md">OBTENIENDO DATOS DEL SERVIDOR...</p>
              </div>
            </div>
          ) : animals.length === 0 ? (
            <div className="flex-1 flex items-center justify-center border border-dashed border-outline-variant/30 rounded-xl">
              <p className="font-mono text-label-md text-on-surface-variant">NO SE ENCONTRARON ANIMALES REGISTRADOS</p>
            </div>
          ) : (
            <>
              <HerdMap
                animals={animals}
                lastFetchTime={lastFetchTime}
                onAnimalClick={(id) => router.push(`/animal/${id}`)}
                className="flex-1 min-h-0"
              />

              <div className="shrink-0 rounded-xl border border-outline-variant/30 bg-surface-container p-3 flex items-center justify-between">
                <p className="text-label-sm text-on-surface-variant">
                  Página {page} de {totalPages || 0} | {totalAnimals} vacas totales
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                    disabled={!hasPrev}
                    className="rounded-md border border-outline-variant/40 bg-surface px-3 py-1.5 text-label-sm text-on-surface-variant disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((prev) => prev + 1)}
                    disabled={!hasNext}
                    className="rounded-md border border-outline-variant/40 bg-surface px-3 py-1.5 text-label-sm text-on-surface-variant disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
