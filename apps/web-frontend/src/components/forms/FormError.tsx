"use client";

/**
 * Form Error Component
 * 
 * Component for displaying form-level errors (not field-specific).
 * 
 * @example
 * ```tsx
 * <FormError error="Something went wrong. Please try again." />
 * ```
 */

import { Alert } from "@/components/ui/Alert";

export interface FormErrorProps {
  /**
   * Error message to display
   */
  error?: string | Error | null;
  /**
   * Optional title for the error
   */
  title?: string;
  /**
   * Whether the error can be dismissed
   * @default false
   */
  dismissible?: boolean;
  /**
   * Callback when error is dismissed
   */
  onDismiss?: () => void;
}

/**
 * Form-level error display component
 */
export function FormError({
  error,
  title = "Error",
  dismissible = false,
  onDismiss,
}: FormErrorProps) {
  if (!error) {
    return null;
  }

  const errorMessage =
    typeof error === "string" ? error : error?.message || "An error occurred";

  return (
    <Alert
      variant="error"
      title={title}
      dismissible={dismissible}
      onDismiss={onDismiss}
    >
      {errorMessage}
    </Alert>
  );
}
