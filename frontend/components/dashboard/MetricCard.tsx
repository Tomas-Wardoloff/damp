import * as React from "react"
import Image from "next/image"
import { cn } from "@/lib/utils"

export type MetricStatus = "neutral" | "sana" | "subclinica" | "clinica" | "mastitis" | "celo" | "febril" | "digestivo" | "sin_datos"

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: number | string
  subtitle: string
  status?: MetricStatus
  iconSrc?: string
  iconAlt?: string
  iconClassName?: string
}

export function MetricCard({
  title,
  value,
  subtitle,
  status = "neutral",
  iconSrc,
  iconAlt = "Icono",
  iconClassName,
  className,
  ...props
}: MetricCardProps) {
  const statusStyles: Record<MetricStatus, { text: string; bg: string; border: string; accent: string; glow: string | null }> = {
    neutral: {
      text: "text-on-surface",
      bg: "bg-surface-container-low",
      border: "border-outline-variant",
      accent: "bg-outline-variant/30",
      glow: null
    },
    sana: {
      text: "text-primary",
      bg: "bg-primary-container/12",
      border: "border-primary/35",
      accent: "bg-primary",
      glow: "bg-primary/18"
    },
    subclinica: {
      text: "text-amber-500",
      bg: "bg-amber-500/12",
      border: "border-amber-500/35",
      accent: "bg-amber-500",
      glow: "bg-amber-500/15"
    },
    clinica: {
      text: "text-red-500",
      bg: "bg-red-500/12",
      border: "border-red-500/35",
      accent: "bg-red-500",
      glow: "bg-red-500/20"
    },
    mastitis: {
      text: "text-red-500",
      bg: "bg-red-500/12",
      border: "border-red-500/35",
      accent: "bg-red-500",
      glow: "bg-red-500/22"
    },
    febril: {
      text: "text-amber-500",
      bg: "bg-amber-500/12",
      border: "border-amber-500/35",
      accent: "bg-amber-500",
      glow: "bg-amber-500/18"
    },
    digestivo: {
      text: "text-orange-500",
      bg: "bg-orange-500/12",
      border: "border-orange-500/35",
      accent: "bg-orange-500",
      glow: "bg-orange-500/18"
    },
    celo: {
      text: "text-blue-400",
      bg: "bg-blue-500/12",
      border: "border-blue-500/35",
      accent: "bg-blue-400",
      glow: "bg-blue-400/18"
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
        <div className="flex items-center justify-between gap-3">
          <div className={cn("text-3xl sm:text-4xl lg:text-5xl leading-none font-display font-bold tracking-tight", style.text)}>
            {value}
          </div>
          {iconSrc && (
            <div className="w-17 h-17 shrink-0 -translate-x-1 flex items-center justify-center pointer-events-none">
              <Image
                src={iconSrc}
                alt={iconAlt}
                width={68}
                height={68}
                className={cn(
                  "opacity-55 brightness-0 invert object-contain",
                  iconClassName,
                )}
              />
            </div>
          )}
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
