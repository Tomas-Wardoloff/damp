import * as React from "react"
import Image from "next/image"
import { cn } from "@/lib/utils"

export type Status = "sana" | "subclinica" | "clinica" | "mastitis" | "celo" | "febril" | "digestivo" | "sin datos" | string

interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: Status
  pulse?: boolean
}

export function StatusBadge({ status, pulse = false, className, ...props }: StatusBadgeProps) {
  const normStatus = status?.toLowerCase() as string;
  const isCelo = normStatus === "celo"

  const statusIconMap: Record<string, string> = {
    sana: "/plus-heart-svgrepo-com.svg",
    subclinica: "/udder-svgrepo-com.svg",
    clinica: "/udder-svgrepo-com.svg",
    mastitis: "/udder-svgrepo-com.svg",
    celo: "/fire-1-svgrepo-com.svg",
    febril: "/thermometer-svgrepo-com.svg",
    digestivo: "/stomach-1-svgrepo-com.svg",
    "sin datos": "/toggle-on-svgrepo-com.svg",
  }
  
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
      bg: "bg-pink-500/20 text-pink-400 border-pink-500/30",
      dot: "bg-pink-400 animate-pulse"
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
  const statusIconSrc = statusIconMap[normStatus]

  return (
    <div
      className={cn(
        "inline-flex items-center py-1.5 rounded-sm border bg-surface-container-highest",
        isCelo ? "gap-2 px-2.5" : "gap-2.5 px-3",
        className
      )}
      {...props}
    >
      <div 
        className={cn(
          "w-2.5 h-2.5 rounded-full",
          current.dot,
          !pulse && "animate-none shadow-none"
        )} 
      />
      {statusIconSrc && (
        <Image
          src={statusIconSrc}
          alt={`Icono ${status}`}
          width={isCelo ? 18 : 14}
          height={isCelo ? 18 : 14}
          className={cn("opacity-80", isCelo && "-mx-0.5")}
        />
      )}
      <span className="text-sm uppercase tracking-widest font-mono text-on-surface">
        {status}
      </span>
    </div>
  )
}
