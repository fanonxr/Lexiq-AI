"use client";

import { useState, useMemo, useCallback } from "react";
import { IntegrationHealthCard, type IntegrationType } from "@/components/appointments/IntegrationHealthCard";
import { AppointmentList, type Appointment } from "@/components/appointments/AppointmentList";
import { AppointmentListSkeleton } from "@/components/appointments/AppointmentListSkeleton";
import { AppointmentCalendar } from "@/components/appointments/AppointmentCalendar";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

/**
 * Appointments Page
 * 
 * Displays calendar appointments synced from Outlook/Google Calendar.
 * Features integration health status and appointment list.
 * 
 * Layout:
 * - Integration Health Card (top)
 * - Appointment List (below)
 */
export default function AppointmentsPage() {
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSynced, setLastSynced] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  // Loading state - will be replaced with actual hook loading states
  const [isLoadingAppointments, setIsLoadingAppointments] = useState(false);
  // Error state - will be replaced with actual hook error states
  const [appointmentsError, setAppointmentsError] = useState<Error | null>(null);

  // Mock appointments data
  const mockAppointments: Appointment[] = useMemo(
    () => [
      {
        id: "1",
        clientName: "John Smith",
        clientEmail: "john.smith@example.com",
        dateTime: new Date("2024-12-20T14:30:00"),
        type: "consultation",
        status: "confirmed",
        description: "Initial consultation for estate planning",
      },
      {
        id: "2",
        clientName: "Sarah Johnson",
        clientEmail: "sarah.j@example.com",
        dateTime: new Date("2024-12-21T10:00:00"),
        type: "follow-up",
        status: "proposed",
        description: "Follow-up on contract review",
      },
      {
        id: "3",
        clientName: "Michael Chen",
        clientEmail: "m.chen@example.com",
        dateTime: new Date("2024-12-22T15:45:00"),
        type: "consultation",
        status: "rescheduled",
        description: "Business incorporation consultation",
      },
      {
        id: "4",
        clientName: "Emily Davis",
        clientEmail: "emily.davis@example.com",
        dateTime: new Date("2024-12-23T09:30:00"),
        type: "meeting",
        status: "confirmed",
        description: "Team meeting",
      },
      {
        id: "5",
        clientName: "Robert Williams",
        clientEmail: "r.williams@example.com",
        dateTime: new Date("2024-12-24T11:00:00"),
        type: "consultation",
        status: "cancelled",
        description: "Cancelled consultation",
      },
    ],
    []
  );

  const [appointments, setAppointments] = useState<Appointment[]>(mockAppointments);

  // Map appointments to their source calendar (mock data - in production this would come from API)
  const appointmentSources = useMemo<Record<string, IntegrationType>>(() => {
    const sources: Record<string, IntegrationType> = {};
    appointments.forEach((apt, index) => {
      // Alternate between outlook and google for demo
      sources[apt.id] = index % 2 === 0 ? "outlook" : "google";
    });
    return sources;
  }, [appointments]);

  /**
   * Handle refresh/sync
   */
  const handleRefresh = useCallback(async () => {
    setIsSyncing(true);
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    // Update last synced time
    setLastSynced(new Date());
    
    // In real implementation, this would fetch new appointments
    // For now, we'll just update the last synced time
    console.log("Syncing appointments...");
    
    setIsSyncing(false);
  }, []);

  /**
   * Handle edit appointment
   */
  const handleEdit = useCallback((appointmentId: string) => {
    console.log("Edit appointment:", appointmentId);
    // In real implementation, this would open an edit modal or navigate to edit page
  }, []);

  /**
   * Handle cancel appointment
   */
  const handleCancel = useCallback((appointmentId: string) => {
    console.log("Cancel appointment:", appointmentId);
    // In real implementation, this would show a confirmation dialog and cancel the appointment
    setAppointments((prev) =>
      prev.map((apt) =>
        apt.id === appointmentId ? { ...apt, status: "cancelled" as const } : apt
      )
    );
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Appointments
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your calendar appointments synced from Outlook and Google Calendar
        </p>
      </div>

      {/* Integration Health Card */}
      <IntegrationHealthCard
        integration="outlook"
        lastSynced={lastSynced}
        onRefresh={handleRefresh}
        isSyncing={isSyncing}
        isConnected={true}
      />

      {/* Two Column Layout: Calendar and List */}
      {/* Mobile: Stack vertically, Tablet: Stack vertically, Desktop: Side by side (1/2 split) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Calendar (Full width on mobile/tablet, 1 column on desktop) */}
        <div className="lg:col-span-1">
          <AppointmentCalendar
            appointments={appointments}
            appointmentSources={appointmentSources}
            onDateSelect={setSelectedDate}
            selectedDate={selectedDate}
          />
        </div>

        {/* Appointment List (Full width on mobile/tablet, 2 columns on desktop) */}
        <div className="lg:col-span-2">
          {appointmentsError ? (
            <ErrorState
              error={appointmentsError}
              onRetry={() => {
                setAppointmentsError(null);
                // In real implementation, this would call refetch()
              }}
              title="Failed to load appointments"
              inline
            />
          ) : isLoadingAppointments ? (
            <AppointmentListSkeleton count={5} />
          ) : (selectedDate
            ? appointments.filter((apt) => {
                const aptDate = new Date(apt.dateTime);
                return (
                  aptDate.getDate() === selectedDate.getDate() &&
                  aptDate.getMonth() === selectedDate.getMonth() &&
                  aptDate.getFullYear() === selectedDate.getFullYear()
                );
              })
            : appointments
          ).length === 0 ? (
            <EmptyState
              icon={<Calendar className="h-12 w-12" />}
              title={
                selectedDate
                  ? "No appointments on this date"
                  : "No appointments found"
              }
              description={
                selectedDate
                  ? "You don't have any appointments scheduled for this date."
                  : "You don't have any appointments yet. Appointments synced from Outlook and Google Calendar will appear here."
              }
              size="default"
            />
          ) : (
            <AppointmentList
              appointments={
                selectedDate
                  ? appointments.filter((apt) => {
                      const aptDate = new Date(apt.dateTime);
                      return (
                        aptDate.getDate() === selectedDate.getDate() &&
                        aptDate.getMonth() === selectedDate.getMonth() &&
                        aptDate.getFullYear() === selectedDate.getFullYear()
                      );
                    })
                  : appointments
              }
              onEdit={handleEdit}
              onCancel={handleCancel}
            />
          )}
        </div>
      </div>
    </div>
  );
}

