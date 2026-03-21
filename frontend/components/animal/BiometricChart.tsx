"use client" // Needed since recharts uses context and hooks under the hood

import * as React from "react"
import { cn } from "@/lib/utils"
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  ReferenceArea 
} from "recharts"

interface Datapoint {
  time: string
  value: number
}

interface BiometricChartProps extends React.HTMLAttributes<HTMLDivElement> {
  data: Datapoint[]
  metricName?: string
  normalRange: [number, number]
  color?: string
}

export function BiometricChart({ 
  data, 
  metricName = "Temperature", 
  normalRange, 
  color = "#ffb95f", // Warning color as requested in spec for chart moving out
  className, 
  ...props 
}: BiometricChartProps) {
  // Safe bounds for chart Y axis
  const minVal = Math.min(...data.map(d => d.value), normalRange[0]) - 0.5
  const maxVal = Math.max(...data.map(d => d.value), normalRange[1]) + 0.5

  return (
    <div className={cn("bg-surface-container p-6 rounded-lg border border-outline-variant", className)} {...props}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-headline-md font-display mb-1">{metricName} - Últimas 24hs</h3>
          <p className="text-label-sm font-mono text-on-surface-variant flex gap-2 items-center">
            <span>Rango Normal: {normalRange[0]} - {normalRange[1]}</span>
            <span className="w-2 h-2 rounded bg-surface-container-highest inline-block border border-outline-variant" />
          </p>
        </div>
      </div>
      
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2c3038" vertical={false} />
            <XAxis 
              dataKey="time" 
              stroke="#9aa0a6" 
              fontSize={12} 
              tickLine={false} 
              axisLine={false} 
              tickMargin={12} 
            />
            <YAxis 
              stroke="#9aa0a6" 
              fontSize={12} 
              tickLine={false} 
              axisLine={false} 
              domain={[minVal, maxVal]}
              tickCount={6}
            />
            
            <Tooltip
              contentStyle={{
                backgroundColor: '#1c2026',
                border: '1px solid rgba(223,226,235,0.15)',
                borderRadius: '8px',
                color: '#dfe2eb'
              }}
              itemStyle={{ color: color }}
              labelStyle={{ color: '#9aa0a6', fontFamily: 'var(--font-space-grotesk)' }}
            />

            {/* Normal Range Band */}
            <ReferenceArea 
              y1={normalRange[0]} 
              y2={normalRange[1]} 
              fill="#ffffff" 
              fillOpacity={0.03} 
              ifOverflow="hidden" 
            />

            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={3}
              dot={{ r: 0, fill: color }}
              activeDot={{ r: 6, fill: color, stroke: '#1c2026', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
