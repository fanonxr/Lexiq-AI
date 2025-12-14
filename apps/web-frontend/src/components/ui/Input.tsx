"use client";

/**
 * Input Component
 * 
 * A versatile form input component with validation states and accessibility.
 * 
 * @example
 * ```tsx
 * <Input
 *   type="email"
 *   label="Email"
 *   error="Invalid email"
 *   required
 * />
 * ```
 */

import { forwardRef, type InputHTMLAttributes } from "react";
import { clsx } from "clsx";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /**
   * Label text for the input (for accessibility)
   */
  label?: string;
  /**
   * Error message to display
   */
  error?: string;
  /**
   * Helper text to display below the input
   */
  helperText?: string;
  /**
   * Whether the input has a validation error
   */
  hasError?: boolean;
  /**
   * Left icon/element to display inside the input
   */
  leftElement?: React.ReactNode;
  /**
   * Right icon/element to display inside the input
   */
  rightElement?: React.ReactNode;
}

/**
 * Input component with validation states and accessibility
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      hasError,
      leftElement,
      rightElement,
      className,
      id,
      required,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const errorId = error ? `${inputId}-error` : undefined;
    const helperId = helperText ? `${inputId}-helper` : undefined;
    const ariaDescribedBy = [errorId, helperId].filter(Boolean).join(" ") || undefined;

    // Base styles
    const baseStyles = [
      "w-full",
      "px-3 py-2",
      "text-base",
      "bg-white border rounded-lg",
      "transition-colors duration-200",
      "focus:outline-none focus:ring-2 focus:ring-offset-1",
      "disabled:opacity-50 disabled:cursor-not-allowed",
      "placeholder:text-zinc-400",
      "dark:bg-zinc-900 dark:border-zinc-700",
      "dark:placeholder:text-zinc-500",
    ];

    // State styles
    const stateStyles = hasError || error
      ? [
          "border-red-500",
          "focus:border-red-500 focus:ring-red-500",
          "dark:border-red-600",
          "dark:focus:border-red-600 dark:focus:ring-red-600",
        ]
      : [
          "border-zinc-300",
          "focus:border-zinc-500 focus:ring-zinc-500",
          "dark:border-zinc-700",
          "dark:focus:border-zinc-500 dark:focus:ring-zinc-500",
        ];

    const inputClasses = clsx(
      baseStyles,
      stateStyles,
      leftElement && "pl-10",
      rightElement && "pr-10",
      className
    );

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5"
          >
            {label}
            {required && (
              <span className="text-red-500 ml-1" aria-label="required">
                *
              </span>
            )}
          </label>
        )}
        <div className="relative">
          {leftElement && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-500">
              {leftElement}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={inputClasses}
            aria-invalid={hasError || error ? "true" : "false"}
            aria-describedby={ariaDescribedBy}
            aria-required={required}
            {...props}
          />
          {rightElement && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-500">
              {rightElement}
            </div>
          )}
        </div>
        {error && (
          <p
            id={errorId}
            className="mt-1.5 text-sm text-red-600 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={helperId} className="mt-1.5 text-sm text-zinc-500 dark:text-zinc-400">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
