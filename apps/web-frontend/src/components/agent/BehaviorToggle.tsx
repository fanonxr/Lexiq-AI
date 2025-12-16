"use client";

import * as React from "react";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

/**
 * Behavior Toggle Component
 * 
 * Switch component with label and description for agent behavior settings.
 * Layout: Text label on left, description below in smaller gray text,
 * Switch on far right.
 * 
 * @example
 * ```tsx
 * <BehaviorToggle
 *   label="Auto-respond to voicemails"
 *   description="Automatically send follow-up emails for missed calls"
 *   checked={autoRespond}
 *   onChange={setAutoRespond}
 * />
 * ```
 */

export interface BehaviorToggleProps {
  /**
   * Label text (displayed on the left)
   */
  label: string;
  /**
   * Description text (displayed below label in smaller gray text)
   */
  description: string;
  /**
   * Whether the toggle is checked
   */
  checked: boolean;
  /**
   * Callback when toggle state changes
   */
  onChange: (checked: boolean) => void;
  /**
   * Whether the toggle is disabled
   * @default false
   */
  disabled?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Behavior Toggle Component
 * 
 * Features:
 * - Switch component with label and description
 * - Layout: Text label on left, description below, Switch on far right
 * - Clean, minimal design
 */
export function BehaviorToggle({
  label,
  description,
  checked,
  onChange,
  disabled = false,
  className,
}: BehaviorToggleProps) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-4 py-3",
        className
      )}
    >
      {/* Left side: Label and Description */}
      <div className="flex-1 min-w-0">
        <label
          htmlFor={`behavior-toggle-${label.toLowerCase().replace(/\s+/g, "-")}`}
          className={cn(
            "block text-sm font-medium text-foreground cursor-pointer",
            disabled && "cursor-not-allowed opacity-50"
          )}
        >
          {label}
        </label>
        <p className="mt-1 text-xs text-muted-foreground">
          {description}
        </p>
      </div>

      {/* Right side: Switch */}
      <div className="flex-shrink-0">
        <Switch
          id={`behavior-toggle-${label.toLowerCase().replace(/\s+/g, "-")}`}
          checked={checked}
          onCheckedChange={onChange}
          disabled={disabled}
          aria-label={label}
          aria-describedby={`behavior-toggle-desc-${label.toLowerCase().replace(/\s+/g, "-")}`}
        />
        <span
          id={`behavior-toggle-desc-${label.toLowerCase().replace(/\s+/g, "-")}`}
          className="sr-only"
        >
          {description}
        </span>
      </div>
    </div>
  );
}

