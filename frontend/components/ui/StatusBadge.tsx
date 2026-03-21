import * as React from "react"
import { cn } from "@/lib/utils"

export type Status = "sana" | "subclinica" | "mastitis" | "celo" | "febril" | "digestivo" | string

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
      bg: "bg-secondary-container/20 text-secondary border-secondary/30",
      dot: "bg-secondary animate-pulse"
    },
    mastitis: {
      bg: "bg-tertiary-container/20 text-tertiary border-tertiary/30",
      dot: "bg-tertiary vital-pulse-tertiary"
    },
    celo: {
      bg: "bg-blue-500/20 text-blue-400 border-blue-500/30",
      dot: "bg-blue-400 animate-pulse"
    },
    febril: {
      bg: "bg-secondary-container/20 text-secondary border-secondary/30",
      dot: "bg-secondary animate-pulse"
    },
    digestivo: {
      bg: "bg-secondary-container/20 text-secondary border-secondary/30",
      dot: "bg-secondary animate-pulse"
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
