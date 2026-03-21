import * as React from "react"
import { cn } from "@/lib/utils"

export type Status = "healthy" | "warning" | "critical"

interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: Status
  pulse?: boolean
}

export function StatusBadge({ status, pulse = false, className, ...props }: StatusBadgeProps) {
  const statusConfig = {
    healthy: {
      bg: "bg-primary-container/20 text-primary border-primary/30",
      dot: "bg-primary vital-pulse-primary"
    },
    warning: {
      bg: "bg-secondary-container/20 text-secondary border-secondary/30",
      dot: "bg-secondary vital-pulse-secondary"
    },
    critical: {
      bg: "bg-tertiary-container/20 text-tertiary border-tertiary/30",
      dot: "bg-tertiary vital-pulse-tertiary"
    }
  }

  const current = statusConfig[status]

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 px-2.5 py-1 rounded-sm border bg-surface-container-highest",
        className
      )}
      {...props}
    >
      <div 
        className={cn(
          "w-2 h-2 rounded-full",
          current.dot,
          !pulse && "animate-none shadow-none"
        )} 
      />
      <span className="text-label-sm uppercase tracking-widest font-mono text-on-surface">
        {status}
      </span>
    </div>
  )
}
