import * as React from "react"
import { cn } from "@/lib/utils"
import { Thermometer, Heart, Wind, Activity, BrainCircuit, MapPin, Compass } from "lucide-react"

interface BiometricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: string | number
  unit?: string
  status: "normal" | "warning" | "high" | "low"
  icon: React.ReactNode
  labelOverride?: string
  iconDescription?: string
}

function BiometricCard({ title, value, unit, status, icon, className, labelOverride, iconDescription, ...props }: BiometricCardProps) {
  const statusStyles = {
    normal: {
      text: "text-primary",
      bg: "bg-primary-container/10",
      border: "border-primary/30",
      accent: "bg-primary",
      label: "Estable"
    },
    warning: {
      text: "text-[var(--color-warning)]",
      bg: "bg-[var(--color-warning)]/10",
      border: "border-[var(--color-warning)]/30",
      accent: "bg-[var(--color-warning)]",
      label: "Atención"
    },
    high: {
      text: "text-secondary",
      bg: "bg-secondary-container/10",
      border: "border-secondary/30",
      accent: "bg-secondary",
      label: "Elevado"
    },
    low: {
      text: "text-secondary",
      bg: "bg-secondary-container/10",
      border: "border-secondary/30",
      accent: "bg-secondary",
      label: "Bajo"
    }
  }

  const current = statusStyles[status]
  const displayLabel = labelOverride || current.label
  const isStringValue = typeof value === 'string' && value.length > 5;
  const valueClass = isStringValue ? "text-3xl md:text-3xl" : "text-6xl md:text-7xl";

  return (
    <div
      className={cn(
        "relative p-6 rounded-xl border flex flex-col justify-between shadow-sm transition-all",
        current.bg,
        current.border,
        className
      )}
      {...props}
    >
      <div className={cn("absolute top-0 left-0 w-full h-1", current.accent)} />

      <div className="flex justify-between items-start mb-4">
        <h4 className="text-label-md text-on-surface-variant font-mono uppercase tracking-widest mt-1">
          {title}
        </h4>
        <div className="relative group flex items-center justify-center">
          <div 
            className={cn("p-2 rounded-md bg-surface-container-highest cursor-help transition-colors duration-200 group-hover:text-white", current.text)}
          >
            <div className="w-5 h-5 flex items-center justify-center">
              {icon}
            </div>
          </div>
          
          {iconDescription && (
            <span className="pointer-events-none absolute right-0 top-full z-[80] mt-2 w-64 rounded-xl bg-slate-900 px-4 py-3 text-[12px] font-normal leading-relaxed text-white opacity-0 shadow-lg shadow-black/40 transition-opacity duration-200 group-hover:opacity-100 whitespace-pre-line text-left">
              {iconDescription}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-2 mt-auto z-10">
        <div className="flex items-baseline gap-2 flex-wrap">
          <div className={cn(`leading-none font-display font-bold tracking-tight ${valueClass}`, current.text)}>
            {value}
          </div>
          {unit && <span className="text-body-md text-on-surface-variant font-mono uppercase tracking-widest">{unit}</span>}
        </div>
        <p className="text-label-sm text-on-surface-variant uppercase tracking-widest font-mono">
          {displayLabel}
        </p>
      </div>

      {/* Subtle glow effect */}
      <div className="absolute inset-0 rounded-xl overflow-hidden pointer-events-none z-0">
        <div className={cn(
          "absolute -bottom-6 -right-6 w-32 h-32 blur-[32px] rounded-full",
          status === 'normal' ? "bg-primary/10" : "bg-secondary/15"
        )} />
      </div>
    </div>
  )
}

interface Biometrics {
  temperature: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  heartRate: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  distance: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  rmssd: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  sdnn: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  location: { value: string; status: "normal" | "warning" | "high" | "low" }
}

interface BiometricCardsProps extends React.HTMLAttributes<HTMLDivElement> {
  biometrics: Biometrics
}

export function BiometricCards({ biometrics, className, ...props }: BiometricCardsProps) {
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-3 gap-4", className)} {...props}>
      <BiometricCard
        title="Temperatura"
        value={biometrics.temperature.value}
        unit="°C"
        status={biometrics.temperature.status}
        icon={<Thermometer />}
        iconDescription="Medición de temperatura corporal del animal. Rango normal (Sana): ~38.5 °C"
      />
      <BiometricCard
        title="Frec. Cardíaca"
        value={biometrics.heartRate.value}
        unit="BPM"
        status={biometrics.heartRate.status}
        icon={<Heart />}
        iconDescription="Latidos por minuto detectados. Rango normal (Sana): 62 - 66 BPM"
      />
      <BiometricCard
        title="Distancia"
        value={biometrics.distance.value}
        unit="MTS"
        status={biometrics.distance.status}
        icon={<Wind />}
        labelOverride="Actividad Física"
        iconDescription="Distancia total recorrida. Promedio normal (Sana): ~100 MTS"
      />
      <BiometricCard
        title="RMSSD"
        value={biometrics.rmssd.value}
        unit="ms"
        status={biometrics.rmssd.status}
        icon={<Activity />}
        labelOverride="Var. Frec. Card."
        iconDescription="Root Mean Square of Successive Differences (Indicador de estrés agudo). Rango normal (Sana): 41 - 43 ms"
      />
      <BiometricCard
        title="SDNN"
        value={biometrics.sdnn.value}
        unit="ms"
        status={biometrics.sdnn.status}
        icon={<Activity />}
        labelOverride="Var. Total"
        iconDescription="Standard Deviation of NN intervals (Indicador de estrés crónico). Rango normal (Sana): > 50 ms"
      />
      <BiometricCard
        title="Ubicación GPS"
        value={biometrics.location.value}
        status={biometrics.location.status}
        icon={<MapPin />}
        labelOverride="Coordenadas"
        iconDescription="Última posición GPS registrada (Latitud, Longitud)"
      />
    </div>
  )
}