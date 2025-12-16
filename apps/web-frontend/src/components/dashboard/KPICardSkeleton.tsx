"use client";

/**
 * KPI Card Skeleton Component
 * 
 * Loading skeleton for KPI cards in the dashboard.
 * Matches the structure of KPICard component.
 * 
 * @example
 * ```tsx
 * <KPICardSkeleton />
 * ```
 */

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";

export function KPICardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {/* Large number skeleton */}
          <Skeleton className="h-9 w-24" />
          {/* Trend indicator skeleton */}
          <Skeleton className="h-4 w-20" />
        </div>
      </CardContent>
    </Card>
  );
}

