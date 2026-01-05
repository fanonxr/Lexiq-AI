"use client";

import { useState, useMemo, useCallback, Suspense } from "react";
import { IntegrationHealthCard, type IntegrationType } from "@/components/appointments/IntegrationHealthCard";
import { AppointmentList, type Appointment } from "@/components/appointments/AppointmentList";
import { AppointmentListSkeleton } from "@/components/appointments/AppointmentListSkeleton";
import { AppointmentCalendar } from "@/components/appointments/AppointmentCalendar";
import { WeeklyCalendarView } from "@/components/appointments/WeeklyCalendarView";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/Label";
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
import { initiateOutlookOAuth, initiateGoogleOAuth } from "@/lib/api/calendar-integrations";
import { logger } from "@/lib/logger";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

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
function AppointmentsPageContent() {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  // View toggle: "clients" (default) shows only LexiqAI-created appointments, "all" shows everything
  const [showClientsOnly, setShowClientsOnly] = useState<boolean>(true);

  // Fetch client appointments (for the list) - filtered by clientsOnly
  const { data: clientAppointments = [], isLoading: isLoadingClientAppointments, error: clientAppointmentsError, refetch: refetchClientAppointments } = useAppointments(undefined, undefined, showClientsOnly);
  
  // Fetch all appointments (for the weekly calendar) - always show all
  const { data: allAppointments = [] } = useAppointments(undefined, undefined, false);
  
  const { data: integrations = [], isLoading: isLoadingIntegrations } = useIntegrationStatus();
  const { mutate: syncAppointments, isLoading: isSyncing } = useSyncAppointments();
  const { mutate: updateAppointment } = useUpdateAppointment();
  const { mutate: cancelAppointment } = useCancelAppointment();
  const { data: appointmentSources } = useAppointmentSources();
  
  // Use client appointments for the list, all appointments for the calendar
  const appointments = showClientsOnly ? clientAppointments : allAppointments;
  const isLoadingAppointments = isLoadingClientAppointments;
  const appointmentsError = clientAppointmentsError;
  
  const refetchAppointments = useCallback(async () => {
    await refetchClientAppointments();
  }, [refetchClientAppointments]);

  // Get integration status for Outlook
  const outlookIntegration = useMemo(() => {
    if (!integrations || integrations.length === 0) {
      return { isConnected: false, lastSynced: null };
    }
    const integration = integrations.find((int) => int.type === "outlook");
    return {
      isConnected: integration?.isConnected ?? false,
      lastSynced: integration?.lastSynced ? new Date(integration.lastSynced) : null,
    };
  }, [integrations]);

  // Get integration status for Google
  const googleIntegration = useMemo(() => {
    if (!integrations || integrations.length === 0) {
      return { isConnected: false, lastSynced: null };
    }
    const integration = integrations.find((int) => int.type === "google");
    return {
      isConnected: integration?.isConnected ?? false,
      lastSynced: integration?.lastSynced ? new Date(integration.lastSynced) : null,
    };
  }, [integrations]);

  /**
   * Handle refresh/sync for a specific integration
   */
  const handleRefresh = useCallback(async (integration?: IntegrationType) => {
    try {
      await syncAppointments(integration);
      // Refetch appointments after sync
      await refetchAppointments();
    } catch (error) {
      logger.error("Failed to sync appointments", error instanceof Error ? error : new Error(String(error)));
    }
  }, [syncAppointments, refetchAppointments]);

  /**
   * Handle edit appointment
   */
  const handleEdit = useCallback((appointmentId: string) => {
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
      logger.error("Failed to cancel appointment", error instanceof Error ? error : new Error(String(error)), { appointmentId });
    }
  }, [cancelAppointment, refetchAppointments]);

  /**
   * Handle connect Outlook calendar
   */
  const handleConnectOutlook = useCallback(async () => {
    try {
      const redirectUri = `${window.location.origin}/auth/outlook/callback`;
      const authUrl = await initiateOutlookOAuth(redirectUri);
      
      if (!authUrl || typeof authUrl !== "string" || !authUrl.startsWith("http")) {
        logger.error("Invalid authUrl received", undefined, { authUrl });
        alert("Failed to get authorization URL. Please try again.");
        return;
      }
      
      window.location.href = authUrl;
    } catch (error) {
      logger.error("Failed to initiate Outlook OAuth", error instanceof Error ? error : new Error(String(error)));
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      alert(`Failed to connect Outlook calendar: ${errorMessage}`);
    }
  }, []);

  /**
   * Handle connect Google calendar
   */
  const handleConnectGoogle = useCallback(async () => {
    try {
      const redirectUri = `${window.location.origin}/auth/google/callback`;
      const authUrl = await initiateGoogleOAuth(redirectUri);
      
      if (!authUrl || typeof authUrl !== "string" || !authUrl.startsWith("http")) {
        logger.error("Invalid authUrl received", undefined, { authUrl });
        alert("Failed to get authorization URL. Please try again.");
        return;
      }
      
      window.location.href = authUrl;
    } catch (error) {
      logger.error("Failed to initiate Google OAuth", error instanceof Error ? error : new Error(String(error)));
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      alert(`Failed to connect Google Calendar: ${errorMessage}`);
    }
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            Appointments
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your calendar appointments synced from Outlook and Google Calendar
          </p>
        </div>
        
        {/* View Toggle */}
        <div className="flex items-center gap-3">
          <Label htmlFor="view-toggle" className="text-sm text-muted-foreground cursor-pointer">
            {showClientsOnly ? "Clients" : "All Appointments"}
          </Label>
          <Switch
            id="view-toggle"
            checked={showClientsOnly}
            onCheckedChange={setShowClientsOnly}
            aria-label="Toggle between clients only and all appointments"
          />
        </div>
      </div>

      {/* Integration Health Cards - Show both Outlook and Google */}
      <div className="flex flex-col gap-3 sm:flex-row">
        {/* Outlook Calendar Integration */}
        <IntegrationHealthCard
          integration="outlook"
          lastSynced={outlookIntegration.lastSynced}
          onRefresh={() => handleRefresh("outlook")}
          onConnect={handleConnectOutlook}
          isSyncing={isSyncing}
          isConnected={outlookIntegration.isConnected}
          className="flex-1"
        />

        {/* Google Calendar Integration */}
        <IntegrationHealthCard
          integration="google"
          lastSynced={googleIntegration.lastSynced}
          onRefresh={() => handleRefresh("google")}
          onConnect={handleConnectGoogle}
          isSyncing={isSyncing}
          isConnected={googleIntegration.isConnected}
          className="flex-1"
        />
      </div>

      {/* Two Column Layout: Calendar and List */}
      {/* Mobile: Stack vertically, Tablet: Stack vertically, Desktop: Side by side (1/2 split) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Calendar (Full width on mobile/tablet, 1 column on desktop) */}
        {/* Always show all appointments in calendar (including calendar events) */}
        <div className="lg:col-span-1">
          <AppointmentCalendar
            appointments={allAppointments || []}
            appointmentSources={appointmentSources ?? undefined}
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
          ) : (() => {
              const appointmentsList = appointments || [];
              const filteredAppointments = selectedDate
                ? appointmentsList.filter((apt) => {
                    const aptDate = typeof apt.dateTime === 'string' ? new Date(apt.dateTime) : apt.dateTime;
                    return (
                      aptDate.getDate() === selectedDate.getDate() &&
                      aptDate.getMonth() === selectedDate.getMonth() &&
                      aptDate.getFullYear() === selectedDate.getFullYear()
                    );
                  })
                : appointmentsList;
              return filteredAppointments.length === 0;
            })() ? (
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
                (() => {
                  const appointmentsList = appointments || [];
                  if (!selectedDate) return appointmentsList;
                  return appointmentsList.filter((apt) => {
                    const aptDate = typeof apt.dateTime === 'string' ? new Date(apt.dateTime) : apt.dateTime;
                    return (
                      aptDate.getDate() === selectedDate.getDate() &&
                      aptDate.getMonth() === selectedDate.getMonth() &&
                      aptDate.getFullYear() === selectedDate.getFullYear()
                    );
                  });
                })()
              }
              onEdit={handleEdit}
              onCancel={handleCancel}
            />
          )}
        </div>
      </div>

      {/* Weekly Calendar View */}
      {/* Always show all appointments in weekly calendar (including calendar events) */}
      <WeeklyCalendarView
        appointments={allAppointments || []}
        appointmentSources={appointmentSources ?? undefined}
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

export default function AppointmentsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AppointmentsPageContent />
    </Suspense>
  );
}

