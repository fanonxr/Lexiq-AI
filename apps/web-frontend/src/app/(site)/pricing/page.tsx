import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Choose the right plan for your law firm. Flexible pricing for LexiqAI voice orchestration platform.",
};

/**
 * Pricing page
 * Will be fully implemented in Phase 4
 */
export default function PricingPage() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Pricing</h1>
        <p className="text-xl text-zinc-600 dark:text-zinc-400">
          Choose the right plan for your law firm
        </p>
      </div>
      
      <div className="grid gap-8 md:grid-cols-3 max-w-5xl mx-auto">
        {/* Pricing cards will be added in Phase 4 */}
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
          <h2 className="text-2xl font-semibold mb-4">Starter</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            Pricing information coming soon
          </p>
        </div>
        
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
          <h2 className="text-2xl font-semibold mb-4">Professional</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            Pricing information coming soon
          </p>
        </div>
        
        <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg p-6">
          <h2 className="text-2xl font-semibold mb-4">Enterprise</h2>
          <p className="text-zinc-600 dark:text-zinc-400">
            Pricing information coming soon
          </p>
        </div>
      </div>
    </div>
  );
}
