"use client";

import * as React from "react";
import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/Label";
import { Button } from "@/components/ui/button";
import { Sparkles, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { logger } from "@/lib/logger";

/**
 * Scripting Input Component
 * 
 * Textarea input with "Magic Wand" icon button for AI improvement
 * and auto-save indicator. Used for agent scripting configuration.
 * 
 * @example
 * ```tsx
 * <ScriptingInput
 *   label="Greeting Script"
 *   placeholder="Enter your greeting..."
 *   value={greeting}
 *   onChange={setGreeting}
 *   onImproveWithAI={() => improveScript()}
 * />
 * ```
 */

export interface ScriptingInputProps {
  /**
   * Current value
   */
  value: string;
  /**
   * Callback when value changes
   */
  onChange: (value: string) => void;
  /**
   * Label for the input
   */
  label: string;
  /**
   * Placeholder text
   */
  placeholder?: string;
  /**
   * Callback when "Improve with AI" is clicked
   */
  onImproveWithAI?: () => void | Promise<void>;
  /**
   * Specific height for the textarea
   * @default "120px"
   */
  height?: string;
  /**
   * Whether to show auto-save indicator
   * @default true
   */
  showAutoSave?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Scripting Input Component
 * 
 * Features:
 * - Textarea with specific height
 * - "Magic Wand" icon button inside input (right side)
 * - "Improve with AI" functionality
 * - Auto-save indicator
 */
export function ScriptingInput({
  value,
  onChange,
  label,
  placeholder,
  onImproveWithAI,
  height = "120px",
  showAutoSave = true,
  className,
}: ScriptingInputProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [isImproving, setIsImproving] = useState(false);

  // Auto-save simulation (debounced)
  useEffect(() => {
    if (!showAutoSave || !value) return;

    setIsSaving(true);
    setIsSaved(false);

    const timer = setTimeout(() => {
      // Simulate auto-save
      setIsSaving(false);
      setIsSaved(true);

      // Hide saved indicator after 2 seconds
      const hideTimer = setTimeout(() => {
        setIsSaved(false);
      }, 2000);

      return () => clearTimeout(hideTimer);
    }, 1000); // Debounce for 1 second

    return () => clearTimeout(timer);
  }, [value, showAutoSave]);

  const handleImproveWithAI = async () => {
    if (!onImproveWithAI || isImproving) return;

    try {
      setIsImproving(true);
      await onImproveWithAI();
    } catch (error) {
      logger.error("Failed to improve script", error instanceof Error ? error : new Error(String(error)));
    } finally {
      setIsImproving(false);
    }
  };

  return (
    <div className={cn("space-y-2", className)}>
      {/* Label */}
      <Label htmlFor={`scripting-input-${label.toLowerCase().replace(/\s+/g, "-")}`}>
        {label}
      </Label>

      {/* Textarea Container with Magic Wand Button */}
      <div className="relative">
        <Textarea
          id={`scripting-input-${label.toLowerCase().replace(/\s+/g, "-")}`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          style={{ height, paddingRight: onImproveWithAI ? "40px" : undefined }}
          className={cn(
            "resize-none",
            // Ensure text doesn't overlap with button
            onImproveWithAI && "pr-10"
          )}
        />

        {/* Magic Wand Button (inside input, right side) */}
        {onImproveWithAI && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className={cn(
              "absolute right-2 top-2 h-8 w-8",
              "text-muted-foreground hover:text-foreground",
              isImproving && "opacity-50 cursor-not-allowed"
            )}
            onClick={handleImproveWithAI}
            disabled={isImproving}
            aria-label="Improve with AI"
            title="Improve with AI"
          >
            {isImproving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
          </Button>
        )}

        {/* Auto-save Indicator (bottom right, below magic wand button) */}
        {showAutoSave && (isSaving || isSaved) && (
          <div
            className={cn(
              "absolute flex items-center gap-1.5 text-xs text-muted-foreground",
              // Position below magic wand button if present, otherwise bottom right
              onImproveWithAI ? "bottom-2 right-12" : "bottom-2 right-2",
              // Smooth fade in/out animations
              "transition-opacity duration-300",
              isSaving ? "opacity-100" : "opacity-100",
              // Fade out when saved indicator disappears
              !isSaved && !isSaving && "opacity-0"
            )}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Saving...</span>
              </>
            ) : isSaved ? (
              <>
                <Check className="h-3 w-3 text-green-600 animate-in fade-in-0 zoom-in-95" />
                <span className="text-green-600 animate-in fade-in-0 zoom-in-95">Saved</span>
              </>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

