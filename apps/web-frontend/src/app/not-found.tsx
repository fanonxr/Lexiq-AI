import Link from "next/link";

/**
 * 404 Not Found page
 */
export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-6xl font-bold mb-4">404</h1>
        <h2 className="text-2xl font-semibold mb-4">Page Not Found</h2>
        <p className="text-zinc-600 dark:text-zinc-400 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/"
            className="rounded-lg bg-foreground px-6 py-3 text-background transition-colors hover:bg-zinc-800 dark:hover:bg-zinc-200"
          >
            Go Home
          </Link>
          <Link
            href="/dashboard"
            className="rounded-lg border border-zinc-200 px-6 py-3 transition-colors hover:bg-zinc-100 dark:border-zinc-800 dark:hover:bg-zinc-900"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
