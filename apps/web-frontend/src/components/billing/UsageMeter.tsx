"use client";

import { Progress } from "@/components/ui/progress";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Alert } from "@/components/ui/Alert";

interface UsageMeterProps {
  current: number;
  limit: number;
  overageRate: number;
  unit?: string;
}

/**
 * Usage Meter Component
 * 
 * Displays usage statistics with progress bar and overage warnings.
 * Shows warnings at 80% and 100% usage thresholds.
 */
export function UsageMeter({ 
  current, 
  limit, 
  overageRate,
  unit = "minutes"
}: UsageMeterProps) {
  // Handle unlimited plans (limit = 0 or null)
  const isUnlimited = limit === 0 || !limit;
  const percentage = isUnlimited ? 0 : Math.min(100, (current / limit) * 100);
  const isOverLimit = !isUnlimited && current > limit;
  const overageMinutes = isOverLimit ? current - limit : 0;
  const overageCost = overageMinutes * overageRate;
  const isWarning = !isUnlimited && percentage >= 80 && !isOverLimit;

  return (
    <div className="space-y-4">
      {/* Usage Display */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
            {unit === "minutes" ? "Minutes Used" : "Usage"}
          </span>
          <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            {current.toLocaleString()} / {isUnlimited ? "∞" : limit.toLocaleString()} {unit}
          </span>
        </div>
        <Progress 
          value={isUnlimited ? 0 : Math.min(100, percentage)} 
          className={isOverLimit ? "bg-red-200 dark:bg-red-900" : ""}
        />
        {!isUnlimited && (
          <div className="text-xs text-zinc-500 dark:text-zinc-500 mt-1">
            {percentage.toFixed(1)}% of included {unit}
          </div>
        )}
      </div>

      {/* Overage Warning */}
      {isOverLimit && (
        <Alert variant="error" title="Overage Charges">
          <div className="text-sm">
            You've exceeded your included {unit} by {overageMinutes.toLocaleString()} {unit}.
            <br />
            Estimated overage cost: ${overageCost.toFixed(2)} ({overageMinutes.toLocaleString()} {unit} × ${overageRate}/{unit})
          </div>
        </Alert>
      )}

      {/* Warning at 80% */}
      {isWarning && (
        <Alert variant="warning" title="Approaching Usage Limit">
          <div className="text-sm">
            You've used {percentage.toFixed(0)}% of your included {unit}. 
            Consider upgrading your plan to avoid overage charges.
          </div>
        </Alert>
      )}

      {/* Success message when usage is low */}
      {!isUnlimited && percentage < 50 && (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <CheckCircle2 className="h-4 w-4" />
          <span>Usage is within normal range</span>
        </div>
      )}
    </div>
  );
}
