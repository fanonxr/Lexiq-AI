"use client";

/**
 * Appointments Hooks
 * 
 * Custom hooks for appointment management including fetching appointments,
 * integration status, syncing, and appointment operations.
 * 
 * @example
 * ```tsx
 * function AppointmentsPage() {
 *   const { data: appointments, isLoading, error } = useAppointments();
 *   const { data: integrations } = useIntegrationStatus();
 *   const { mutate: syncAppointments, isLoading: isSyncing } = useSyncAppointments();
 *   const { mutate: updateAppointment } = useUpdateAppointment();
 * 
 *   if (isLoading) return <LoadingSpinner />;
 *   if (error) return <ErrorMessage error={error} />;
 * 
 *   return <div>Render appointments here</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback } from "react";
import {
  fetchAppointments,
  getIntegrationStatus,
  syncAppointments,
  updateAppointment,
  cancelAppointment,
  getAppointmentSources,
  type Appointment,
  type IntegrationStatus,
  type SyncAppointmentsResponse,
} from "@/lib/api/appointments";
import { logger } from "@/lib/logger";
import type { IntegrationType } from "@/components/appointments/IntegrationHealthCard";
import type { AppointmentType, AppointmentStatus } from "@/components/appointments/AppointmentList";

/**
 * Hook result with loading and error states
 */
interface UseQueryResult<T> {
  data: T | null | undefined;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Mutation result with loading and error states
 */
interface UseMutationResult<TData, TVariables> {
  mutate: (variables: TVariables) => Promise<TData>;
  isLoading: boolean;
  error: Error | null;
  reset: () => void;
}

/**
 * Mutation result with optional variables (for mutations that don't require parameters)
 */
interface UseMutationResultOptional<TData> {
  mutate: (variables?: never) => Promise<TData>;
  isLoading: boolean;
  error: Error | null;
  reset: () => void;
}

/**
 * Hook to fetch appointments
 * 
 * @param startDate - Optional start date filter
 * @param endDate - Optional end date filter
 * @returns Appointments with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: appointments, isLoading, error, refetch } = useAppointments();
 * 
 * // With date range
 * const { data: appointments } = useAppointments(startDate, endDate);
 * ```
 */
export function useAppointments(
  startDate?: Date,
  endDate?: Date
): UseQueryResult<Appointment[]> {
  const [data, setData] = useState<Appointment[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const appointments = await fetchAppointments(startDate, endDate);
      setData(appointments);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch appointments");
      setError(error);
      logger.error("Error fetching appointments", error);
    } finally {
      setIsLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

/**
 * Hook to get integration status for Outlook and Google Calendar
 * 
 * @returns Integration statuses with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: integrations, isLoading, error } = useIntegrationStatus();
 * ```
 */
export function useIntegrationStatus(): UseQueryResult<IntegrationStatus[]> {
  const [data, setData] = useState<IntegrationStatus[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const integrations = await getIntegrationStatus();
      setData(integrations);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch integration status");
      setError(error);
      logger.error("Error fetching integration status", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

/**
 * Hook to sync appointments from calendar integrations
 * 
 * @returns Sync mutation with loading and error states
 * 
 * @example
 * ```tsx
 * const { mutate: syncAppointments, isLoading: isSyncing } = useSyncAppointments();
 * 
 * const handleSync = () => {
 *   syncAppointments("outlook");
 * };
 * ```
 */
export function useSyncAppointments(): UseMutationResultOptional<SyncAppointmentsResponse> & {
  mutate: (integration?: IntegrationType) => Promise<SyncAppointmentsResponse>;
} {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async (integration?: IntegrationType): Promise<SyncAppointmentsResponse> => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await syncAppointments(integration);
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to sync appointments");
        setError(error);
        logger.error("Error syncing appointments", error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isLoading, error, reset };
}

/**
 * Hook to update an appointment
 * 
 * @returns Update mutation with loading and error states
 * 
 * @example
 * ```tsx
 * const { mutate: updateAppointment, isLoading } = useUpdateAppointment();
 * 
 * const handleUpdate = () => {
 *   updateAppointment("appointment-1", {
 *     status: "confirmed",
 *     dateTime: new Date(),
 *   });
 * };
 * ```
 */
export function useUpdateAppointment(): UseMutationResult<
  Appointment,
  { appointmentId: string; updates: { dateTime?: Date; type?: AppointmentType; status?: AppointmentStatus; description?: string } }
> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async ({
      appointmentId,
      updates,
    }: {
      appointmentId: string;
      updates: {
        dateTime?: Date;
        type?: AppointmentType;
        status?: AppointmentStatus;
        description?: string;
      };
    }): Promise<Appointment> => {
      try {
        setIsLoading(true);
        setError(null);
        const appointment = await updateAppointment(appointmentId, updates);
        return appointment;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to update appointment");
        setError(error);
        logger.error("Error updating appointment", error, { appointmentId: data.appointmentId });
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isLoading, error, reset };
}

/**
 * Hook to cancel an appointment
 * 
 * @returns Cancel mutation with loading and error states
 * 
 * @example
 * ```tsx
 * const { mutate: cancelAppointment, isLoading } = useCancelAppointment();
 * 
 * const handleCancel = () => {
 *   cancelAppointment("appointment-1", "Client requested cancellation");
 * };
 * ```
 */
export function useCancelAppointment(): UseMutationResult<
  Appointment,
  { appointmentId: string; reason?: string }
> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(
    async ({
      appointmentId,
      reason,
    }: {
      appointmentId: string;
      reason?: string;
    }): Promise<Appointment> => {
      try {
        setIsLoading(true);
        setError(null);
        const appointment = await cancelAppointment(appointmentId, reason);
        return appointment;
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Failed to cancel appointment");
        setError(error);
        logger.error("Error cancelling appointment", error, { appointmentId: data.appointmentId });
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setError(null);
  }, []);

  return { mutate, isLoading, error, reset };
}

/**
 * Hook to get appointment source mappings (which calendar each appointment comes from)
 * 
 * @returns Appointment source mappings with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: sources, isLoading, error } = useAppointmentSources();
 * ```
 */
export function useAppointmentSources(): UseQueryResult<Record<string, IntegrationType>> {
  const [data, setData] = useState<Record<string, IntegrationType> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const sources = await getAppointmentSources();
      setData(sources);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Failed to fetch appointment sources");
      setError(error);
      logger.error("Error fetching appointment sources", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

