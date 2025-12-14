"use client";

/**
 * Alert Component
 * 
 * A notification component for displaying messages to users.
 * 
 * @example
 * ```tsx
 * <Alert variant="success" title="Success!">
 *   Your changes have been saved.
 * </Alert>
 * ```
 */

import { type HTMLAttributes } from "react";
import { clsx } from "clsx";

export type AlertVariant = "success" | "error" | "warning" | "info";

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Visual style variant
   * @default "info"
   */
  variant?: AlertVariant;
  /**
   * Optional title for the alert
   */
  title?: string;
  /**
   * Whether the alert can be dismissed
   * @default false
   */
  dismissible?: boolean;
  /**
   * Callback when alert is dismissed
   */
  onDismiss?: () => void;
}

/**
 * Alert component for notifications
 */
export function Alert({
  variant = "info",
  title,
  dismissible = false,
  onDismiss,
  className,
  children,
  ...props
}: AlertProps) {
  // Variant styles
  const variantStyles = {
    success: [
      "bg-green-50 border-green-200 text-green-800",
      "dark:bg-green-900/20 dark:border-green-800 dark:text-green-200",
    ],
    error: [
      "bg-red-50 border-red-200 text-red-800",
      "dark:bg-red-900/20 dark:border-red-800 dark:text-red-200",
    ],
    warning: [
      "bg-yellow-50 border-yellow-200 text-yellow-800",
      "dark:bg-yellow-900/20 dark:border-yellow-800 dark:text-yellow-200",
    ],
    info: [
      "bg-blue-50 border-blue-200 text-blue-800",
      "dark:bg-blue-900/20 dark:border-blue-800 dark:text-blue-200",
    ],
  };

  const alertClasses = clsx(
    "relative rounded-lg border p-4",
    variantStyles[variant],
    className
  );

  return (
    <div
      role="alert"
      aria-live="polite"
      className={alertClasses}
      {...props}
    >
      <div className="flex items-start">
        <div className="flex-1">
          {title && (
            <h4 className="mb-1 font-semibold">{title}</h4>
          )}
          <div className="text-sm">{children}</div>
        </div>
        {dismissible && onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="ml-4 -mt-1 -mr-2 flex-shrink-0 rounded-md p-1.5 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
            aria-label="Dismiss alert"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
