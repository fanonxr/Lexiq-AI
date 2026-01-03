"use client";

import * as React from "react";
import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Edit, X, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import { logger } from "@/lib/logger";
import { AppointmentStatusBadge } from "./AppointmentStatusBadge";

/**
 * Appointment List Component
 * 
 * Dense table displaying appointments in a Linear-style issues list.
 * Features avatars, status badges, and hidden action buttons on hover.
 * 
 * @example
 * ```tsx
 * <AppointmentList
 *   appointments={appointments}
 *   onEdit={(id) => handleEdit(id)}
 *   onCancel={(id) => handleCancel(id)}
 * />
 * ```
 */

/**
 * Appointment status type
 */
export type AppointmentStatus = "confirmed" | "proposed" | "rescheduled" | "cancelled";

/**
 * Appointment type
 */
export type AppointmentType = "consultation" | "follow-up" | "meeting" | "other";

/**
 * Appointment data
 */
export interface Appointment {
  /**
   * Unique appointment identifier
   */
  id: string;
  /**
   * Client name
   */
  clientName: string;
  /**
   * Client email (optional, for avatar fallback)
   */
  clientEmail?: string;
  /**
   * Appointment date and time
   */
  dateTime: Date;
  /**
   * Appointment type
   */
  type: AppointmentType;
  /**
   * Appointment status
   */
  status: AppointmentStatus;
  /**
   * Optional description or notes
   */
  description?: string;
}

export interface AppointmentListProps {
  /**
   * Array of appointments
   */
  appointments: Appointment[];
  /**
   * Callback when edit action is clicked
   */
  onEdit?: (appointmentId: string) => void;
  /**
   * Callback when cancel action is clicked
   */
  onCancel?: (appointmentId: string) => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get initials from name
 */
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
}

/**
 * Get avatar background color based on name
 */
function getAvatarColor(name: string): string {
  const colors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-purple-500",
    "bg-pink-500",
    "bg-orange-500",
    "bg-indigo-500",
    "bg-teal-500",
    "bg-red-500",
  ];
  const index = name.charCodeAt(0) % colors.length;
  return colors[index];
}

/**
 * Format appointment type
 */
function formatAppointmentType(type: AppointmentType): string {
  switch (type) {
    case "consultation":
      return "Consultation";
    case "follow-up":
      return "Follow-up";
    case "meeting":
      return "Meeting";
    default:
      return "Other";
  }
}


/**
 * Format date/time for display
 */
function formatDateTime(dateTime: Date): { date: string; time: string } {
  return {
    date: format(dateTime, "MMM d, yyyy"),
    time: format(dateTime, "h:mm a"),
  };
}

/**
 * Appointment List Component
 * 
 * Features:
 * - Dense table (Linear-style issues list)
 * - Columns: Client Name (with avatar), Date/Time, Type, Status, Actions
 * - Avatar: Circle with client initials
 * - Hidden Actions column (appears on row hover)
 * - Copy details on Date/Time click
 */
export function AppointmentList({
  appointments,
  onEdit,
  onCancel,
  className,
}: AppointmentListProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [hoveredRowId, setHoveredRowId] = useState<string | null>(null);

  const handleCopyDateTime = async (appointment: Appointment) => {
    const { date, time } = formatDateTime(appointment.dateTime);
    const text = `${appointment.clientName} - ${date} at ${time}`;
    
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(appointment.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      logger.error("Failed to copy appointment text", err instanceof Error ? err : new Error(String(err)), { appointmentId: appointment.id });
    }
  };

  if (appointments.length === 0) {
    return (
      <div className={cn("rounded-lg border border-zinc-200 bg-white p-8 text-center dark:border-zinc-800 dark:bg-zinc-900", className)}>
        <p className="text-sm text-muted-foreground">
          No appointments scheduled. Appointments will appear here when synced from your calendar.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Client</TableHead>
            <TableHead>Date/Time</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-[100px] text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {appointments.map((appointment) => {
            const { date, time } = formatDateTime(appointment.dateTime);
            const initials = getInitials(appointment.clientName);
            const avatarColor = getAvatarColor(appointment.clientName);
            const isHovered = hoveredRowId === appointment.id;
            const isCopied = copiedId === appointment.id;

            return (
              <TableRow
                key={appointment.id}
                onMouseEnter={() => setHoveredRowId(appointment.id)}
                onMouseLeave={() => setHoveredRowId(null)}
                className="group"
              >
                {/* Client Name with Avatar */}
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium text-white",
                        avatarColor
                      )}
                    >
                      {initials}
                    </div>
                    <span className="font-medium text-foreground">
                      {appointment.clientName}
                    </span>
                  </div>
                </TableCell>

                {/* Date/Time (clickable to copy) */}
                <TableCell>
                  <button
                    onClick={() => handleCopyDateTime(appointment)}
                    className={cn(
                      "flex flex-col items-start gap-0.5 text-left hover:text-primary transition-colors",
                      "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm"
                    )}
                    aria-label={`Copy appointment details for ${appointment.clientName} on ${date} at ${time}`}
                    title="Click to copy appointment details"
                  >
                    <span className="text-sm text-foreground">{date}</span>
                    <span className="text-xs text-muted-foreground">{time}</span>
                    {isCopied && (
                      <span className="flex items-center gap-1 text-xs text-green-600">
                        <Check className="h-3 w-3" />
                        Copied
                      </span>
                    )}
                  </button>
                </TableCell>

                {/* Type */}
                <TableCell className="text-muted-foreground">
                  {formatAppointmentType(appointment.type)}
                </TableCell>

                {/* Status */}
                <TableCell>
                  <AppointmentStatusBadge status={appointment.status} />
                </TableCell>

                {/* Actions (hidden until hover) */}
                <TableCell className="text-right">
                  <div
                    className={cn(
                      "flex items-center justify-end gap-2 transition-opacity",
                      isHovered ? "opacity-100" : "opacity-0"
                    )}
                    role="group"
                    aria-label={`Actions for ${appointment.clientName}`}
                  >
                    {onEdit && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onEdit(appointment.id)}
                        aria-label={`Edit appointment with ${appointment.clientName}`}
                        title="Edit"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                    )}
                    {onCancel && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => onCancel(appointment.id)}
                        aria-label={`Cancel appointment with ${appointment.clientName}`}
                        title="Cancel"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

