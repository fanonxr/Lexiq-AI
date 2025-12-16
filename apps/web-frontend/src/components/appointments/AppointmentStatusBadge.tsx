"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { AppointmentStatus } from "./AppointmentList";

/**
 * Appointment Status Badge Component
 * 
 * Status badge for appointments with specific styling for each status type.
 * 
 * @example
 * ```tsx
 * <AppointmentStatusBadge status="confirmed" />
 * <AppointmentStatusBadge status="proposed" />
 * <AppointmentStatusBadge status="rescheduled" />
 * ```
 */

export interface AppointmentStatusBadgeProps {
  /**
   * Appointment status
   */
  status: AppointmentStatus;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get status badge styling based on status
 */
function getStatusBadgeStyles(status: AppointmentStatus): string {
  switch (status) {
    case "confirmed":
      // Solid Black
      return "bg-zinc-900 text-white border-transparent dark:bg-zinc-50 dark:text-zinc-900";
    case "proposed":
      // Gray Outline
      return "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700";
    case "rescheduled":
      // Orange
      return "bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800";
    case "cancelled":
      // Red
      return "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800";
    default:
      return "bg-zinc-100 text-zinc-600 border-zinc-200";
  }
}

/**
 * Format status text for display
 */
function formatStatusText(status: AppointmentStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

/**
 * Appointment Status Badge Component
 * 
 * Features:
 * - Status variants:
 *   - Confirmed: Solid Black (bg-zinc-900 text-white)
 *   - Proposed: Gray Outline (bg-zinc-100 text-zinc-600 border-zinc-200)
 *   - Rescheduled: Orange (text-orange-600 border-orange-200)
 *   - Cancelled: Red (text-red-600 border-red-200)
 */
export function AppointmentStatusBadge({
  status,
  className,
}: AppointmentStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        getStatusBadgeStyles(status),
        className
      )}
    >
      {formatStatusText(status)}
    </span>
  );
}

