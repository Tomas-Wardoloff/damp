"use client"

import { AlertTriangle, CheckCircle, Info } from "lucide-react"
import { DIAGNOSIS_CONTENT, URGENCY_CONFIG, type CowStatus } from "@/types"
import { cn } from "@/lib/utils"

interface Props {
  status: CowStatus
  confidence: number
  className?: string
}

export function DiagnosisPanel({ status, confidence, className }: Props) {
  const content = DIAGNOSIS_CONTENT[status] ?? DIAGNOSIS_CONTENT["HEALTHY"]
  const urgency = URGENCY_CONFIG[content.urgency]
  const confPercent = Math.round(confidence * 100)

  const UrgencyIcon =
    content.urgency === "none" ? CheckCircle :
      content.urgency === "high" ? AlertTriangle :
        Info

  return (
    <div className="rounded-2xl border border-outline-variant/30 bg-surface-container-low overflow-hidden">

      {/* Header strip — urgency color */}
      <div className="p-6 flex items-center justify-between border-b border-outline-variant/30">
        <div className="flex items-center gap-2">
          <span className="text-headline-md font-display mb-1">
            Diagnóstico con IA
          </span>
        </div>
        <span className={cn("text-xs font-bold px-2.5 py-1 rounded-full border", urgency.bg, urgency.color, urgency.border)}>
          {urgency.label}
        </span>
      </div>

      <div className="p-5 flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold text-on-surface">{content.label}</h3>
            <p className="mt-1 text-sm text-on-surface-variant">{content.summary}</p>
          </div>

          <div className="shrink-0 flex flex-col items-center gap-1">
            <p className="text-6xl font-bold tracking-tighter tabular-nums">
              {confPercent}%
            </p>
            <span className="text-xs text-on-surface-variant/70 text-center leading-tight">
              confianza del modelo
            </span>
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-2">
            Qué significa
          </p>
          <p className="text-sm text-on-surface leading-relaxed">
            {content.what_it_means}
          </p>
        </div>

        {/* Recommendation */}
        <div className={cn("rounded-xl border p-4 flex gap-3 items-start", urgency.bg, urgency.border)}>
          <UrgencyIcon className={cn("w-4 h-4 mt-0.5 shrink-0", urgency.color)} />
          <div>
            <p className={cn("text-xs font-semibold uppercase tracking-wider mb-1", urgency.color)}>
              Acción recomendada
            </p>
            <p className="text-sm text-on-surface leading-relaxed">
              {content.recommendation}
            </p>
          </div>
        </div>

      </div>
    </div >
  )
}