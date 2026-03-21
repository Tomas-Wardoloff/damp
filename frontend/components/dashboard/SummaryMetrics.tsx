import * as React from "react"
import { cn } from "@/lib/utils"
import { MetricCard } from "./MetricCard"

interface SummaryMetricsProps extends React.HTMLAttributes<HTMLDivElement> {
  metrics: {
    total: number
    sana: number
    mastitis: number
    celo: number
    febril: number
    digestivo: number
    sinDatos: number
  }
}

export function SummaryMetrics({ metrics, className, ...props }: SummaryMetricsProps) {
  const getPercentage = (value: number) => {
    return metrics.total > 0 ? Math.round((value / metrics.total) * 100) : 0;
  };

  return (
    <div className={cn("grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-4", className)} {...props}>
      <MetricCard
        title="Total Ganado"
        value={metrics.total}
        subtitle="Monitoreados"
        status="neutral"
      />
      <MetricCard
        title="Sin Datos"
        value={metrics.sinDatos}
        status="sin_datos"
        subtitle={`${getPercentage(metrics.sinDatos)}% del ganado`}
      />
      <MetricCard
        title="Sanas"
        value={metrics.sana}
        status="sana"
        subtitle={`${getPercentage(metrics.sana)}% del ganado`}
      />
      <MetricCard
        title="Mastitis"
        value={metrics.mastitis}
        status="mastitis"
        subtitle={`${getPercentage(metrics.mastitis)}% del ganado`}
      />
      <MetricCard
        title="Celo"
        value={metrics.celo}
        status="celo"
        subtitle={`${getPercentage(metrics.celo)}% del ganado`}
      />
      <MetricCard
        title="Febril"
        value={metrics.febril}
        status="febril"
        subtitle={`${getPercentage(metrics.febril)}% del ganado`}
      />
      <MetricCard
        title="Digestivo"
        value={metrics.digestivo}
        status="digestivo"
        subtitle={`${getPercentage(metrics.digestivo)}% del ganado`}
      />
    </div>
  )
}
