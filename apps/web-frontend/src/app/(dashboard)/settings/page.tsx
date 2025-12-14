import type { Metadata } from "next";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Settings",
  description: "Manage your LexiqAI account settings, preferences, and integrations.",
};

/**
 * Settings page
 * Will be fully implemented in later phases
 */
export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold">Settings</h1>
      <p className="mt-4 text-zinc-600 dark:text-zinc-400">
        User settings and preferences will be available here.
      </p>
    </div>
  );
}
