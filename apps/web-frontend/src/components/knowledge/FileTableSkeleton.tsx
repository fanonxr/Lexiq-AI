"use client";

/**
 * File Table Skeleton Component
 * 
 * Loading skeleton for the file data table in the knowledge base page.
 * Matches the structure of FileDataTable component.
 * 
 * @example
 * ```tsx
 * <FileTableSkeleton count={3} />
 * ```
 */

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/Skeleton";

export interface FileTableSkeletonProps {
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

export function FileTableSkeleton({
  count = 5,
  className,
}: FileTableSkeletonProps) {
  return (
    <Table className={className}>
      <TableHeader>
        <TableRow>
          <TableHead>File Name</TableHead>
          <TableHead className="w-[150px]">Date</TableHead>
          <TableHead className="w-[100px]">Size</TableHead>
          <TableHead className="w-[120px]">Status</TableHead>
          <TableHead className="w-[120px] text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: count }).map((_, index) => (
          <TableRow key={index}>
            <TableCell>
              <Skeleton className="h-4 w-40" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-20" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4 w-16" />
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

