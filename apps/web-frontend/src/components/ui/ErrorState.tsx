"use client";

/**
 * Error State Component
 * 
 * Displays error messages for API failures, network errors, and other errors.
 * Includes retry functionality and helpful error messages.
 * 
 * @example
 * ```tsx
 * <ErrorState
 *   error={error}
 *   onRetry={() => refetch()}
 *   title="Failed to load data"
 * />
 * ```
 */

import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/Alert";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  /**
   * Error object or message
   */
  error: Error | string | null | undefined;
  /**
   * Callback to retry the failed operation
   */
  onRetry?: () => void;
  /**
   * Optional title for the error
   */
  title?: string;
  /**
   * Optional description
   */
  description?: string;
  /**
   * Whether the retry is in progress
   */
  isRetrying?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
  /**
   * Whether to show as inline alert or full error state
   * @default false (full error state)
   */
  inline?: boolean;
}

/**
 * Get user-friendly error message from error object
 */
function getErrorMessage(error: Error | string | null | undefined): string {
  if (!error) return "An unknown error occurred";
  
  if (typeof error === "string") return error;
  
  // Network errors
  if (error.message.includes("fetch") || error.message.includes("network")) {
    return "Network error. Please check your connection and try again.";
  }
  
  // API errors
  if (error.message.includes("404")) {
    return "The requested resource was not found.";
  }
  
  if (error.message.includes("403") || error.message.includes("401")) {
    return "You don't have permission to access this resource.";
  }
  
  if (error.message.includes("500") || error.message.includes("server")) {
    return "Server error. Please try again later.";
  }
  
  // Return the error message if available
  return error.message || "An error occurred. Please try again.";
}

/**
 * Error State Component
 */
export function ErrorState({
  error,
  onRetry,
  title,
  description,
  isRetrying = false,
  className,
  inline = false,
}: ErrorStateProps) {
  if (!error) return null;

  const errorMessage = getErrorMessage(error);
  const displayTitle = title || "Something went wrong";

  // Inline error (for use within cards/components)
  if (inline) {
    return (
      <Alert variant="error" title={displayTitle} className={className}>
        <div className="space-y-2">
          <p>{errorMessage}</p>
          {description && <p className="text-sm opacity-90">{description}</p>}
          {onRetry && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              disabled={isRetrying}
              className="mt-2 gap-2"
            >
              <RefreshCw className={cn("h-4 w-4", isRetrying && "animate-spin")} />
              {isRetrying ? "Retrying..." : "Retry"}
            </Button>
          )}
        </div>
      </Alert>
    );
  }

  // Full error state (centered, for page-level errors)
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
        <AlertCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
      </div>
      
      <h3 className="mb-2 text-lg font-semibold text-foreground">
        {displayTitle}
      </h3>
      
      <p className="mb-4 max-w-md text-sm text-muted-foreground">
        {errorMessage}
      </p>
      
      {description && (
        <p className="mb-4 max-w-md text-xs text-muted-foreground">
          {description}
        </p>
      )}
      
      {onRetry && (
        <Button
          variant="default"
          onClick={onRetry}
          disabled={isRetrying}
          className="gap-2"
        >
          <RefreshCw className={cn("h-4 w-4", isRetrying && "animate-spin")} />
          {isRetrying ? "Retrying..." : "Try Again"}
        </Button>
      )}
    </div>
  );
}

