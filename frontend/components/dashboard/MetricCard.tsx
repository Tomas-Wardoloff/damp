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
      text: "text-[#2ecc71]",
      bg: "bg-[#2ecc71]/10",
      border: "border-[#2ecc71]/30",
      accent: "bg-[#2ecc71]",
      glow: "bg-[#2ecc71]/10"
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
      text: "text-[#e74c3c]",
      bg: "bg-[#e74c3c]/10",
      border: "border-[#e74c3c]/30",
      accent: "bg-[#e74c3c]",
      glow: "bg-[#e74c3c]/20"
    },
    febril: {
      text: "text-[#e67e22]",
      bg: "bg-[#e67e22]/10",
      border: "border-[#e67e22]/30",
      accent: "bg-[#e67e22]",
      glow: "bg-[#e67e22]/15"
    },
    digestivo: {
      text: "text-[#1abc9c]",
      bg: "bg-[#1abc9c]/10",
      border: "border-[#1abc9c]/30",
      accent: "bg-[#1abc9c]",
      glow: "bg-[#1abc9c]/15"
    },
    celo: {
      text: "text-[#9b59b6]",
      bg: "bg-[#9b59b6]/10",
      border: "border-[#9b59b6]/30",
      accent: "bg-[#9b59b6]",
      glow: "bg-[#9b59b6]/15"
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
