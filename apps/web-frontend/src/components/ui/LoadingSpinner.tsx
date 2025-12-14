"use client";

/**
 * Loading Spinner Component
 * 
 * A loading indicator component for async operations.
 * 
 * @example
 * ```tsx
 * <LoadingSpinner size="md" />
 * ```
 */

import { type HTMLAttributes } from "react";
import { clsx } from "clsx";

export type SpinnerSize = "sm" | "md" | "lg";

export interface LoadingSpinnerProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Size of the spinner
   * @default "md"
   */
  size?: SpinnerSize;
  /**
   * Optional text to display below the spinner
   */
  text?: string;
  /**
   * Whether to show full screen overlay
   * @default false
   */
  fullScreen?: boolean;
}

/**
 * Loading spinner component
 */
export function LoadingSpinner({
  size = "md",
  text,
  fullScreen = false,
  className,
  ...props
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  const spinner = (
    <div
      className={clsx(
        "flex flex-col items-center justify-center gap-2",
        fullScreen && "min-h-screen",
        className
      )}
      role="status"
      aria-live="polite"
      aria-label={text || "Loading"}
      {...props}
    >
      <svg
        className={clsx(
          "animate-spin text-zinc-600 dark:text-zinc-400",
          sizeClasses[size]
        )}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      {text && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{text}</p>
      )}
      <span className="sr-only">Loading...</span>
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm">
        {spinner}
      </div>
    );
  }

  return spinner;
}
