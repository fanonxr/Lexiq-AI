"use client";

/**
 * Global Keyboard Navigation Hook
 * 
 * Provides keyboard shortcuts for global navigation and actions.
 * 
 * Features:
 * - Esc: Close modals/drawers
 * - Cmd/Ctrl + K: Command palette (placeholder for future implementation)
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   useKeyboardNavigation({
 *     onEscape: () => closeModal(),
 *     onCommandPalette: () => openCommandPalette(),
 *   });
 * }
 * ```
 */

import { useEffect, useCallback } from "react";

export interface KeyboardNavigationOptions {
  /**
   * Callback when Escape key is pressed
   */
  onEscape?: () => void;
  /**
   * Callback when Cmd/Ctrl + K is pressed (command palette)
   */
  onCommandPalette?: () => void;
  /**
   * Whether to ignore keyboard shortcuts when typing in inputs
   * @default true
   */
  ignoreInputs?: boolean;
  /**
   * Whether the keyboard navigation is enabled
   * @default true
   */
  enabled?: boolean;
}

/**
 * Global keyboard navigation hook
 * 
 * Handles global keyboard shortcuts like Esc and Cmd/Ctrl + K
 */
export function useKeyboardNavigation({
  onEscape,
  onCommandPalette,
  ignoreInputs = true,
  enabled = true,
}: KeyboardNavigationOptions = {}) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Ignore if typing in input/textarea
      if (ignoreInputs) {
        if (
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement ||
          (e.target instanceof HTMLElement && e.target.isContentEditable)
        ) {
          return;
        }
      }

      // Escape key: Close modals/drawers
      if (e.key === "Escape" && onEscape) {
        e.preventDefault();
        onEscape();
        return;
      }

      // Cmd/Ctrl + K: Command palette
      if (
        (e.metaKey || e.ctrlKey) &&
        e.key === "k" &&
        onCommandPalette
      ) {
        e.preventDefault();
        onCommandPalette();
        return;
      }
    },
    [enabled, ignoreInputs, onEscape, onCommandPalette]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled, handleKeyDown]);
}

