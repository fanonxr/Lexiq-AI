import type { Metadata } from "next";

// Force dynamic rendering because layout uses client components
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Recordings",
  description: "View and manage your call recordings, transcripts, and analytics.",
};

/**
 * Recordings page
 * Will be fully implemented in later phases
 */
export default function RecordingsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold">Recordings</h1>
      <p className="mt-4 text-zinc-600 dark:text-zinc-400">
        View and manage your call recordings here.
      </p>
    </div>
  );
}
