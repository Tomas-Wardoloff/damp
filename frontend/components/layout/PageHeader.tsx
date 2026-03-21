"use client"

import { usePathname } from "next/navigation"
import { LayoutDashboard, TriangleAlert, Map, Settings, Activity } from "lucide-react"

export interface PageHeaderProps {
  title?: string
  description?: string
}

export function PageHeader({ title, description }: PageHeaderProps = {}) {
  const pathname = usePathname()

  const pageInfo = {
    "/": {
      title: "Dashboard",
      description: "Vista general del sistema de monitoreo",
      icon: LayoutDashboard
    },
    "/alertas": {
      title: "Alertas",
      description: "Gestión de advertencias y eventos críticos",
      icon: TriangleAlert
    },
    "/mapa": {
      title: "Mapa de Rodeo",
      description: "Ubicación y estado de los animales",
      icon: Map
    },
    "/configuracion": {
      title: "Configuración",
      description: "Ajustes de la plataforma y preferencias",
      icon: Settings
    }
  }

  // Fallback to Dashboard if path not found exactly (e.g., dynamic routes could be handled later if needed)
  const current = pageInfo[pathname as keyof typeof pageInfo] || {
    title: "DAMP Sentinel",
    description: "Biomarker Monitoring System",
    icon: Activity
  }

  const displayTitle = title || current.title
  const displayDescription = description || current.description

  return (
    <header className="px-6 h-18 border-b border-outline-variant/30 flex justify-between items-center shrink-0">
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-headline-md font-display leading-none mb-1 text-on-surface">
            {displayTitle}
          </h1>
          <p className="text-label-sm font-mono text-on-surface-variant uppercase tracking-widest">
            {displayDescription}
          </p>
        </div>
      </div>
    </header>
  )
}
