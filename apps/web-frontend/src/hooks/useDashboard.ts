"use client";

/**
 * Dashboard Hooks
 * 
 * Custom hooks for fetching dashboard data from the API.
 * Provides loading states, error handling, and data transformation.
 * 
 * @example
 * ```tsx
 * function DashboardPage() {
 *   const { data: kpis, isLoading, error } = useKPIs();
 *   const { data: volumeData } = useVolumeData(dateRange);
 *   const { data: activity } = useRecentActivity();
 * 
 *   if (isLoading) return <LoadingSpinner />;
 *   if (error) return <ErrorMessage error={error} />;
 * 
 *   return <div>render dashboard</div>;
 * }
 * ```
 */

import React, { useState, useEffect, useCallback, type ReactNode } from "react";
import { DateRange } from "react-day-picker";
import {
  fetchKPIMetrics,
  fetchVolumeData,
  fetchRecentActivity,
  type KPIMetric,
  type VolumeDataPoint,
  type ActivityItem,
} from "@/lib/api/dashboard";
import type { ActivityListItem } from "@/components/dashboard/ActivityList";
import { User as UserIcon, AlertCircle, DollarSign, Phone, FileText, Clock } from "lucide-react";
import { logger } from "@/lib/logger";

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
 * Map activity type to icon component
 */
function getActivityIcon(type: ActivityItem["type"]): ReactNode {
  const iconProps = { className: "h-4 w-4" };
  
  switch (type) {
    case "client_intake":
      return React.createElement(UserIcon, iconProps);
    case "call":
      return React.createElement(Phone, iconProps);
    case "alert":
      return React.createElement(AlertCircle, iconProps);
    case "payment":
      return React.createElement(DollarSign, iconProps);
    case "document":
      return React.createElement(FileText, iconProps);
    case "appointment":
      return React.createElement(Clock, iconProps);
    default:
      return React.createElement(UserIcon, iconProps);
  }
}

/**
 * Transform API activity item to component activity list item
 */
function transformActivityItem(item: ActivityItem): ActivityListItem {
  return {
    id: item.id,
    icon: getActivityIcon(item.type),
    text: item.text,
    timestamp: new Date(item.timestamp),
    onClick: () => {
      // Default click handler - can be overridden
      logger.debug("Activity clicked", { activityId: item.id });
    },
  };
}

/**
 * Hook to fetch KPI metrics
 * 
 * @returns KPI metrics with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: kpis, isLoading, error, refetch } = useKPIs();
 * ```
 */
export function useKPIs(): UseQueryResult<KPIMetric[]> {
  const [data, setData] = useState<KPIMetric[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchKPIMetrics();
      setData(response.metrics);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch KPI metrics");
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

/**
 * Hook to fetch volume chart data for a date range
 * 
 * @param dateRange - Date range to fetch data for
 * @returns Volume data points with loading and error states
 * 
 * @example
 * ```tsx
 * const dateRange = { from: new Date(), to: new Date() };
 * const { data: volumeData, isLoading, error } = useVolumeData(dateRange);
 * ```
 */
export function useVolumeData(
  dateRange: DateRange | undefined
): UseQueryResult<VolumeDataPoint[]> {
  const [data, setData] = useState<VolumeDataPoint[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!dateRange?.from || !dateRange?.to) {
      setData(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchVolumeData(dateRange);
      setData(response.data);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch volume data");
      setError(error);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [dateRange]);

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
 * Hook to fetch recent activity
 * 
 * @param limit - Maximum number of activity items to fetch (default: 10)
 * @returns Activity items with loading and error states
 * 
 * @example
 * ```tsx
 * const { data: activity, isLoading, error } = useRecentActivity(20);
 * ```
 */
export function useRecentActivity(
  limit: number = 10
): UseQueryResult<ActivityListItem[]> {
  const [data, setData] = useState<ActivityListItem[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchRecentActivity(limit);
      const transformed = response.items.map(transformActivityItem);
      setData(transformed);
    } catch (err) {
      const error =
        err instanceof Error
          ? err
          : new Error("Failed to fetch recent activity");
      setError(error);
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [limit]);

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

