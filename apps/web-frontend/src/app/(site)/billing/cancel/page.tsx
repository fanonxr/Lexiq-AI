"use client";

import { useRouter } from "next/navigation";
import { XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Billing cancel page
 * Shown when user cancels Stripe checkout
 */
export default function BillingCancelPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="flex justify-center">
            <XCircle className="h-12 w-12 text-zinc-600 dark:text-zinc-400" />
          </div>
          <h2 className="mt-4 text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            Checkout Cancelled
          </h2>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Your checkout was cancelled. No charges were made.
          </p>
          <div className="mt-6 space-y-2">
            <Button
              onClick={() => router.push("/pricing")}
              className="w-full"
            >
              Return to Pricing
            </Button>
            <Button
              onClick={() => router.push("/dashboard")}
              className="w-full"
              variant="outline"
            >
              Go to Dashboard
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
