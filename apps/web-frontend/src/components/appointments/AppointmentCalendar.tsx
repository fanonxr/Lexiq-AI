"use client";

import * as React from "react";
import { useState } from "react";
import { DayPicker } from "react-day-picker";
import { format, isSameDay } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Appointment } from "./AppointmentList";
import type { IntegrationType } from "./IntegrationHealthCard";

import "react-day-picker/dist/style.css";

/**
 * Appointment Calendar Component
 * 
 * Calendar view displaying appointments from Outlook and Google Calendar
 * in a unified monthly calendar. Shows appointments on their respective dates
 * with indicators for which calendar they come from.
 * 
 * @example
 * ```tsx
 * <AppointmentCalendar
 *   appointments={appointments}
 *   onDateSelect={(date) => handleDateSelect(date)}
 * />
 * ```
 */

export interface AppointmentCalendarProps {
  /**
   * Array of appointments to display
   */
  appointments: Appointment[];
  /**
   * Map of appointment IDs to their source calendar (outlook/google)
   */
  appointmentSources?: Record<string, IntegrationType>;
  /**
   * Callback when a date is selected
   */
  onDateSelect?: (date: Date) => void;
  /**
   * Currently selected date
   */
  selectedDate?: Date;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Appointment Calendar Component
 * 
 * Features:
 * - Monthly calendar view
 * - Displays appointments on dates
 * - Shows source calendar (Outlook/Google)
 * - Click to select date
 * - Unified view of both calendars
 */
export function AppointmentCalendar({
  appointments,
  appointmentSources = {},
  onDateSelect,
  selectedDate,
  className,
}: AppointmentCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date());

  // Group appointments by date for quick lookup
  const appointmentsByDate = React.useMemo(() => {
    const grouped: Record<string, Appointment[]> = {};
    if (appointments && Array.isArray(appointments)) {
      appointments.forEach((apt) => {
        const dateKey = format(
          typeof apt.dateTime === 'string' ? new Date(apt.dateTime) : apt.dateTime,
          "yyyy-MM-dd"
        );
        if (!grouped[dateKey]) {
          grouped[dateKey] = [];
        }
        grouped[dateKey].push(apt);
      });
    }
    return grouped;
  }, [appointments]);

  // Create modifiers for days with appointments
  const modifiers = React.useMemo(() => {
    const hasAppointments: Date[] = [];
    Object.keys(appointmentsByDate).forEach((dateKey) => {
      const date = new Date(dateKey);
      if (!isNaN(date.getTime())) {
        hasAppointments.push(date);
      }
    });
    return { hasAppointments };
  }, [appointmentsByDate]);

  const handleDayClick = (date: Date | undefined) => {
    if (date) {
      onDateSelect?.(date);
    }
  };

  const handleMonthChange = (date: Date) => {
    setCurrentMonth(date);
  };

  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Calendar</CardTitle>
      </CardHeader>
      <CardContent>
        <DayPicker
          mode="single"
          selected={selectedDate}
          onSelect={handleDayClick}
          month={currentMonth}
          onMonthChange={handleMonthChange}
          modifiers={modifiers}
          className="p-3"
          classNames={{
            months: "flex flex-col space-y-4",
            month: "space-y-4",
            caption: "flex justify-center pt-1 relative items-center",
            caption_label: "text-sm font-medium",
            nav: "space-x-1 flex items-center",
            nav_button: cn(
              "h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100",
              "border border-border rounded-md",
              "hover:bg-muted transition-colors"
            ),
            nav_button_previous: "absolute left-1",
            nav_button_next: "absolute right-1",
            table: "w-full border-collapse space-y-1",
            head_row: "flex",
            head_cell: "text-muted-foreground rounded-md w-9 font-normal text-[0.8rem]",
            row: "flex w-full mt-2",
            cell: "h-9 w-9 text-center text-sm p-0 relative focus-within:relative focus-within:z-20",
            day: cn(
              "h-9 w-9 p-0 font-normal aria-selected:opacity-100",
              "rounded-md hover:bg-muted transition-colors",
              "aria-selected:bg-primary aria-selected:text-primary-foreground"
            ),
            day_selected: "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground",
            day_today: "bg-muted text-foreground font-semibold",
            day_outside: "text-muted-foreground opacity-50",
            day_disabled: "text-muted-foreground opacity-50",
            day_range_middle: "aria-selected:bg-muted aria-selected:text-foreground",
            day_hidden: "invisible",
            day_hasAppointments: "relative after:content-[''] after:absolute after:bottom-1 after:left-1/2 after:-translate-x-1/2 after:h-1.5 after:w-1.5 after:rounded-full after:bg-primary",
          }}
          modifiersClassNames={{
            hasAppointments: "day_hasAppointments",
          }}
          components={{
            IconLeft: () => <ChevronLeft className="h-4 w-4" />,
            IconRight: () => <ChevronRight className="h-4 w-4" />,
          }}
        />

        {/* Legend */}
        <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground border-t border-zinc-200 dark:border-zinc-800 pt-4">
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-blue-500" />
            <span>Outlook</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span>Google Calendar</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
