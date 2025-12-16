"use client"

import * as React from "react"
import { DayPicker, DateRange } from "react-day-picker"
import { format } from "date-fns"
import { CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "./button"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"

import "react-day-picker/dist/style.css"

/**
 * DateRangePicker Component
 * 
 * Minimal date range picker matching Linear/Vercel design style.
 * Supports preset ranges (Last 7 days, Last 30 days, etc.)
 * Positioned in dashboard header.
 * 
 * @example
 * ```tsx
 * <DateRangePicker
 *   dateRange={range}
 *   onDateRangeChange={setRange}
 * />
 * ```
 */

export interface DateRangePickerProps {
  /**
   * Selected date range
   */
  dateRange?: DateRange
  /**
   * Callback when date range changes
   */
  onDateRangeChange?: (range: DateRange | undefined) => void
  /**
   * Additional CSS classes
   */
  className?: string
  /**
   * Placeholder text
   */
  placeholder?: string
}

const PRESET_RANGES = [
  {
    label: "Last 7 days",
    value: 7,
  },
  {
    label: "Last 30 days",
    value: 30,
  },
  {
    label: "Last 90 days",
    value: 90,
  },
  {
    label: "This month",
    value: "thisMonth",
  },
  {
    label: "Last month",
    value: "lastMonth",
  },
] as const

export function DateRangePicker({
  dateRange,
  onDateRangeChange,
  className,
  placeholder = "Pick a date range",
}: DateRangePickerProps) {
  const [open, setOpen] = React.useState(false)

  const handlePresetClick = (preset: typeof PRESET_RANGES[number]) => {
    const today = new Date()
    let from: Date
    let to: Date = today

    if (preset.value === "thisMonth") {
      from = new Date(today.getFullYear(), today.getMonth(), 1)
    } else if (preset.value === "lastMonth") {
      const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      from = lastMonth
      to = new Date(today.getFullYear(), today.getMonth(), 0)
    } else {
      from = new Date(today)
      from.setDate(from.getDate() - preset.value)
    }

    onDateRangeChange?.({ from, to })
    setOpen(false)
  }

  const displayText = React.useMemo(() => {
    if (!dateRange?.from) {
      return placeholder
    }
    if (dateRange.from && !dateRange.to) {
      return format(dateRange.from, "LLL dd, y")
    }
    if (dateRange.from && dateRange.to) {
      return `${format(dateRange.from, "LLL dd, y")} - ${format(dateRange.to, "LLL dd, y")}`
    }
    return placeholder
  }, [dateRange, placeholder])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "w-[280px] justify-start text-left font-normal",
            !dateRange && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {displayText}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <div className="flex">
          {/* Preset ranges sidebar */}
          <div className="border-r border-border p-3">
            <div className="space-y-1">
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                Presets
              </div>
              {PRESET_RANGES.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => handlePresetClick(preset)}
                  className={cn(
                    "block w-full rounded-md px-2 py-1.5 text-left text-sm",
                    "hover:bg-muted transition-colors",
                    "text-foreground"
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Calendar */}
          <DayPicker
            mode="range"
            selected={dateRange}
            onSelect={onDateRangeChange}
            numberOfMonths={2}
            className="p-3"
            classNames={{
              months: "flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0",
              month: "space-y-4",
              caption: "flex justify-center pt-1 relative items-center",
              caption_label: "text-sm font-medium",
              nav: "space-x-1 flex items-center",
              nav_button: cn(
                "h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100",
                "border border-border rounded-md",
                "hover:bg-muted transition-colors"
              ),
              nav_button_previous: "absolute left-1",
              nav_button_next: "absolute right-1",
              table: "w-full border-collapse space-y-1",
              head_row: "flex",
              head_cell: "text-muted-foreground rounded-md w-9 font-normal text-[0.8rem]",
              row: "flex w-full mt-2",
              cell: "h-9 w-9 text-center text-sm p-0 relative [&:has([aria-selected].day-range-end)]:rounded-r-md [&:has([aria-selected].day-outside)]:bg-muted/50 [&:has([aria-selected])]:bg-muted first:[&:has([aria-selected])]:rounded-l-md last:[&:has([aria-selected])]:rounded-r-md focus-within:relative focus-within:z-20",
              day: cn(
                "h-9 w-9 p-0 font-normal aria-selected:opacity-100",
                "rounded-md hover:bg-muted transition-colors",
                "aria-selected:bg-primary aria-selected:text-primary-foreground"
              ),
              day_range_end: "day-range-end",
              day_selected: "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground",
              day_today: "bg-muted text-foreground",
              day_outside: "day-outside text-muted-foreground opacity-50 aria-selected:bg-muted/50 aria-selected:text-muted-foreground aria-selected:opacity-30",
              day_disabled: "text-muted-foreground opacity-50",
              day_range_middle: "aria-selected:bg-muted aria-selected:text-foreground",
              day_hidden: "invisible",
            }}
            components={{
              Chevron: ({ orientation }) => {
                const Icon = orientation === "left" ? ChevronLeft : ChevronRight
                return <Icon className="h-4 w-4" />
              },
            }}
          />
        </div>
      </PopoverContent>
    </Popover>
  )
}

