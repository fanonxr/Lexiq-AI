"use client";

/**
 * Form Button Component
 * 
 * Button component optimized for form submissions with loading states.
 * 
 * @example
 * ```tsx
 * <FormButton
 *   type="submit"
 *   isLoading={isSubmitting}
 *   disabled={!isValid}
 * >
 *   Submit
 * </FormButton>
 * ```
 */

import { Button, type ButtonProps } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export interface FormButtonProps extends Omit<ButtonProps, "type"> {
  /**
   * Button type
   * @default "submit"
   */
  type?: "submit" | "button" | "reset";
  /**
   * Whether the form is being submitted
   * @default false
   */
  isLoading?: boolean;
  /**
   * Loading text to display
   */
  loadingText?: string;
}

/**
 * Form button component with loading states
 */
export function FormButton({
  type = "submit",
  isLoading = false,
  loadingText,
  disabled,
  children,
  className,
  ...props
}: FormButtonProps) {
  return (
    <Button
      type={type}
      disabled={disabled || isLoading}
      className={className}
      {...props}
    >
      {isLoading && (
        <LoadingSpinner size="sm" className="mr-2" />
      )}
      {isLoading && loadingText ? loadingText : children}
    </Button>
  );
}
