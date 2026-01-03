"use client";

/**
 * Card Component
 * 
 * A container component for grouping related content.
 * Follows the LexiqAI design system with border-based structure (no shadows).
 * 
 * @example
 * ```tsx
 * <Card hoverable>
 *   <CardHeader>
 *     <CardTitle>Title</CardTitle>
 *   </CardHeader>
 *   <CardContent>Content here</CardContent>
 * </Card>
 * ```
 */

import { type HTMLAttributes } from "react";
import { clsx } from "clsx";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Whether the card has a hover effect
   * Adds border color transition on hover (border-zinc-400)
   * @default false
   */
  hoverable?: boolean;
  /**
   * Whether the card has padding
   * @default true
   */
  padded?: boolean;
  /**
   * Border radius size
   * @default "lg" (8px)
   */
  radius?: "md" | "lg";
}

/**
 * Card container component
 * Uses border-based structure (no shadows) per design system
 */
export function Card({
  hoverable = false,
  padded = true,
  radius = "lg",
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={clsx(
        // Base styles - border-based structure (no shadows)
        // Light mode: white background, dark mode: dark background
        "border border-zinc-200 bg-white text-zinc-900",
        "dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100",
        // Border radius - matches design system (rounded-md: 6px, rounded-lg: 8px)
        radius === "md" ? "rounded-md" : "rounded-lg",
        // Hover effect - subtle border color transition
        hoverable && "transition-colors hover:border-zinc-400 dark:hover:border-zinc-600",
        // Padding
        padded && "p-6",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Card header component
 */
export function CardHeader({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx("mb-4 flex flex-col space-y-1.5", className)}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Card title component
 */
export function CardTitle({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={clsx(
        "text-2xl font-semibold leading-none tracking-tight text-zinc-900 dark:text-zinc-100",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

/**
 * Card description component
 */
export function CardDescription({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={clsx(
        "text-sm text-zinc-600 dark:text-zinc-400",
        className
      )}
      {...props}
    >
      {children}
    </p>
  );
}

/**
 * Card content component
 */
export function CardContent({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx("", className)} {...props}>
      {children}
    </div>
  );
}

/**
 * Card footer component
 */
export function CardFooter({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx("mt-4 flex items-center", className)}
      {...props}
    >
      {children}
    </div>
  );
}
