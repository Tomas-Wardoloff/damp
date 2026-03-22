import * as React from "react"
import Image from "next/image"
import { cn } from "@/lib/utils"
import { StatusBadge, type Status } from "@/components/ui/StatusBadge"
import { Activity, Thermometer, Heart, Wind } from "lucide-react"

export interface Animal {
  id: string
  breed?: string
  status: Status
  temperature: number | string
  heartRate: number | string
  distance: number | string
  lastUpdated: string
}

interface AnimalCardProps extends React.HTMLAttributes<HTMLDivElement> {
  animal: Animal
}

export function AnimalCard({ animal, className, ...props }: AnimalCardProps) {
  const normStatus = animal.status?.toLowerCase() as string;
  const statusBorderColor = {
    sana: "border-primary/20 hover:border-primary/50",
    subclinica: "border-amber-500/30 hover:border-amber-500/60",
    clinica: "border-red-500/40 hover:border-red-500/80",
    mastitis: "border-red-500/40 hover:border-red-500/80",
    febril: "border-amber-500/30 hover:border-amber-500/60",
    digestivo: "border-orange-500/30 hover:border-orange-500/60",
    celo: "border-blue-500/30 hover:border-blue-500/60",
    "sin datos": "border-outline-variant/50 hover:border-outline-variant",
  }[normStatus] || "border-outline-variant/50 hover:border-outline-variant"

  const statusIconWrapColor = {
    sana: "border-primary/35 bg-primary/10",
    subclinica: "border-amber-500/35 bg-amber-500/10",
    clinica: "border-red-500/35 bg-red-500/10",
    mastitis: "border-red-500/35 bg-red-500/10",
    febril: "border-amber-500/35 bg-amber-500/10",
    digestivo: "border-orange-500/35 bg-orange-500/10",
    celo: "border-blue-500/35 bg-blue-500/10",
    "sin datos": "border-outline-variant/40 bg-surface-container-highest",
  }[normStatus] || "border-outline-variant/40 bg-surface-container-highest"

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
      <div className="flex justify-between items-start gap-3">
        <div className="min-w-0">
          <h3 className="text-base leading-tight font-display mb-0.5 text-on-surface">
            ID: #{animal.id}
          </h3>
          <p className="text-label-sm text-on-surface-variant uppercase tracking-wider">
            {animal.breed}
          </p>
        </div>
        <StatusBadge status={animal.status} />
      </div>

      <div className="mt-2 grid grid-cols-[1fr_auto] gap-3 items-center">
        <div className="grid grid-cols-2 gap-2 gap-y-3 min-w-0">
          <div className="flex items-center gap-2">
            <Thermometer className="w-4 h-4 text-on-surface-variant group-hover:text-secondary drop-shadow-sm transition-colors" />
            <span className="text-body-md whitespace-nowrap">
              {typeof animal.temperature === 'number' ? animal.temperature.toFixed(1) : animal.temperature}°C
            </span>
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

        <div className="flex items-center justify-center pr-0.5">
          <div className={cn("shrink-0 rounded-lg border p-2", statusIconWrapColor)}>
            <Image
              src="/cow-animals-svgrepo-com.svg"
              alt="Vaca"
              width={32}
              height={32}
              className="opacity-95"
            />
          </div>
        </div>
      </div>

      {normStatus === 'clinica' || normStatus === 'mastitis' ? (
        <div className="absolute inset-0 bg-red-500/5 pointer-events-none rounded-lg animate-pulse" />
      ) : null}
      {normStatus === 'subclinica' || normStatus === 'febril' ? (
        <div className="absolute inset-0 bg-amber-500/5 pointer-events-none rounded-lg" />
      ) : null}
      {normStatus === 'digestivo' ? (
        <div className="absolute inset-0 bg-orange-500/5 pointer-events-none rounded-lg" />
      ) : null}
    </div>
  )
}