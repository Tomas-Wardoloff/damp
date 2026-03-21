import * as React from "react"
import { cn } from "@/lib/utils"
import { StatusBadge, type Status } from "@/components/ui/StatusBadge"
import { Activity, Thermometer, Heart, Wind } from "lucide-react"

export interface Animal {
  id: string
  breed?: string
  status: Status
  temperature: number
  heartRate: number
  distance: number
  lastUpdated: string
}

interface AnimalCardProps extends React.HTMLAttributes<HTMLDivElement> {
  animal: Animal
}

export function AnimalCard({ animal, className, ...props }: AnimalCardProps) {
  const statusBorderColor = {
    healthy: "border-primary/20 hover:border-primary/50",
    warning: "border-secondary/30 hover:border-secondary/60",
    critical: "border-tertiary/40 hover:border-tertiary/80"
  }[animal.status]

  return (
    <div
      className={cn(
        "group relative flex flex-col p-4 gap-3 bg-surface-container rounded-lg border border-outline-variant transition-colors cursor-pointer",
        statusBorderColor,
        "hover:bg-surface-container-highest",
        className
      )}
      {...props}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-base leading-tight font-display mb-0.5 text-on-surface">
            ID: #{animal.id}
          </h3>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider">
            {animal.breed}
          </p>
        </div>
        <StatusBadge status={animal.status} pulse={animal.status !== 'healthy'} />
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2 gap-y-3">
        <div className="flex items-center gap-2">
          <Thermometer className="w-4 h-4 text-on-surface-variant group-hover:text-secondary drop-shadow-sm transition-colors" />
          <span className="text-body-md whitespace-nowrap">{animal.temperature.toFixed(1)}°C</span>
        </div>
        <div className="flex items-center gap-2">
          <Heart className="w-4 h-4 text-on-surface-variant group-hover:text-tertiary drop-shadow-sm transition-colors" />
          <span className="text-body-md whitespace-nowrap">{animal.heartRate} bpm</span>
        </div>
        <div className="flex items-center gap-2">
          <Wind className="w-4 h-4 text-on-surface-variant group-hover:text-primary drop-shadow-sm transition-colors" />
          <span className="text-body-md whitespace-nowrap">{animal.distance} m</span>
        </div>
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-on-surface-variant group-hover:text-primary drop-shadow-sm opacity-80 transition-colors" />
          <span className="text-body-md text-primary">Normal</span>
        </div>
      </div>

      {animal.status === 'critical' && (
        <div className="absolute inset-0 bg-tertiary/5 pointer-events-none rounded-lg animate-pulse" />
      )}
      {animal.status === 'warning' && (
        <div className="absolute inset-0 bg-secondary/5 pointer-events-none rounded-lg" />
      )}
    </div>
  )
}
