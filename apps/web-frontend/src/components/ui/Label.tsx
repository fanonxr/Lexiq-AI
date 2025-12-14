"use client";

/**
 * Label Component
 * 
 * A form label component with accessibility features.
 * 
 * @example
 * ```tsx
 * <Label htmlFor="email" required>
 *   Email Address
 * </Label>
 * ```
 */

import { forwardRef, type LabelHTMLAttributes } from "react";
import { clsx } from "clsx";

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  /**
   * Whether the associated field is required
   * @default false
   */
  required?: boolean;
  /**
   * Optional helper text to display
   */
  helperText?: string;
}

/**
 * Label component for form inputs
 */
export const Label = forwardRef<HTMLLabelElement, LabelProps>(
  ({ required = false, helperText, className, children, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        <label
          ref={ref}
          className={clsx(
            "block text-sm font-medium text-zinc-700 dark:text-zinc-300",
            className
          )}
          {...props}
        >
          {children}
          {required && (
            <span className="text-red-500 ml-1" aria-label="required">
              *
            </span>
          )}
        </label>
        {helperText && (
          <span className="text-xs text-zinc-500 dark:text-zinc-400">
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Label.displayName = "Label";
