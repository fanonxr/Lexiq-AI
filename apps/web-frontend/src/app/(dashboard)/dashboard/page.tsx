import type { Metadata } from "next";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Dashboard",
  description: "View your LexiqAI dashboard, recent activity, and quick actions.",
};

/**
 * Dashboard home page
 * Will be fully implemented in later phases
 */
export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <p className="mt-4 text-zinc-600 dark:text-zinc-400">
        Welcome to your LexiqAI dashboard. This page will be fully implemented in
        later phases.
      </p>
    </div>
  );
}
