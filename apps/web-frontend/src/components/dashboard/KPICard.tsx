"use client"

import * as React from "react"
import { ArrowUp, ArrowDown } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { cn } from "@/lib/utils"

/**
 * KPI Card Component
 * 
 * Displays key performance indicators with large monospaced numbers,
 * trend indicators, and hover effects. Used in the dashboard overview.
 * 
 * @example
 * ```tsx
 * <KPICard
 *   title="Billable Hours Saved"
 *   value={1247}
 *   trend={{ direction: "up", percentage: 12 }}
 * />
 * ```
 */

export interface KPICardProps {
  /**
   * Title of the KPI metric
   */
  title: string
  /**
   * Current value (can be number or formatted string)
   */
  value: number | string
  /**
   * Trend information showing change from previous period
   */
  trend?: {
    direction: "up" | "down"
    percentage: number
    label?: string // e.g., "from last week"
  }
  /**
   * Optional formatter function for numeric values
   */
  formatValue?: (value: number) => string
  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Default formatter for large numbers
 */
const defaultFormatter = (value: number): string => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toLocaleString()
}

export const KPICard = React.memo(function KPICard({
  title,
  value,
  trend,
  formatValue = defaultFormatter,
  className,
}: KPICardProps) {
  // Format the value
  const displayValue = typeof value === "number" ? formatValue(value) : value

  return (
    <Card
      hoverable
      className={cn("transition-colors", className)}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {/* Large monospaced number */}
          <div className="text-3xl font-semibold tracking-tight mono-number">
            {displayValue}
          </div>
          
          {/* Trend indicator */}
          {trend && (
            <div className="flex items-center gap-1 text-sm">
              {trend.direction === "up" ? (
                <>
                  <ArrowUp className="h-3.5 w-3.5 text-green-600" />
                  <span className="text-green-600">
                    {trend.percentage}%
                  </span>
                </>
              ) : (
                <>
                  <ArrowDown className="h-3.5 w-3.5 text-red-600" />
                  <span className="text-red-600">
                    {trend.percentage}%
                  </span>
                </>
              )}
              {trend.label && (
                <span className="text-muted-foreground">
                  {trend.label}
                </span>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
});

