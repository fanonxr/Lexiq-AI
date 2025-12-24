"use client";

import { useState, useMemo, lazy, Suspense } from "react";
import { DateRange } from "react-day-picker";
import { User, AlertCircle, DollarSign, Phone, FileText, Clock } from "lucide-react";
import { KPICard } from "@/components/dashboard/KPICard";
import { KPICardSkeleton } from "@/components/dashboard/KPICardSkeleton";
import { ChartSkeleton } from "@/components/dashboard/ChartSkeleton";
import { ActivityList, type ActivityListItem } from "@/components/dashboard/ActivityList";
import { StatusIndicator } from "@/components/dashboard/StatusIndicator";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { subDays, format } from "date-fns";
import { useKPIs, useVolumeData, useRecentActivity } from "@/hooks/useDashboard";

// Lazy load heavy chart component
const VolumeChart = lazy(() => 
  import("@/components/dashboard/VolumeChart").then(module => ({
    default: module.VolumeChart,
  }))
);

// Re-export type for use in this file
export type { VolumeChartDataPoint } from "@/components/dashboard/VolumeChart";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

/**
 * Dashboard home page (Command Center)
 * 
 * Displays key performance indicators, volume charts, and recent activity.
 * Follows the Vercel/Linear design language with data density and monochromatic elegance.
 * 
 * Layout:
 * - Header: Title "Overview", Status Indicator, Date Range Picker
 * - Top Row: 4 KPI cards (Billable Hours Saved, Calls Handled, Revenue Impact, Active Clients)
 * - Middle Row: Volume Chart (8 columns) + Activity List (4 columns)
 */
export default function DashboardPage() {
  // Date range state - default to last 30 days
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: subDays(new Date(), 30),
    to: new Date(),
  });

  // Fetch data using hooks
  const { data: kpiData, isLoading: isLoadingKPIs, error: kpiError, refetch: refetchKPIs } = useKPIs();
  const { data: volumeDataPoints, isLoading: isLoadingChart, error: chartError, refetch: refetchChart } = useVolumeData(dateRange);
  const { data: activityData, isLoading: isLoadingActivity, error: activityError, refetch: refetchActivity } = useRecentActivity(10);

  // Transform volume data points to chart format
  const volumeData = useMemo<VolumeChartDataPoint[]>(() => {
    if (!volumeDataPoints) return [];
    return volumeDataPoints.map(point => ({
      date: point.date,
      value: point.value,
    }));
  }, [volumeDataPoints]);

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
          Overview
        </h1>
        
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          {/* Status Indicator */}
          <StatusIndicator status="online" />
          
          {/* Date Range Picker */}
          <DateRangePicker
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
            placeholder="Select date range"
          />
        </div>
      </div>

      {/* KPI Row - 4 cards spanning full width */}
      {/* Mobile: 1 column, Tablet: 2 columns, Desktop: 4 columns */}
      {kpiError ? (
        <ErrorState
          error={kpiError}
          onRetry={refetchKPIs}
          title="Failed to load KPIs"
          inline
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {isLoadingKPIs ? (
            // Show skeleton loaders
            Array.from({ length: 4 }).map((_, index) => (
              <KPICardSkeleton key={index} />
            ))
          ) : (
            (kpiData || []).map((kpi, index) => (
              <KPICard
                key={index}
                title={kpi.title}
                value={kpi.value}
                trend={kpi.trend}
                formatValue={kpi.formatValue}
              />
            ))
          )}
        </div>
      )}

      {/* Middle Row - Volume Chart + Activity List */}
      {/* Mobile: Stack vertically, Tablet: Stack vertically, Desktop: Side by side (8/4 split) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Volume Chart - Full width on mobile/tablet, 8 columns on desktop */}
        <div className="lg:col-span-8">
          {chartError ? (
            <Card>
              <CardContent className="pt-6">
                <ErrorState
                  error={chartError}
                  onRetry={refetchChart}
                  title="Failed to load chart data"
                  inline
                />
              </CardContent>
            </Card>
          ) : isLoadingChart ? (
            <ChartSkeleton height={300} />
          ) : volumeData.length > 0 ? (
            <Card hoverable>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Call Volume</CardTitle>
              </CardHeader>
              <CardContent>
                <Suspense fallback={<ChartSkeleton height={300} />}>
                  <VolumeChart data={volumeData} height={300} />
                </Suspense>
              </CardContent>
            </Card>
          ) : (
            <Card hoverable>
              <CardHeader className="pb-3">
                <CardTitle className="text-base font-semibold">Call Volume</CardTitle>
              </CardHeader>
              <CardContent>
                <EmptyState
                  title="No data available"
                  description="Select a date range to view chart data"
                  size="sm"
                />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Activity List - Full width on mobile/tablet, 4 columns on desktop */}
        <div className="lg:col-span-4">
          <Card hoverable>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingActivity ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-12 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" />
                  ))}
                </div>
              ) : activityError ? (
                <ErrorState
                  error={activityError}
                  onRetry={refetchActivity}
                  title="Failed to load activity"
                  inline
                />
              ) : (
                <ActivityList items={activityData || []} maxItems={10} />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
