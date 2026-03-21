import * as React from "react"
import { cn } from "@/lib/utils"
import { TriangleAlert, Clock3 } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { type Alert } from "./AlertFeed"

interface AlertCardProps extends React.HTMLAttributes<HTMLDivElement> {
  alert: Alert
  onViewAnimal: (animalId: string) => void
}

export function AlertCard({ alert, onViewAnimal, className, ...props }: AlertCardProps) {
  return (
    <div
      className={cn("group relative bg-surface p-4 rounded-md border border-outline-variant/50 hover:border-outline-variant transition-colors flex flex-col gap-2", className)}
      {...props}
    >
      <div className="flex items-start justify-between">
        <div className="flex gap-2 items-center">
          <TriangleAlert
            className={cn("w-4 h-4", alert.severity === "critical" ? "text-tertiary" : "text-secondary")}
          />
          <h4 className="text-body-md font-display font-medium text-on-surface">
            {alert.animalName} ({alert.animalId})
          </h4>
        </div>
        <div className="flex text-on-surface-variant text-label-sm items-center gap-1 font-mono">
          <Clock3 className="w-3 h-3" />
          {alert.timestamp}
        </div>
      </div>

      <p className="text-body-md text-on-surface-variant">
        {alert.condition}
      </p>

      <Button
        variant="text"
        size="none"
        className={cn(
          "mt-2 w-fit",
          alert.severity === "critical" ? "text-tertiary" : "text-secondary"
        )}
        onClick={() => onViewAnimal(alert.animalId)}
      >
        Ver Animal →
      </Button>

      {/* Subtle glow edge for critical/warning */}
      {alert.severity === 'critical' && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-tertiary rounded-l-md" />
      )}
      {alert.severity === 'warning' && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary rounded-l-md" />
      )}
    </div>
  )
}
