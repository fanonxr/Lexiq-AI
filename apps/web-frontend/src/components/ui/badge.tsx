import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground border-border",
      },
      status: {
        success: "border-green-200 text-green-600 bg-green-50",
        error: "border-red-200 text-red-600 bg-red-50",
        warning: "border-amber-200 text-amber-600 bg-amber-50",
        info: "border-blue-200 text-blue-600 bg-blue-50",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  /**
   * Whether to show a pulsing dot indicator (for status badges)
   * @default false
   */
  pulse?: boolean
  /**
   * Color of the pulse dot (only used when pulse is true)
   * @default "green"
   */
  pulseColor?: "green" | "red" | "amber" | "blue"
}

function Badge({ 
  className, 
  variant, 
  status,
  pulse = false,
  pulseColor = "green",
  children,
  ...props 
}: BadgeProps) {
  const pulseColorClasses = {
    green: "bg-green-500",
    red: "bg-red-500",
    amber: "bg-amber-500",
    blue: "bg-blue-500",
  }

  return (
    <div 
      className={cn(
        badgeVariants({ variant, status }),
        pulse && "gap-2",
        className
      )} 
      {...props}
    >
      {pulse && (
        <span 
          className={cn(
            "h-2 w-2 rounded-full",
            pulseColorClasses[pulseColor],
            "animate-pulse"
          )} 
          aria-hidden="true"
        />
      )}
      {children}
    </div>
  )
}

export { Badge, badgeVariants }
