"use client";

/**
 * Call List Skeleton Component
 * 
 * Loading skeleton for the call list in the recordings/inbox page.
 * Shows multiple skeleton items matching CallListItem structure.
 * 
 * @example
 * ```tsx
 * <CallListSkeleton count={5} />
 * ```
 */

import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";

export interface CallListSkeletonProps {
  /**
   * Number of skeleton items to show
   * @default 5
   */
  count?: number;
  /**
   * Additional CSS classes
   */
  className?: string;
}

export function CallListSkeleton({
  count = 5,
  className,
}: CallListSkeletonProps) {
  return (
    <div className={cn("divide-y divide-zinc-200 dark:divide-zinc-800", className)}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="p-4 space-y-2">
          {/* Top row: Name and badge */}
          <div className="flex items-center justify-between gap-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
          {/* Bottom row: Summary and timestamp */}
          <div className="flex items-center justify-between gap-2">
            <Skeleton className="h-3 w-48" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

