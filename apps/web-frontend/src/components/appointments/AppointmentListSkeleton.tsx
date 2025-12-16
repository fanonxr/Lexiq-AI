"use client";

/**
 * Appointment List Skeleton Component
 * 
 * Loading skeleton for the appointment list in the appointments page.
 * Matches the structure of AppointmentList component.
 * 
 * @example
 * ```tsx
 * <AppointmentListSkeleton count={5} />
 * ```
 */

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/Skeleton";

export interface AppointmentListSkeletonProps {
  /**
   * Number of skeleton rows to show
   * @default 5
   */
  count?: number;
  /**
   * Additional CSS classes
   */
  className?: string;
}

export function AppointmentListSkeleton({
  count = 5,
  className,
}: AppointmentListSkeletonProps) {
  return (
    <Table className={className}>
      <TableHeader>
        <TableRow>
          <TableHead>Client Name</TableHead>
          <TableHead className="w-[200px]">Date & Time</TableHead>
          <TableHead className="w-[150px]">Type</TableHead>
          <TableHead className="w-[120px]">Status</TableHead>
          <TableHead className="w-[100px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: count }).map((_, index) => (
          <TableRow key={index}>
            <TableCell>
              <div className="flex items-center gap-3">
                {/* Avatar skeleton */}
                <Skeleton className="h-8 w-8 rounded-full" />
                <Skeleton className="h-4 w-32" />
              </div>
            </TableCell>
            <TableCell>
              <div className="space-y-1">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-16" />
              </div>
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-20" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-5 w-20 rounded-full" />
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-1">
                <Skeleton className="h-8 w-8 rounded-md" />
                <Skeleton className="h-8 w-8 rounded-md" />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

