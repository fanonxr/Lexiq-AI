"use client";

import * as React from "react";
import { useState, useMemo } from "react";
import { format, startOfWeek, addDays, addWeeks, subWeeks, isSameDay, isToday, parseISO } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Appointment } from "./AppointmentList";
import type { IntegrationType } from "./IntegrationHealthCard";

/**
 * Weekly Calendar View Component
 * 
 * Displays a weekly calendar view showing all appointments and events
 * from Outlook calendar and appointments booked through the application.
 * 
 * Features:
 * - Week view (7 days)
 * - Shows all appointments/events for the week
 * - Differentiates between Outlook events and app-booked appointments
 * - Navigation between weeks
 * - Click to view appointment details
 */

export interface WeeklyCalendarViewProps {
  /**
   * Array of appointments to display
   */
  appointments: Appointment[];
  /**
   * Map of appointment IDs to their source calendar (outlook/google)
   */
  appointmentSources?: Record<string, IntegrationType>;
  /**
   * Callback when an appointment is clicked
   */
  onAppointmentClick?: (appointment: Appointment) => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get the start of the week (Monday)
 */
function getWeekStart(date: Date): Date {
  return startOfWeek(date, { weekStartsOn: 1 }); // Monday
}

/**
 * Get all days in a week
 */
function getWeekDays(weekStart: Date): Date[] {
  return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
}

/**
 * Group appointments by day
 */
function groupAppointmentsByDay(appointments: Appointment[]): Record<string, Appointment[]> {
  const grouped: Record<string, Appointment[]> = {};
  
  if (!appointments || !Array.isArray(appointments)) {
    return grouped;
  }

  appointments.forEach((apt) => {
    const date = typeof apt.dateTime === 'string' ? parseISO(apt.dateTime) : apt.dateTime;
    const dateKey = format(date, "yyyy-MM-dd");
    
    if (!grouped[dateKey]) {
      grouped[dateKey] = [];
    }
    grouped[dateKey].push(apt);
  });

  // Sort appointments within each day by time
  Object.keys(grouped).forEach((dateKey) => {
    grouped[dateKey].sort((a, b) => {
      const dateA = typeof a.dateTime === 'string' ? parseISO(a.dateTime) : a.dateTime;
      const dateB = typeof b.dateTime === 'string' ? parseISO(b.dateTime) : b.dateTime;
      return dateA.getTime() - dateB.getTime();
    });
  });

  return grouped;
}

/**
 * Format time for display
 */
function formatTime(date: Date): string {
  return format(date, "h:mm a");
}

export function WeeklyCalendarView({
  appointments,
  appointmentSources = {},
  onAppointmentClick,
  className,
}: WeeklyCalendarViewProps) {
  const [currentWeekStart, setCurrentWeekStart] = useState(() => getWeekStart(new Date()));
  
  const weekDays = useMemo(() => getWeekDays(currentWeekStart), [currentWeekStart]);
  const appointmentsByDay = useMemo(() => groupAppointmentsByDay(appointments), [appointments]);

  const handlePreviousWeek = () => {
    setCurrentWeekStart((prev) => subWeeks(prev, 1));
  };

  const handleNextWeek = () => {
    setCurrentWeekStart((prev) => addWeeks(prev, 1));
  };

  const handleToday = () => {
    setCurrentWeekStart(getWeekStart(new Date()));
  };

  const weekRange = useMemo(() => {
    const start = weekDays[0];
    const end = weekDays[6];
    return `${format(start, "MMM d")} - ${format(end, "MMM d, yyyy")}`;
  }, [weekDays]);

  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">Weekly Calendar</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviousWeek}
              className="h-8 w-8 p-0"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleToday}
              className="h-8 px-3 text-xs"
            >
              Today
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextWeek}
              className="h-8 w-8 p-0"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{weekRange}</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-2">
            {weekDays.map((day, index) => {
              const dayName = format(day, "EEE");
              const dayNumber = format(day, "d");
              const isCurrentDay = isToday(day);
              const dateKey = format(day, "yyyy-MM-dd");
              const dayAppointments = appointmentsByDay[dateKey] || [];

              return (
                <div
                  key={index}
                  className={cn(
                    "text-center pb-2 border-b border-zinc-200 dark:border-zinc-800",
                    isCurrentDay && "border-primary"
                  )}
                >
                  <div
                    className={cn(
                      "text-xs font-medium text-muted-foreground mb-1",
                      isCurrentDay && "text-primary font-semibold"
                    )}
                  >
                    {dayName}
                  </div>
                  <div
                    className={cn(
                      "text-lg font-semibold",
                      isCurrentDay
                        ? "text-primary"
                        : "text-zinc-900 dark:text-zinc-100"
                    )}
                  >
                    {dayNumber}
                  </div>
                  {dayAppointments.length > 0 && (
                    <div className="mt-1 text-xs text-muted-foreground">
                      {dayAppointments.length} {dayAppointments.length === 1 ? "event" : "events"}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Appointments grid */}
          <div className="grid grid-cols-7 gap-2 min-h-[400px]">
            {weekDays.map((day, dayIndex) => {
              const dateKey = format(day, "yyyy-MM-dd");
              const dayAppointments = appointmentsByDay[dateKey] || [];
              const isCurrentDay = isToday(day);

              return (
                <div
                  key={dayIndex}
                  className={cn(
                    "border border-zinc-200 dark:border-zinc-800 rounded-lg p-2 space-y-1.5 min-h-[400px]",
                    isCurrentDay && "border-primary bg-primary/5"
                  )}
                >
                  {dayAppointments.length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center pt-2">
                      No events
                    </div>
                  ) : (
                    dayAppointments.map((apt, aptIndex) => {
                      const aptDate = typeof apt.dateTime === 'string' ? parseISO(apt.dateTime) : apt.dateTime;
                      const source = appointmentSources[apt.id] || "outlook";
                      const isOutlook = source === "outlook";
                      const isGoogle = source === "google";

                      return (
                        <div
                          key={aptIndex}
                          onClick={() => onAppointmentClick?.(apt)}
                          className={cn(
                            "p-2 rounded-md text-xs cursor-pointer transition-colors",
                            "hover:opacity-90 border-l-2",
                            isOutlook && "bg-blue-50 dark:bg-blue-950/20 border-blue-500",
                            isGoogle && "bg-green-50 dark:bg-green-950/20 border-green-500",
                            !isOutlook && !isGoogle && "bg-zinc-100 dark:bg-zinc-800 border-zinc-400"
                          )}
                        >
                          <div className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                            {apt.description || apt.clientName || "Untitled Event"}
                          </div>
                          <div className="text-muted-foreground mt-0.5">
                            {formatTime(aptDate)}
                          </div>
                          {apt.clientName && apt.description && apt.clientName !== apt.description && (
                            <div className="text-muted-foreground mt-0.5 truncate">
                              {apt.clientName}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground border-t border-zinc-200 dark:border-zinc-800 pt-4">
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded border-l-2 border-blue-500 bg-blue-50 dark:bg-blue-950/20" />
              <span>Outlook Calendar</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded border-l-2 border-green-500 bg-green-50 dark:bg-green-950/20" />
              <span>Google Calendar</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-3 w-3 rounded border-l-2 border-zinc-400 bg-zinc-100 dark:bg-zinc-800" />
              <span>App Booked</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

