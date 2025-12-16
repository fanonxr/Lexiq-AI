"use client";

/**
 * Skeleton Component
 * 
 * A loading placeholder component that shows a shimmer animation.
 * Used for skeleton screens while content is loading.
 * 
 * @example
 * ```tsx
 * <Skeleton className="h-4 w-32" />
 * ```
 */

import { type HTMLAttributes } from "react";
import { clsx } from "clsx";

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Whether to show the skeleton
   * @default true
   */
  show?: boolean;
}

/**
 * Skeleton component with shimmer animation
 */
export function Skeleton({
  className,
  show = true,
  ...props
}: SkeletonProps) {
  if (!show) return null;

  return (
    <div
      className={clsx(
        "animate-pulse rounded-md bg-zinc-200 dark:bg-zinc-800",
        className
      )}
      aria-busy="true"
      aria-label="Loading"
      {...props}
    />
  );
}

