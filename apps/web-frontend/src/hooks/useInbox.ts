"use client";

/**
 * Inbox Hooks
 * 
 * Custom hooks for fetching inbox/call data from the API.
 * Provides loading states, error handling, and data transformation.
 * 
 * @example
 * ```tsx
 * function RecordingsPage() {
 *   const { data: calls, isLoading, error } = useCalls("all");
 *   const { data: callDetails } = useCallDetails(selectedCallId);
 *   const { data: audioUrl } = useAudioUrl(selectedCallId);
 * 
 *   if (isLoading) return <LoadingSpinner />;
 *   if (error) return <ErrorMessage error={error} />;
 * 
 *   return <div>{/* render calls */}</div>;
 * }
 * ```
 */

import { useState, useEffect, useCallback } from "react";
import {
  fetchCalls,
  fetchCallDetails,
  getAudioUrl,
  type CallFilter,
  type CallListResponse,
  type CallDetailsResponse,
  type AudioUrlResponse,
} from "@/lib/api/inbox";
import type { Call } from "@/components/inbox/CallListItem";
import type { TranscriptSegment } from "@/components/inbox/AudioPlayer";

/**
 * Hook result with loading and error states
 */
interface UseQueryResult<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Transform API call data to component Call format
 */
function transformCallData(apiCall: any): Call {
  return {
    id: apiCall.id,
    callerName: apiCall.callerName || apiCall.caller_name || "Unknown Caller",
    status: (apiCall.status as Call["status"]) || "existing_client",
    summary: apiCall.summary || apiCall.transcript_preview || "",
    timestamp: new Date(apiCall.timestamp || apiCall.created_at || apiCall.started_at),
    phoneNumber: apiCall.phoneNumber || apiCall.phone_number,
    duration: apiCall.duration,
    metadata: apiCall.metadata,
  };
}

/**
 * Hook to fetch calls with filtering
 * 
 * @param filter - Filter type (all, unread, leads, spam)
 * @returns Calls list with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: calls, isLoading, error, refetch } = useCalls("unread");
 * ```
 */
export function useCalls(filter: CallFilter = "all"): UseQueryResult<Call[]> {
  const [data, setData] = useState<Call[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchCalls(filter);
      const transformedCalls = response.calls.map(transformCallData);
      setData(transformedCalls);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch calls");
      setError(error);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}

/**
 * Hook to fetch call details including transcript and summary
 * 
 * @param callId - Call ID to fetch details for
 * @returns Call details with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: callDetails, isLoading, error } = useCallDetails("call-123");
 * ```
 */
export function useCallDetails(
  callId: string | null
): UseQueryResult<CallDetailsResponse> {
  const [data, setData] = useState<CallDetailsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!callId) {
      setData(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchCallDetails(callId);
      setData(response);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch call details");
      setError(error);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [callId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}

/**
 * Hook to get audio file URL for a call
 * 
 * @param callId - Call ID to get audio URL for
 * @returns Audio URL with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: audioUrl, isLoading, error } = useAudioUrl("call-123");
 * ```
 */
export function useAudioUrl(
  callId: string | null
): UseQueryResult<string> {
  const [data, setData] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!callId) {
      setData(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const response = await getAudioUrl(callId);
      setData(response.audioUrl);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch audio URL");
      setError(error);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [callId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}

/**
 * Hook to get filter counts for calls
 * 
 * @returns Filter counts with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: counts, isLoading, error } = useCallCounts();
 * ```
 */
export function useCallCounts(): UseQueryResult<CallListResponse["counts"]> {
  const [data, setData] = useState<CallListResponse["counts"] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchCalls("all");
      setData(response.counts);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch call counts");
      setError(error);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    refetch: fetchData,
  };
}

