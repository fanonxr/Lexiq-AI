"use client";

import { useState, useMemo, useCallback } from "react";
import { IntegrationHealthCard, type IntegrationType } from "@/components/appointments/IntegrationHealthCard";
import { AppointmentList, type Appointment } from "@/components/appointments/AppointmentList";
import { AppointmentListSkeleton } from "@/components/appointments/AppointmentListSkeleton";
import { AppointmentCalendar } from "@/components/appointments/AppointmentCalendar";
import { WeeklyCalendarView } from "@/components/appointments/WeeklyCalendarView";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useAppointments,
  useIntegrationStatus,
  useSyncAppointments,
  useUpdateAppointment,
  useCancelAppointment,
  useAppointmentSources,
} from "@/hooks/useAppointments";
import { initiateOutlookOAuth } from "@/lib/api/calendar-integrations";

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
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);

  // Fetch appointments and integration status
  const { data: appointments = [], isLoading: isLoadingAppointments, error: appointmentsError, refetch: refetchAppointments } = useAppointments();
  const { data: integrations = [], isLoading: isLoadingIntegrations } = useIntegrationStatus();
  const { mutate: syncAppointments, isLoading: isSyncing } = useSyncAppointments();
  const { mutate: updateAppointment } = useUpdateAppointment();
  const { mutate: cancelAppointment } = useCancelAppointment();
  const { data: appointmentSources = {} } = useAppointmentSources();

  // Get last synced time from integrations (use the most recent one)
  const lastSynced = useMemo(() => {
    if (!integrations || integrations.length === 0) {
      return new Date();
    }
    const syncedDates = integrations
      .filter((int) => int.lastSynced)
      .map((int) => new Date(int.lastSynced!))
      .sort((a, b) => b.getTime() - a.getTime());
    return syncedDates.length > 0 ? syncedDates[0] : new Date();
  }, [integrations]);

  // Get primary integration (outlook or google) for the health card
  const primaryIntegration = useMemo<IntegrationType>(() => {
    if (!integrations || integrations.length === 0) {
      return "outlook";
    }
    // Prefer outlook if available, otherwise google
    const outlook = integrations.find((int) => int.type === "outlook");
    return outlook ? "outlook" : "google";
  }, [integrations]);

  const primaryIntegrationStatus = useMemo(() => {
    if (!integrations || integrations.length === 0) {
      return { isConnected: false, lastSynced: null };
    }
    const integration = integrations.find((int) => int.type === primaryIntegration);
    return {
      isConnected: integration?.isConnected ?? false,
      lastSynced: integration?.lastSynced ? new Date(integration.lastSynced) : null,
    };
  }, [integrations, primaryIntegration]);

  /**
   * Handle refresh/sync
   */
  const handleRefresh = useCallback(async () => {
    try {
      await syncAppointments();
      // Refetch appointments after sync
      await refetchAppointments();
    } catch (error) {
      console.error("Failed to sync appointments:", error);
    }
  }, [syncAppointments, refetchAppointments]);

  /**
   * Handle edit appointment
   */
  const handleEdit = useCallback((appointmentId: string) => {
    console.log("Edit appointment:", appointmentId);
    // TODO: Open edit modal or navigate to edit page
    // For now, this is a placeholder
  }, []);

  /**
   * Handle cancel appointment
   */
  const handleCancel = useCallback(async (appointmentId: string) => {
    try {
      await cancelAppointment({ appointmentId });
      // Refetch appointments after cancellation
      await refetchAppointments();
    } catch (error) {
      console.error("Failed to cancel appointment:", error);
    }
  }, [cancelAppointment, refetchAppointments]);

  /**
   * Handle connect Outlook calendar
   */
  const handleConnectOutlook = useCallback(async () => {
    try {
      const redirectUri = `${window.location.origin}/auth/outlook/callback`;
      console.log("Initiating Outlook OAuth with redirectUri:", redirectUri);
      
      const authUrl = await initiateOutlookOAuth(redirectUri);
      console.log("Received authUrl:", authUrl);
      
      if (!authUrl || typeof authUrl !== "string") {
        console.error("Invalid authUrl received:", authUrl);
        alert("Failed to get authorization URL. Please check the console for details.");
        return;
      }
      
      if (!authUrl.startsWith("http")) {
        console.error("Invalid authUrl format:", authUrl);
        alert("Invalid authorization URL format. Please check the console for details.");
        return;
      }
      
      // Redirect user to Microsoft OAuth page
      console.log("Redirecting to:", authUrl);
      window.location.href = authUrl;
    } catch (error) {
      console.error("Failed to initiate Outlook OAuth:", error);
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      alert(`Failed to connect Outlook calendar: ${errorMessage}`);
    }
  }, []);

  /**
   * Handle connect Google calendar (placeholder for future implementation)
   */
  const handleConnectGoogle = useCallback(async () => {
    // TODO: Implement Google Calendar OAuth flow
    console.log("Google Calendar connection not yet implemented");
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
        integration={primaryIntegration}
        lastSynced={primaryIntegrationStatus.lastSynced || lastSynced}
        onRefresh={handleRefresh}
        onConnect={
          primaryIntegration === "outlook"
            ? handleConnectOutlook
            : primaryIntegration === "google"
            ? handleConnectGoogle
            : undefined
        }
        isSyncing={isSyncing}
        isConnected={primaryIntegrationStatus.isConnected}
      />

      {/* Two Column Layout: Calendar and List */}
      {/* Mobile: Stack vertically, Tablet: Stack vertically, Desktop: Side by side (1/2 split) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Calendar (Full width on mobile/tablet, 1 column on desktop) */}
        <div className="lg:col-span-1">
          <AppointmentCalendar
            appointments={appointments || []}
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
                refetchAppointments();
              }}
              title="Failed to load appointments"
              inline
            />
          ) : isLoadingAppointments ? (
            <AppointmentListSkeleton count={5} />
          ) : (selectedDate
            ? appointments.filter((apt) => {
                const aptDate = typeof apt.dateTime === 'string' ? new Date(apt.dateTime) : apt.dateTime;
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
                      const aptDate = typeof apt.dateTime === 'string' ? new Date(apt.dateTime) : apt.dateTime;
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

      {/* Weekly Calendar View */}
      <WeeklyCalendarView
        appointments={appointments || []}
        appointmentSources={appointmentSources}
        onAppointmentClick={(apt) => {
          // Set selected date to the appointment's date
          const aptDate = typeof apt.dateTime === 'string' ? new Date(apt.dateTime) : apt.dateTime;
          setSelectedDate(aptDate);
          // Scroll to top to see the appointment in the list
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      />
    </div>
  );
}

