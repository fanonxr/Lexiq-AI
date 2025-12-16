"use client";

/**
 * Chart Skeleton Component
 * 
 * Loading skeleton for charts (volume chart, etc.).
 * Shows a placeholder with chart-like structure.
 * 
 * @example
 * ```tsx
 * <ChartSkeleton height={300} />
 * ```
 */

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";

export interface ChartSkeletonProps {
  /**
   * Height of the chart skeleton
   * @default 300
   */
  height?: number;
  /**
   * Additional CSS classes
   */
  className?: string;
}

export function ChartSkeleton({
  height = 300,
  className,
}: ChartSkeletonProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4" style={{ height: `${height}px` }}>
          {/* Chart area with bars/lines */}
          <div className="flex h-full items-end justify-between gap-2">
            {Array.from({ length: 12 }).map((_, i) => (
              <Skeleton
                key={i}
                className="w-full"
                style={{
                  height: `${Math.random() * 60 + 20}%`,
                }}
              />
            ))}
          </div>
          {/* X-axis labels */}
          <div className="flex justify-between">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-12" />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

