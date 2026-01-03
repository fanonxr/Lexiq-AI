"use client";

import { useEffect } from "react";
import Link from "next/link";
import { logger } from "@/lib/logger";

/**
 * Error boundary page
 * This component must be a Client Component
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    logger.error("Application error", error, {
      digest: error.digest,
    });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h1 className="text-4xl font-bold mb-4">Something went wrong!</h1>
        <p className="text-zinc-600 dark:text-zinc-400 mb-8">
          We encountered an unexpected error. Please try again or contact support if the problem persists.
        </p>
        
        {error.digest && (
          <p className="text-sm text-zinc-500 dark:text-zinc-500 mb-4">
            Error ID: {error.digest}
          </p>
        )}
        
        <div className="flex gap-4 justify-center">
          <button
            onClick={reset}
            className="rounded-lg bg-foreground px-6 py-3 text-background transition-colors hover:bg-zinc-800 dark:hover:bg-zinc-200"
          >
            Try Again
          </button>
          <Link
            href="/"
            className="rounded-lg border border-zinc-200 px-6 py-3 transition-colors hover:bg-zinc-100 dark:border-zinc-800 dark:hover:bg-zinc-900"
          >
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
