"use client";

import * as React from "react";
import { Phone, Mail, Archive, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Action Toolbar Component
 * 
 * Toolbar with action buttons for call operations.
 * Features icon buttons (Call, Mail, Archive) and a primary
 * "Export to Clio" button. Positioned top right of detail pane.
 * 
 * @example
 * ```tsx
 * <ActionToolbar
 *   onCall={() => console.log("Call clicked")}
 *   onMail={() => console.log("Mail clicked")}
 *   onArchive={() => console.log("Archive clicked")}
 *   onExport={() => console.log("Export clicked")}
 * />
 * ```
 */

export interface ActionToolbarProps {
  /**
   * Callback when Call button is clicked
   */
  onCall?: () => void;
  /**
   * Callback when Mail button is clicked
   */
  onMail?: () => void;
  /**
   * Callback when Archive button is clicked
   */
  onArchive?: () => void;
  /**
   * Callback when Export to Clio button is clicked
   */
  onExport?: () => void;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Action Toolbar Component
 * 
 * Features:
 * - Button group: Call, Mail, Archive (icon buttons)
 * - Primary action: "Export to Clio" (black button)
 * - Positioned top right of detail pane
 */
export const ActionToolbar = React.memo(function ActionToolbar({
  onCall,
  onMail,
  onArchive,
  onExport,
  className,
}: ActionToolbarProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      {/* Icon Buttons Group */}
      <div className="flex items-center gap-1">
        {/* Call Button */}
        {onCall && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onCall}
            aria-label="Call"
            title="Call"
          >
            <Phone className="h-4 w-4" />
          </Button>
        )}

        {/* Mail Button */}
        {onMail && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onMail}
            aria-label="Send Email"
            title="Send Email"
          >
            <Mail className="h-4 w-4" />
          </Button>
        )}

        {/* Archive Button */}
        {onArchive && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onArchive}
            aria-label="Archive"
            title="Archive"
          >
            <Archive className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Primary Action: Export to Clio */}
      {onExport && (
        <Button
          variant="default"
          onClick={onExport}
          className="gap-2"
          aria-label="Export to Clio"
        >
          <Download className="h-4 w-4" />
          Export to Clio
        </Button>
      )}
    </div>
  );
});

