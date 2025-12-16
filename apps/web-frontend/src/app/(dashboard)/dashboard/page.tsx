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
  // Loading state - will be replaced with actual hook loading states
  const [isLoadingKPIs, setIsLoadingKPIs] = useState(false);
  const [isLoadingChart, setIsLoadingChart] = useState(false);
  const [isLoadingActivity, setIsLoadingActivity] = useState(false);
  
  // Error state - will be replaced with actual hook error states
  const [kpiError, setKpiError] = useState<Error | null>(null);
  const [chartError, setChartError] = useState<Error | null>(null);
  const [activityError, setActivityError] = useState<Error | null>(null);

  // Date range state - default to last 30 days
  const [dateRange, setDateRange] = useState<DateRange | undefined>({
    from: subDays(new Date(), 30),
    to: new Date(),
  });

  // Mock KPI data - will be replaced with API calls later
  const kpiData = useMemo(() => [
    {
      title: "Billable Hours Saved",
      value: 1247,
      trend: { direction: "up" as const, percentage: 12, label: "from last week" },
    },
    {
      title: "Calls Handled",
      value: 342,
      trend: { direction: "up" as const, percentage: 8, label: "from last week" },
    },
    {
      title: "Revenue Impact",
      value: 45600,
      formatValue: (val: number) => `$${val.toLocaleString()}`,
      trend: { direction: "up" as const, percentage: 15, label: "from last week" },
    },
    {
      title: "Active Clients",
      value: 89,
      trend: { direction: "up" as const, percentage: 5, label: "from last week" },
    },
  ], []);

  // Mock volume chart data - generates data for the selected date range
  const volumeData = useMemo<VolumeChartDataPoint[]>(() => {
    if (!dateRange?.from || !dateRange?.to) return [];
    
    const days = Math.ceil(
      (dateRange.to.getTime() - dateRange.from.getTime()) / (1000 * 60 * 60 * 24)
    );
    const data: VolumeChartDataPoint[] = [];
    
    for (let i = 0; i <= days; i++) {
      const date = new Date(dateRange.from);
      date.setDate(date.getDate() + i);
      // Generate mock data with some variation
      const value = Math.floor(Math.random() * 200) + 50;
      data.push({
        date: format(date, "yyyy-MM-dd"),
        value,
      });
    }
    
    return data;
  }, [dateRange]);

  // Mock activity data
  const activityData = useMemo<ActivityListItem[]>(() => [
    {
      id: "1",
      icon: <User className="h-4 w-4" />,
      text: "New Client Intake: John Doe",
      timestamp: new Date(Date.now() - 10 * 60 * 1000), // 10 minutes ago
      onClick: () => console.log("Clicked activity 1"),
    },
    {
      id: "2",
      icon: <Phone className="h-4 w-4" />,
      text: "Incoming call from Sarah Smith",
      timestamp: new Date(Date.now() - 25 * 60 * 1000), // 25 minutes ago
      onClick: () => console.log("Clicked activity 2"),
    },
    {
      id: "3",
      icon: <AlertCircle className="h-4 w-4" />,
      text: "Follow-up required: Case #1234",
      timestamp: new Date(Date.now() - 45 * 60 * 1000), // 45 minutes ago
      onClick: () => console.log("Clicked activity 3"),
    },
    {
      id: "4",
      icon: <DollarSign className="h-4 w-4" />,
      text: "Payment received: $2,500",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
      onClick: () => console.log("Clicked activity 4"),
    },
    {
      id: "5",
      icon: <FileText className="h-4 w-4" />,
      text: "Document uploaded: Contract.pdf",
      timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000), // 3 hours ago
      onClick: () => console.log("Clicked activity 5"),
    },
    {
      id: "6",
      icon: <Clock className="h-4 w-4" />,
      text: "Appointment scheduled: Tomorrow 2 PM",
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
      onClick: () => console.log("Clicked activity 6"),
    },
  ], []);

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
          onRetry={() => {
            setKpiError(null);
            // In real implementation, this would call refetch()
          }}
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
            kpiData.map((kpi, index) => (
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
                  onRetry={() => {
                    setChartError(null);
                    // In real implementation, this would call refetch()
                  }}
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
              <ActivityList items={activityData} maxItems={10} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
