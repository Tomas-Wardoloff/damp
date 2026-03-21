import * as React from "react"
import { cn } from "@/lib/utils"
import { Thermometer, Heart, Wind, Activity, BrainCircuit, Mic } from "lucide-react"

interface BiometricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: string | number
  unit?: string
  status: "normal" | "warning" | "high" | "low"
  icon: React.ReactNode
  labelOverride?: string
}

function BiometricCard({ title, value, unit, status, icon, className, labelOverride, ...props }: BiometricCardProps) {
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
        "relative p-6 rounded-xl border flex flex-col justify-between overflow-hidden shadow-sm transition-all",
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
        <div className={cn("p-2 rounded-md bg-surface-container-highest", current.text)}>
          <div className="w-5 h-5 flex items-center justify-center">
            {icon}
          </div>
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
      <div className={cn(
        "absolute -bottom-6 -right-6 w-32 h-32 blur-[32px] rounded-full pointer-events-none",
        status === 'normal' ? "bg-primary/10" : "bg-secondary/15"
      )} />
    </div>
  )
}

interface Biometrics {
  temperature: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  heartRate: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  distance: { value: number | string; status: "normal" | "warning" | "high" | "low" }
  stress: { value: string; status: "normal" | "warning" | "high" | "low" }
  rumination: { value: string; status: "normal" | "warning" | "high" | "low" }
  vocalization: { value: string; status: "normal" | "warning" | "high" | "low" }
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
      />
      <BiometricCard 
        title="Frec. Cardíaca" 
        value={biometrics.heartRate.value} 
        unit="BPM" 
        status={biometrics.heartRate.status}
        icon={<Heart />}
      />
      <BiometricCard 
        title="Distancia" 
        value={biometrics.distance.value} 
        unit="MTS" 
        status={biometrics.distance.status}
        icon={<Wind />}
        labelOverride="Actividad Física"
      />
      <BiometricCard 
        title="Estrés Fisiológico" 
        value={biometrics.stress.value} 
        status={biometrics.stress.status}
        icon={<BrainCircuit />}
        labelOverride="Análisis HRV"
      />
      <BiometricCard 
        title="Rumia" 
        value={biometrics.rumination.value} 
        status={biometrics.rumination.status}
        icon={<Activity />}
        labelOverride="Actividad Digestiva"
      />
      <BiometricCard 
        title="Vocalización" 
        value={biometrics.vocalization.value} 
        status={biometrics.vocalization.status}
        icon={<Mic />}
        labelOverride="Sonido emitido"
      />
    </div>
  )
}
