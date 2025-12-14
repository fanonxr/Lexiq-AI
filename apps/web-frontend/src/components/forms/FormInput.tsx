"use client";

/**
 * Form Input Component
 * 
 * Enhanced input component for forms with validation integration.
 * Works with or without react-hook-form.
 * 
 * @example
 * ```tsx
 * <FormInput
 *   name="email"
 *   label="Email"
 *   type="email"
 *   error={errors.email}
 * />
 * ```
 */

import { forwardRef } from "react";
import { Input, type InputProps } from "@/components/ui/Input";

/**
 * Field error type (compatible with react-hook-form if installed)
 */
export interface FieldError {
  message?: string;
  type?: string;
}

export interface FormInputProps extends Omit<InputProps, "error" | "hasError"> {
  /**
   * Field name for form registration
   */
  name: string;
  /**
   * Error from form validation (FieldError or string)
   */
  error?: FieldError | string | null;
  /**
   * Register function from react-hook-form (optional, requires react-hook-form)
   * If provided, will auto-register the field
   */
  register?: (name: string, rules?: any) => any;
  /**
   * Validation rules (if not using react-hook-form)
   */
  rules?: {
    required?: boolean | string;
    minLength?: { value: number; message: string };
    maxLength?: { value: number; message: string };
    pattern?: { value: RegExp; message: string };
    validate?: (value: any) => boolean | string;
  };
}

/**
 * Form input component with validation support
 */
export const FormInput = forwardRef<HTMLInputElement, FormInputProps>(
  (
    {
      name,
      error,
      register,
      rules,
      label,
      required,
      className,
      ...props
    },
    ref
  ) => {
    // Extract error message
    const errorMessage =
      typeof error === "string"
        ? error
        : error?.message || null;

    // Determine if field is required
    const isRequired =
      required ||
      (typeof rules?.required === "string" ? true : rules?.required) ||
      false;

    // Register with react-hook-form if provided
    const registerProps = register
      ? register(name, rules)
      : {};

    return (
      <Input
        ref={ref}
        id={name}
        name={name}
        label={label}
        error={errorMessage || undefined}
        hasError={!!errorMessage}
        required={isRequired}
        className={className}
        {...registerProps}
        {...props}
      />
    );
  }
);

FormInput.displayName = "FormInput";
