import * as React from "react"
import { cn } from "@/lib/utils"
import { Bell } from "lucide-react"
import { AlertCard } from "./AlertCard"

export interface Alert {
  id: string
  animalId: string
  animalName: string
  condition: string
  severity: "warning" | "critical"
  timestamp: string
}

interface AlertFeedProps extends React.HTMLAttributes<HTMLDivElement> {
  alerts: Alert[]
  onViewAnimal: (animalId: string) => void
}

export function AlertFeed({ alerts, onViewAnimal, className, ...props }: AlertFeedProps) {
  return (
    <div className={cn("bg-surface-container-low rounded-lg border border-outline-variant flex flex-col overflow-hidden", className)} {...props}>
      <div className="p-4 border-b border-outline-variant/30 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-on-surface-variant" />
          <h3 className="text-body-md font-semibold tracking-wide uppercase text-on-surface">Alertas Activas</h3>
        </div>
        <span className="text-label-sm bg-tertiary-container/20 text-tertiary px-2 py-0.5 rounded-sm">
          {alerts.length}
        </span>
      </div>
      <div className="overflow-y-auto p-4 flex flex-col gap-3">
        {alerts.map((alert) => (
          <AlertCard 
            key={alert.id} 
            alert={alert} 
            onViewAnimal={onViewAnimal} 
          />
        ))}
      </div>
    </div>
  )
}
