"use client";

/**
 * Empty State Component
 * 
 * Displays helpful messages when there's no data to show.
 * Provides context and actionable guidance.
 * 
 * @example
 * ```tsx
 * <EmptyState
 *   icon={<Inbox className="h-12 w-12" />}
 *   title="No calls found"
 *   description="You don't have any calls yet. Calls will appear here once they're recorded."
 *   action={<Button onClick={handleAction}>Get Started</Button>}
 * />
 * ```
 */

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface EmptyStateProps {
  /**
   * Icon to display (usually a Lucide icon)
   */
  icon?: ReactNode;
  /**
   * Title text
   */
  title: string;
  /**
   * Description text
   */
  description?: string;
  /**
   * Optional action button or element
   */
  action?: ReactNode;
  /**
   * Additional CSS classes
   */
  className?: string;
  /**
   * Size variant
   * @default "default"
   */
  size?: "sm" | "default" | "lg";
}

/**
 * Empty State Component
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  size = "default",
}: EmptyStateProps) {
  const sizeClasses = {
    sm: {
      icon: "h-8 w-8",
      title: "text-base",
      description: "text-sm",
      container: "p-4",
    },
    default: {
      icon: "h-12 w-12",
      title: "text-lg",
      description: "text-sm",
      container: "p-8",
    },
    lg: {
      icon: "h-16 w-16",
      title: "text-xl",
      description: "text-base",
      container: "p-12",
    },
  };

  const sizes = sizeClasses[size];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        sizes.container,
        className
      )}
    >
      {icon && (
        <div
          className={cn(
            "mb-4 text-muted-foreground",
            sizes.icon
          )}
        >
          {icon}
        </div>
      )}
      
      <h3
        className={cn(
          "mb-2 font-semibold text-foreground",
          sizes.title
        )}
      >
        {title}
      </h3>
      
      {description && (
        <p
          className={cn(
            "mb-4 max-w-md text-muted-foreground",
            sizes.description
          )}
        >
          {description}
        </p>
      )}
      
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

