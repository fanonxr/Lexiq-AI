"use client"

import * as React from "react"
import { formatDistanceToNow } from "date-fns"
import { cn } from "@/lib/utils"

/**
 * Activity List Component
 * 
 * Displays a compact list of recent activity items with icons,
 * text, and relative timestamps. Used in the dashboard overview.
 * 
 * @example
 * ```tsx
 * <ActivityList
 *   items={[
 *     {
 *       id: "1",
 *       icon: <User className="h-4 w-4" />,
 *       text: "New Client Intake: John Doe",
 *       timestamp: new Date(),
 *       onClick: () => console.log("Clicked")
 *     }
 *   ]}
 * />
 * ```
 */

export interface ActivityListItem {
  /**
   * Unique identifier for the item
   */
  id: string
  /**
   * Icon element (from Lucide React)
   */
  icon: React.ReactNode
  /**
   * Activity text (will be truncated if too long)
   */
  text: string
  /**
   * Timestamp for the activity
   */
  timestamp: Date
  /**
   * Optional click handler
   */
  onClick?: () => void
}

export interface ActivityListProps {
  /**
   * Array of activity items to display
   */
  items: ActivityListItem[]
  /**
   * Maximum number of items to display
   * @default 10
   */
  maxItems?: number
  /**
   * Additional CSS classes
   */
  className?: string
}

/**
 * Format relative time (e.g., "10m ago", "2h ago")
 */
const formatRelativeTime = (date: Date): string => {
  return formatDistanceToNow(date, { addSuffix: true })
}

export function ActivityList({
  items,
  maxItems = 10,
  className,
}: ActivityListProps) {
  const displayedItems = items.slice(0, maxItems)

  if (displayedItems.length === 0) {
    return (
      <div className={cn("text-sm text-muted-foreground p-4", className)}>
        No recent activity
      </div>
    )
  }

  return (
    <div className={cn("space-y-1", className)}>
      {displayedItems.map((item) => (
        <button
          key={item.id}
          onClick={item.onClick}
          disabled={!item.onClick}
          className={cn(
            "w-full flex items-start gap-3 p-3 rounded-md",
            "text-left transition-colors",
            "hover:bg-muted/50",
            item.onClick && "cursor-pointer",
            !item.onClick && "cursor-default",
            // Focus state - visible focus indicator for keyboard navigation
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
          aria-label={`${item.text}, ${formatRelativeTime(item.timestamp)}`}
        >
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5 text-muted-foreground">
            {item.icon}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Text with truncation */}
            <p className="text-sm text-foreground truncate">
              {item.text}
            </p>
            {/* Relative timestamp */}
            <p className="text-xs text-muted-foreground mt-0.5">
              {formatRelativeTime(item.timestamp)}
            </p>
          </div>
        </button>
      ))}
    </div>
  )
}

