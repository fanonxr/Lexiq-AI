"use client"

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

/**
 * Status Indicator Component
 * 
 * Displays system status with an animated pulse dot.
 * Used in the dashboard header to show system online/offline state.
 * 
 * @example
 * ```tsx
 * <StatusIndicator status="online" />
 * <StatusIndicator status="offline" />
 * ```
 */

export type SystemStatus = "online" | "offline"

export interface StatusIndicatorProps {
  /**
   * System status
   * @default "online"
   */
  status?: SystemStatus
  /**
   * Additional CSS classes
   */
  className?: string
}

export function StatusIndicator({
  status = "online",
  className,
}: StatusIndicatorProps) {
  const isOnline = status === "online"

  return (
    <Badge
      variant="outline"
      pulse={isOnline}
      pulseColor={isOnline ? "green" : "red"}
      className={cn("gap-2", className)}
    >
      {isOnline ? "System Online" : "System Offline"}
    </Badge>
  )
}

