"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { SummaryMetrics } from "@/components/dashboard/SummaryMetrics"
import { HerdMap } from "@/components/dashboard/HerdMap"
import { AlertFeed } from "@/components/alerts/AlertFeed"
import { useRouter } from "next/navigation"
import { PageHeader } from "@/components/layout/PageHeader"
import { fetchDashboardData } from "@/lib/api"
import { type Animal } from "@/components/animal/AnimalCard"
import { type Alert } from "@/components/alerts/AlertFeed"
import { Activity } from "lucide-react"

export default function Dashboard() {
  const router = useRouter()

  const [animals, setAnimals] = useState<Animal[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null)

  useEffect(() => {
    async function loadData() {
      setIsLoading(true)
      try {
        const data = await fetchDashboardData()

        // As fallback for the demo if backend is empty/offline:
        if (data.animals.length === 0) {
          // You could load MOCK_ANIMALS here, but let's show an empty state or let the HerdMap handle it
          setAnimals([])
        } else {
          setAnimals(data.animals)
        }
        setAlerts(data.alerts)
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
  }, [])

  const metrics = {
    total: animals.length,
    healthy: animals.filter(a => a.status === "healthy").length,
    warning: animals.filter(a => a.status === "warning").length,
    critical: animals.filter(a => a.status === "critical").length,
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
            <HerdMap
              animals={animals}
              lastFetchTime={lastFetchTime}
              onAnimalClick={(id) => router.push(`/animal/${id}`)}
              className="flex-1 min-h-0"
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="flex-1 min-w-[320px] max-w-100 border-l border-outline-variant/30 p-6 bg-surface-container-lowest overflow-y-auto">
          <AlertFeed
            alerts={alerts}
            onViewAnimal={(id) => router.push(`/animal/${id}`)}
          />
        </div>
      </div>
    </div>
  )
}
