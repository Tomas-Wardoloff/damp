import * as React from "react"
import { cn } from "@/lib/utils"

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: number | string
  subtitle: string
  status?: "neutral" | "healthy" | "warning" | "critical"
}

export function MetricCard({ title, value, subtitle, status = "neutral", className, ...props }: MetricCardProps) {
  const statusStyles = {
    neutral: {
      text: "text-on-surface",
      bg: "bg-surface-container-low",
      border: "border-outline-variant",
      accent: "bg-outline-variant/30"
    },
    healthy: {
      text: "text-primary",
      bg: "bg-primary-container/10",
      border: "border-primary/30",
      accent: "bg-primary"
    },
    warning: {
      text: "text-secondary",
      bg: "bg-secondary-container/10",
      border: "border-secondary/30",
      accent: "bg-secondary"
    },
    critical: {
      text: "text-tertiary",
      bg: "bg-tertiary-container/10",
      border: "border-tertiary/40",
      accent: "bg-tertiary"
    }
  }[status]

  return (
    <div
      className={cn(
        "relative p-6 rounded-xl border flex flex-col justify-between overflow-hidden shadow-sm transition-all",
        statusStyles.bg,
        statusStyles.border,
        className
      )}
      {...props}
    >
      <div className={cn("absolute top-0 left-0 w-full h-1", statusStyles.accent)} />

      <h4 className="text-label-md text-on-surface-variant font-mono uppercase tracking-widest mb-4">
        {title}
      </h4>

      <div className="flex flex-col gap-2 mt-auto">
        <div className={cn("text-6xl md:text-7xl leading-none font-display font-bold tracking-tight", statusStyles.text)}>
          {value}
        </div>
        <p className="text-body-md text-on-surface-variant">
          {subtitle}
        </p>
      </div>

      {/* Subtle glow effect for critical / warning purely as a vibe */}
      {status === 'critical' && (
        <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-tertiary/20 blur-[32px] rounded-full pointer-events-none" />
      )}
      {status === 'warning' && (
        <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-secondary/15 blur-[32px] rounded-full pointer-events-none" />
      )}
    </div>
  )
}
