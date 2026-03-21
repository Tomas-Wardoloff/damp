import * as React from "react"
import { cn } from "@/lib/utils"
import { MetricCard } from "./MetricCard"

interface SummaryMetricsProps extends React.HTMLAttributes<HTMLDivElement> {
  metrics: {
    total: number
    healthy: number
    warning: number
    critical: number
  }
}

export function SummaryMetrics({ metrics, className, ...props }: SummaryMetricsProps) {
  const healthyPercentage = metrics.total > 0 ? Math.round((metrics.healthy / metrics.total) * 100) : 0;

  return (
    <div className={cn("grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6", className)} {...props}>
      <MetricCard
        title="Cabezas de Ganado"
        value={metrics.total}
        subtitle="Animales monitoreados"
      />
      <MetricCard
        title="Animales Sanos"
        value={metrics.healthy}
        status="healthy"
        subtitle={`${healthyPercentage}% del ganado total`}
      />
      <MetricCard
        title="Animales en Riesgo"
        value={metrics.warning}
        status="warning"
        subtitle="Alerta moderada"
      />
      <MetricCard
        title="Animales en Estado Críticos"
        value={metrics.critical}
        status="critical"
        subtitle="Requieren atención"
      />
    </div>
  )
}
