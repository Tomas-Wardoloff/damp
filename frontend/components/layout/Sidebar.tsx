"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  TriangleAlert,
  Map as MapIcon,
  Settings,
  LifeBuoy,
  ChevronLeft,
  ChevronRight,
  Activity,
  User
} from "lucide-react"

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = React.useState(true)
  const pathname = usePathname()

  const navItems = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Alertas", href: "/alertas", icon: TriangleAlert },
    { name: "Mapa de Rodeo", href: "/mapa", icon: MapIcon },
    { name: "Configuración", href: "/configuracion", icon: Settings },
  ]

  return (
    <aside
      className={cn(
        "h-screen bg-surface-container-low border-r border-outline-variant/30 flex flex-col transition-all duration-300 relative z-20 shrink-0",
        isCollapsed ? "w-20" : "w-64"
      )}
    >
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-6 bg-surface-container border border-outline-variant rounded-full p-1 text-on-surface hover:text-primary transition-colors z-30 shadow-ambient"
      >
        {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>

      {/* Logo Area */}
      <div className="h-18 flex items-center justify-center border-b border-outline-variant/30 px-4">
        <div className={cn("flex items-center gap-3 w-full", isCollapsed ? "justify-center" : "")}>
          <div className="bg-primary/10 p-2 rounded-md shrink-0">
            <Activity className="w-6 h-6 text-primary" />
          </div>
          {!isCollapsed && (
            <div className="overflow-hidden whitespace-nowrap">
              <h1 className="text-headline-md font-display leading-none text-xl mb-0.5">DAMP</h1>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-6 flex flex-col gap-2 px-3 overflow-y-auto overflow-x-hidden">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              title={isCollapsed ? item.name : undefined}
              className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-md transition-all group",
                isActive
                  ? "bg-surface-container text-primary"
                  : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
              )}
            >
              <Icon className={cn("w-5 h-5 shrink-0", isActive ? "text-primary" : "text-on-surface-variant group-hover:text-on-surface")} />
              {!isCollapsed && (
                <span className="text-body-md whitespace-nowrap font-medium">
                  {item.name}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer Actions */}
      <div className="p-3 border-t border-outline-variant/30 flex flex-col gap-2">
        <button
          title={isCollapsed ? "Soporte" : undefined}
          className="flex items-center gap-3 px-3 py-3 rounded-md text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-all group w-full"
        >
          <LifeBuoy className="w-5 h-5 shrink-0" />
          {!isCollapsed && (
            <span className="text-body-md whitespace-nowrap font-medium">Soporte</span>
          )}
        </button>

        <button
          title={isCollapsed ? "Perfil de Usuario" : undefined}
          className="flex items-center gap-3 px-2 py-2 rounded-md hover:bg-surface-container transition-all text-left mt-2 w-full"
        >
          <div className="w-8 h-8 rounded-full bg-secondary outline-1 outline-offset-2 outline-secondary/30 shrink-0 overflow-hidden relative flex items-center justify-center">
            <User className="w-5 h-5 text-on-surface" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col whitespace-nowrap overflow-hidden">
              <span className="text-body-md font-medium text-on-surface leading-tight">user@email.com</span>
            </div>
          )}
        </button>
      </div>
    </aside>
  )
}
