"use client";

/**
 * Card Component
 * 
 * A container component for grouping related content.
 * 
 * @example
 * ```tsx
 * <Card>
 *   <CardHeader>
 *     <CardTitle>Title</CardTitle>
 *   </CardHeader>
 *   <CardContent>Content here</CardContent>
 * </CardHeader>
 * </Card>
 * ```
 */

import { type HTMLAttributes, type ReactNode } from "react";
import { clsx } from "clsx";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Whether the card has a hover effect
   * @default false
   */
  hoverable?: boolean;
  /**
   * Whether the card has padding
   * @default true
   */
  padded?: boolean;
}

/**
 * Card container component
 */
export function Card({
  hoverable = false,
  padded = true,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={clsx(
        "rounded-lg border border-zinc-200 bg-white",
        "dark:border-zinc-800 dark:bg-zinc-900",
        hoverable && "transition-shadow hover:shadow-md",
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
        "text-sm text-zinc-500 dark:text-zinc-400",
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
