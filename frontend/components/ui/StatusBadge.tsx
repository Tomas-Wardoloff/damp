import * as React from "react"
import { cn } from "@/lib/utils"

export type Status = "sana" | "subclinica" | "clinica" | "mastitis" | "celo" | "febril" | "digestivo" | "sin datos" | string

interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: Status
  pulse?: boolean
}

export function StatusBadge({ status, pulse = false, className, ...props }: StatusBadgeProps) {
  const normStatus = status?.toLowerCase() as string;
  
  const statusConfig: Record<string, { bg: string, dot: string }> = {
    sana: {
      bg: "bg-primary-container/20 text-primary border-primary/30",
      dot: "bg-primary vital-pulse-primary"
    },
    subclinica: {
      bg: "bg-amber-500/20 text-amber-500 border-amber-500/30",
      dot: "bg-amber-500 animate-pulse"
    },
    clinica: {
      bg: "bg-red-500/20 text-red-500 border-red-500/30",
      dot: "bg-red-500 animate-pulse"
    },
    mastitis: {
      bg: "bg-red-500/20 text-red-500 border-red-500/30",
      dot: "bg-red-500 vital-pulse-tertiary"
    },
    celo: {
      bg: "bg-blue-500/20 text-blue-400 border-blue-500/30",
      dot: "bg-blue-400 animate-pulse"
    },
    febril: {
      bg: "bg-amber-500/20 text-amber-500 border-amber-500/30",
      dot: "bg-amber-500 animate-pulse"
    },
    digestivo: {
      bg: "bg-orange-500/20 text-orange-500 border-orange-500/30",
      dot: "bg-orange-500 animate-pulse"
    },
    "sin datos": {
      bg: "bg-surface-container/50 text-on-surface-variant border-outline-variant/50",
      dot: "bg-outline-variant/50 animate-none"
    }
  }

  const current = statusConfig[normStatus] || statusConfig.sana

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
