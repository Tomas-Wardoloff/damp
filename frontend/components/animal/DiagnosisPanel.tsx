import * as React from "react"
import { cn } from "@/lib/utils"
import { BrainCircuit, AlertTriangle } from "lucide-react"

interface DiagnosisPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  condition: string
  confidence: number
  recommendation: string
}

export function DiagnosisPanel({ condition, confidence, recommendation, className, ...props }: DiagnosisPanelProps) {
  return (
    <div className={cn("relative overflow-hidden bg-surface-container-low p-6 rounded-lg border border-outline-variant flex flex-col gap-4", className)} {...props}>
      <div className="absolute -right-10 -top-10 text-outline-variant/5">
        <BrainCircuit className="w-48 h-48" />
      </div>
      
      <div className="flex items-center justify-between relative z-10">
        <div className="flex items-center gap-3">
          <div className="bg-surface p-2 rounded-md border border-outline-variant/30 text-primary">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <h3 className="text-label-md uppercase tracking-widest text-on-surface-variant">Diagnóstico Predictivo IA</h3>
        </div>
        
        <div className="flex flex-col items-end">
          <span className="text-display-lg text-primary leading-none">{confidence}%</span>
          <span className="text-label-sm uppercase font-mono text-on-surface-variant tracking-wider">Confianza del Modelo</span>
        </div>
      </div>

      <div className="relative z-10 flex flex-col gap-2 mt-2">
        <h4 className="text-headline-md font-display text-on-surface leading-snug">
          {condition}
        </h4>
        
        <div className="bg-surface p-4 rounded-md border-l-2 border-secondary/50 flex gap-3 items-start mt-2">
          <AlertTriangle className="w-5 h-5 text-secondary shrink-0 mt-0.5" />
          <div>
            <span className="text-label-sm block uppercase font-mono text-secondary mb-1">Acción Recomendada</span>
            <p className="text-body-md text-on-surface leading-relaxed">
              {recommendation}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
