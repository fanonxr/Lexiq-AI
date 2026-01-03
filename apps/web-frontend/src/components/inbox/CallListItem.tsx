"use client";

import * as React from "react";
import { formatDistanceToNow } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Call List Item Component
 * 
 * Displays a call in the inbox list with caller name, status badge,
 * summary text, and relative timestamp. Supports selected state with
 * visual indicators.
 * 
 * @example
 * ```tsx
 * <CallListItem
 *   call={{ 
 *     id: "1",
 *     callerName: "John Doe",
 *     status: "new_client",
 *     summary: "Inquiry about estate planning services...",
 *     timestamp: new Date(),
 *   }}
 *   isSelected={false}
 *   onClick={() => logger.debug("Call selected", { callId: "1" })}
 * />
 * ```
 */

/**
 * Call status type
 */
export type CallStatus = 
  | "new_client" 
  | "lead" 
  | "existing_client" 
  | "spam" 
  | "unread" 
  | "archived";

/**
 * Call object interface
 */
export interface Call {
  /**
   * Unique identifier for the call
   */
  id: string;
  /**
   * Caller's name or phone number
   */
  callerName: string;
  /**
   * Call status for badge display
   */
  status: CallStatus;
  /**
   * Summary/transcript preview text (will be truncated)
   */
  summary: string;
  /**
   * Call timestamp
   */
  timestamp: Date;
  /**
   * Optional phone number
   */
  phoneNumber?: string;
  /**
   * Optional duration in seconds
   */
  duration?: number;
  /**
   * Optional metadata
   */
  metadata?: Record<string, unknown>;
}

export interface CallListItemProps {
  /**
   * Call data to display
   */
  call: Call;
  /**
   * Whether this call is currently selected
   */
  isSelected: boolean;
  /**
   * Click handler for selection
   */
  onClick: () => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get status badge label and variant
 */
function getStatusBadge(status: CallStatus): { label: string; variant: "default" | "secondary" | "outline" } {
  switch (status) {
    case "new_client":
      return { label: "New Client", variant: "secondary" };
    case "lead":
      return { label: "Lead", variant: "default" };
    case "existing_client":
      return { label: "Client", variant: "outline" };
    case "spam":
      return { label: "Spam", variant: "outline" };
    case "unread":
      return { label: "Unread", variant: "default" };
    case "archived":
      return { label: "Archived", variant: "outline" };
    default:
      return { label: "Call", variant: "outline" };
  }
}

/**
 * Format relative time (e.g., "10m ago", "2h ago")
 */
function formatRelativeTime(date: Date): string {
  return formatDistanceToNow(date, { addSuffix: true });
}

/**
 * Call List Item Component
 * 
 * Two-line layout:
 * - Top: Caller Name + Status Badge
 * - Bottom: Truncated summary + Relative timestamp
 * 
 * Selected state: bg-muted with black left-border accent
 */
export const CallListItem = React.memo(function CallListItem({
  call,
  isSelected,
  onClick,
  className,
}: CallListItemProps) {
  const statusBadge = getStatusBadge(call.status);

  return (
    <button
      onClick={onClick}
      className={cn(
        // Base styles
        "w-full text-left p-4 transition-colors",
        "border-l-4 border-transparent",
        // Hover state
        "hover:bg-muted/50",
        // Selected state: bg-muted with black left-border accent
        isSelected && "bg-muted border-l-primary",
        // Focus state - visible focus indicator for keyboard navigation
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        className
      )}
      aria-selected={isSelected}
      aria-label={`${call.callerName}, ${statusBadge.label}, ${formatRelativeTime(call.timestamp)}`}
      role="option"
      tabIndex={isSelected ? 0 : -1}
    >
      <div className="flex flex-col gap-2">
        {/* Top line: Caller Name + Status Badge */}
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-foreground truncate">
            {call.callerName}
          </span>
          <Badge variant={statusBadge.variant} className="flex-shrink-0">
            {statusBadge.label}
          </Badge>
        </div>

        {/* Bottom line: Truncated summary + Relative timestamp */}
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground truncate flex-1">
            {call.summary}
          </p>
          <span className="text-xs text-muted-foreground flex-shrink-0">
            {formatRelativeTime(call.timestamp)}
          </span>
        </div>
      </div>
    </button>
  );
});

