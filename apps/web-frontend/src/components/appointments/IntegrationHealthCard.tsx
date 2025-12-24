"use client";

import * as React from "react";
import { Calendar, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

/**
 * Integration Health Card Component
 * 
 * Slim banner displaying calendar integration status (Outlook/Google)
 * with connection status, last sync time, and refresh button.
 * 
 * @example
 * ```tsx
 * <IntegrationHealthCard
 *   integration="outlook"
 *   lastSynced={new Date()}
 *   onRefresh={() => syncAppointments()}
 * />
 * ```
 */

export type IntegrationType = "outlook" | "google";

export interface IntegrationHealthCardProps {
  /**
   * Calendar integration type
   */
  integration: IntegrationType;
  /**
   * Last sync timestamp
   */
  lastSynced: Date | null;
  /**
   * Callback when refresh is clicked
   */
  onRefresh?: () => void | Promise<void>;
  /**
   * Callback when connect is clicked
   */
  onConnect?: () => void | Promise<void>;
  /**
   * Whether sync is in progress
   * @default false
   */
  isSyncing?: boolean;
  /**
   * Whether the integration is connected
   * @default true
   */
  isConnected?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Get integration display name
 */
function getIntegrationName(integration: IntegrationType): string {
  switch (integration) {
    case "outlook":
      return "Outlook";
    case "google":
      return "Google Calendar";
    default:
      return "Calendar";
  }
}

/**
 * Integration Health Card Component
 * 
 * Features:
 * - Slim banner at top of page
 * - Outlook/Google logo + "Connected" (Green Dot)
 * - Text: "Last synced X minutes ago"
 * - Click to refresh
 */
export function IntegrationHealthCard({
  integration,
  lastSynced,
  onRefresh,
  onConnect,
  isSyncing = false,
  isConnected = true,
  className,
}: IntegrationHealthCardProps) {
  const formattedTime = lastSynced
    ? formatDistanceToNow(lastSynced, { addSuffix: true })
    : "Never";

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4 rounded-lg border border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900",
        className
      )}
    >
      {/* Left side: Integration info */}
      <div className="flex items-center gap-3">
        {/* Calendar Icon */}
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Calendar className="h-4 w-4" />
        </div>

        {/* Integration name and status */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-foreground">
            {getIntegrationName(integration)}
          </span>
          {isConnected ? (
            <Badge status="success" className="gap-1.5">
              <span className="h-2 w-2 rounded-full bg-green-500" />
              Connected
            </Badge>
          ) : (
            <Badge status="error" className="gap-1.5">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              Disconnected
            </Badge>
          )}
        </div>

        {/* Last synced time */}
        {isConnected && (
          <span className="text-sm text-muted-foreground">
            Last synced {formattedTime}
          </span>
        )}
      </div>

      {/* Right side: Connect or Refresh button */}
      {!isConnected && onConnect ? (
        <Button
          variant="outline"
          size="sm"
          onClick={onConnect}
          className="gap-2"
          aria-label={`Connect ${getIntegrationName(integration)}`}
        >
          Connect {getIntegrationName(integration)}
        </Button>
      ) : (
        onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            disabled={isSyncing}
            className="gap-2"
            aria-label="Refresh calendar sync"
          >
            {isSyncing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="hidden sm:inline">Syncing...</span>
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                <span className="hidden sm:inline">Refresh</span>
              </>
            )}
          </Button>
        )
      )}
    </div>
  );
}

