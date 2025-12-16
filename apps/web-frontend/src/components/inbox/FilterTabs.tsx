"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Filter Tabs Component
 * 
 * Sticky header with filter tabs for call list.
 * Tabs: All, Unread, Leads, Spam with badge counts.
 * 
 * @example
 * ```tsx
 * <FilterTabs
 *   activeFilter="all"
 *   onFilterChange={(filter) => setFilter(filter)}
 *   counts={{ all: 50, unread: 12, leads: 8, spam: 2 }}
 * />
 * ```
 */

export type FilterType = "all" | "unread" | "leads" | "spam";

export interface FilterTabsProps {
  /**
   * Currently active filter
   */
  activeFilter: FilterType;
  /**
   * Callback when filter changes
   */
  onFilterChange: (filter: FilterType) => void;
  /**
   * Optional badge counts for each filter
   */
  counts?: {
    all: number;
    unread: number;
    leads: number;
    spam: number;
  };
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * Filter Tabs Component
 * 
 * Features:
 * - Sticky header at top of call list
 * - Tabs: All, Unread, Leads, Spam
 * - Active state styling
 * - Badge counts for unread
 */
export function FilterTabs({
  activeFilter,
  onFilterChange,
  counts,
  className,
}: FilterTabsProps) {
  const tabs: { id: FilterType; label: string }[] = [
    { id: "all", label: "All" },
    { id: "unread", label: "Unread" },
    { id: "leads", label: "Leads" },
    { id: "spam", label: "Spam" },
  ];

  return (
    <div
      className={cn(
        "sticky top-0 z-10 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800",
        className
      )}
      role="tablist"
      aria-label="Filter calls by status"
    >
      <div className="flex items-center gap-1 px-2 py-2">
        {tabs.map((tab) => {
          const isActive = activeFilter === tab.id;
          const count = counts?.[tab.id];

          return (
            <button
              key={tab.id}
              onClick={() => onFilterChange(tab.id)}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                isActive
                  ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
              )}
              aria-selected={isActive}
              aria-label={`${tab.label}${count !== undefined && count > 0 ? `, ${count} items` : ""}`}
              role="tab"
              tabIndex={isActive ? 0 : -1}
            >
              <span className="flex items-center gap-2">
                {tab.label}
                {count !== undefined && count > 0 && (
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      isActive
                        ? "border-white/20 text-white/90 dark:border-zinc-900/20 dark:text-zinc-900/90"
                        : ""
                    )}
                  >
                    {count}
                  </Badge>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

