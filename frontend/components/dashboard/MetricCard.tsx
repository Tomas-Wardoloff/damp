import * as React from "react"
import { cn } from "@/lib/utils"

export type MetricStatus = "neutral" | "sana" | "subclinica" | "clinica" | "mastitis" | "celo" | "febril" | "digestivo" | "sin_datos"

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: number | string
  subtitle: string
  status?: MetricStatus
}

export function MetricCard({ title, value, subtitle, status = "neutral", className, ...props }: MetricCardProps) {
  const statusStyles: Record<MetricStatus, { text: string; bg: string; border: string; accent: string; glow: string | null }> = {
    neutral: {
      text: "text-on-surface",
      bg: "bg-surface-container-low",
      border: "border-outline-variant",
      accent: "bg-outline-variant/30",
      glow: null
    },
    sana: {
      text: "text-[#16a34a]",
      bg: "bg-[#16a34a]/12",
      border: "border-[#16a34a]/35",
      accent: "bg-[#16a34a]",
      glow: "bg-[#16a34a]/18"
    },
    subclinica: {
      text: "text-secondary",
      bg: "bg-secondary-container/10",
      border: "border-secondary/30",
      accent: "bg-secondary",
      glow: "bg-secondary/15"
    },
    clinica: {
      text: "text-tertiary",
      bg: "bg-tertiary-container/10",
      border: "border-tertiary/40",
      accent: "bg-tertiary",
      glow: "bg-tertiary/20"
    },
    mastitis: {
      text: "text-[#dc2626]",
      bg: "bg-[#dc2626]/12",
      border: "border-[#dc2626]/35",
      accent: "bg-[#dc2626]",
      glow: "bg-[#dc2626]/22"
    },
    febril: {
      text: "text-[#eab308]",
      bg: "bg-[#eab308]/12",
      border: "border-[#eab308]/35",
      accent: "bg-[#eab308]",
      glow: "bg-[#eab308]/18"
    },
    digestivo: {
      text: "text-[#f97316]",
      bg: "bg-[#f97316]/12",
      border: "border-[#f97316]/35",
      accent: "bg-[#f97316]",
      glow: "bg-[#f97316]/18"
    },
    celo: {
      text: "text-[#ec4899]",
      bg: "bg-[#ec4899]/12",
      border: "border-[#ec4899]/35",
      accent: "bg-[#ec4899]",
      glow: "bg-[#ec4899]/18"
    },
    sin_datos: {
      text: "text-on-surface-variant",
      bg: "bg-surface-container/50",
      border: "border-outline-variant/50",
      accent: "bg-outline-variant/20",
      glow: null
    }
  }

  const style = statusStyles[status] || statusStyles.neutral

  return (
    <div
      className={cn(
        "relative p-4 md:p-6 rounded-xl border flex flex-col justify-between overflow-hidden shadow-sm transition-all",
        style.bg,
        style.border,
        className
      )}
      {...props}
    >
      <div className={cn("absolute top-0 left-0 w-full h-1", style.accent)} />

      <h4 className="text-label-sm md:text-label-md text-on-surface-variant font-mono uppercase tracking-widest mb-3 md:mb-4">
        {title}
      </h4>

      <div className="flex flex-col gap-1 md:gap-2 mt-auto">
        <div className={cn("text-3xl sm:text-4xl lg:text-5xl leading-none font-display font-bold tracking-tight", style.text)}>
          {value}
        </div>
        <p className="text-label-sm md:text-body-md text-on-surface-variant">
          {subtitle}
        </p>
      </div>

      {style.glow && (
        <div className={cn("absolute -bottom-6 -right-6 w-32 h-32 blur-[32px] rounded-full pointer-events-none", style.glow)} />
      )}
    </div>
  )
}
