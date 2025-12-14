"use client";

import { Button } from "@/components/ui/button";
import Link from "next/link";

/**
 * Call to Action Section Component
 * 
 * Final CTA section for the landing page.
 */
export function CTASection() {
  return (
    <section className="py-16 sm:py-20 bg-zinc-50 dark:bg-zinc-950 -mt-px">
      <div className="mx-auto max-w-5xl px-6">
        <div className="space-y-6 text-center">
          <h2 className="text-foreground text-balance text-3xl font-semibold lg:text-4xl text-zinc-900 dark:text-zinc-100">
            Ready to Transform Your Law Firm?
          </h2>
          <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
            Join leading law firms using LexiqAI to streamline communication and
            improve client satisfaction.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/signup">Get Started</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/pricing">View Pricing</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
