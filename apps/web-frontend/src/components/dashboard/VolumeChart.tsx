"use client"

import * as React from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts"
import { format, parseISO } from "date-fns"
import { cn } from "@/lib/utils"

/**
 * Volume Chart Component
 * 
 * Displays volume data over time using an area chart.
 * Features gradient fill, minimal axes, and custom tooltip styling.
 * 
 * @example
 * ```tsx
 * <VolumeChart
 *   data={[
 *     { date: "2024-01-01", value: 100 },
 *     { date: "2024-01-02", value: 150 },
 *   ]}
 *   height={300}
 * />
 * ```
 */

export interface VolumeChartDataPoint {
  date: string
  value: number
}

export interface VolumeChartProps {
  /**
   * Chart data points
   */
  data: VolumeChartDataPoint[]
  /**
   * Chart height in pixels
   * @default 300
   */
  height?: number
  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Custom tooltip component with black background and white text
 * Instant snap to data point with smooth animations disabled
 */
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const date = parseISO(label)
    return (
      <div className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 shadow-lg animate-in fade-in-0 zoom-in-95 duration-0">
        <p className="text-xs text-white/70 mb-1">
          {format(date, "MMM dd, yyyy")}
        </p>
        <p className="text-sm font-semibold text-white">
          {payload[0].value.toLocaleString()}
        </p>
      </div>
    )
  }
  return null
}

/**
 * Custom label formatter for X-axis dates
 */
const formatXAxisLabel = (tickItem: string) => {
  try {
    const date = parseISO(tickItem)
    return format(date, "MMM dd")
  } catch {
    return tickItem
  }
}

export function VolumeChart({
  data,
  height = 300,
  className,
}: VolumeChartProps) {
  // Create gradient definition for the area fill
  const gradientId = React.useId()
  const [activeIndex, setActiveIndex] = React.useState<number | null>(null)

  // Handle mouse move for crosshair
  const handleMouseMove = React.useCallback((state: any) => {
    if (state && state.activeTooltipIndex !== undefined) {
      setActiveIndex(state.activeTooltipIndex)
    }
  }, [])

  const handleMouseLeave = React.useCallback(() => {
    setActiveIndex(null)
  }, [])

  // Get active data point for crosshair
  const activeDataPoint = activeIndex !== null ? data[activeIndex] : null

  return (
    <div className={cn("w-full relative", className)}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={data}
          margin={{
            top: 10,
            right: 10,
            left: 0,
            bottom: 0,
          }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#09090b" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#09090b" stopOpacity={0} />
            </linearGradient>
          </defs>
          
          {/* Minimal grid - only vertical lines, no horizontal */}
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#e4e4e7"
            vertical={true}
            horizontal={false}
          />
          
          {/* X-axis - show dates */}
          <XAxis
            dataKey="date"
            tickFormatter={formatXAxisLabel}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#71717a", fontSize: 12 }}
            interval="preserveStartEnd"
          />
          
          {/* Y-axis - hide lines, show values */}
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#71717a", fontSize: 12 }}
            width={60}
          />
          
          {/* Vertical crosshair line on hover */}
          {activeDataPoint && (
            <ReferenceLine
              x={activeDataPoint.date}
              stroke="#71717a"
              strokeWidth={1}
              strokeDasharray="2 2"
              opacity={0.5}
            />
          )}
          
          {/* Custom tooltip with instant snap (no animation) */}
          <Tooltip
            content={<CustomTooltip />}
            animationDuration={0}
            cursor={false}
          />
          
          {/* Area with gradient fill and zinc-900 stroke */}
          <Area
            type="monotone"
            dataKey="value"
            stroke="#09090b"
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{
              r: 4,
              fill: "#09090b",
              stroke: "#ffffff",
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

