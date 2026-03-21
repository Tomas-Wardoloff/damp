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
}

export function BiometricChart({
  data,
  metricName = "Temperature",
  normalRange,
  className,
  ...props
}: BiometricChartProps) {
  const dataValues = data?.map(d => d.value) || []
  const dataMin = dataValues.length > 0 ? Math.min(...dataValues) : 0
  const dataMax = dataValues.length > 0 ? Math.max(...dataValues) : 0

  const minVal = Math.floor(Math.min(dataMin, normalRange[0] - 1.0))
  const maxVal = Math.ceil(Math.max(dataMax, normalRange[1] + 1.0))

  const GREEN = "#92f592"
  const YELLOW = "#ffb95f"
  const RED = "#fa8f82"

  const getOffset = (val: number) => {
    if (dataMax === dataMin) {
      return val > dataMax ? 0 : val < dataMin ? 100 : 50;
    }
    const percentage = ((dataMax - val) / (dataMax - dataMin)) * 100
    return Math.max(0, Math.min(100, percentage))
  }

  const warningHigh = normalRange[1] + 0.5
  const warningLow = normalRange[0] - 0.5

  return (
    <div className={cn("bg-surface-container p-6 rounded-lg border border-outline-variant", className)} {...props}>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-headline-md font-display mb-1">{metricName}</h3>
          <p className="text-label-sm font-mono text-on-surface-variant flex gap-2 items-center">
            <span>Rango Normal: {normalRange[0]} - {normalRange[1]}</span>
          </p>
        </div>
      </div>

      {!data || data.length === 0 ? (
        <div className="h-[300px] w-full flex items-center justify-center border-2 border-dashed border-outline-variant/40 rounded-lg">
          <p className="text-on-surface-variant font-mono text-label-md">No hay datos registrados</p>
        </div>
      ) : (
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
                  <stop offset={`${getOffset(maxVal)}%`} stopColor={RED} />
                  <stop offset={`${getOffset(warningHigh)}%`} stopColor={RED} />

                  <stop offset={`${getOffset(warningHigh)}%`} stopColor={YELLOW} />
                  <stop offset={`${getOffset(normalRange[1])}%`} stopColor={YELLOW} />

                  <stop offset={`${getOffset(normalRange[1])}%`} stopColor={GREEN} />
                  <stop offset={`${getOffset(normalRange[0])}%`} stopColor={GREEN} />

                  <stop offset={`${getOffset(normalRange[0])}%`} stopColor={YELLOW} />
                  <stop offset={`${getOffset(warningLow)}%`} stopColor={YELLOW} />

                  <stop offset={`${getOffset(warningLow)}%`} stopColor={RED} />
                  <stop offset={`${getOffset(minVal)}%`} stopColor={RED} />
                </linearGradient>
              </defs>

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
                labelStyle={{ color: '#9aa0a6', fontFamily: 'var(--font-space-grotesk)' }}
              />

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
                stroke="url(#splitColor)"
                strokeWidth={3}
                dot={{ r: 0 }}
                activeDot={{ r: 6, fill: GREEN, stroke: '#1c2026', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}