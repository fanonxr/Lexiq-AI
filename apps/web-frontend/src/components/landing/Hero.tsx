"use client";

import Link from "next/link";
import { TextScramble } from "@/components/ui/text-scramble";
import { Button } from "@/components/ui/button";

/**
 * Hero Section Component
 * 
 * Landing page hero section with animated text scramble effect.
 */
export function Hero() {
  return (
    <section className="relative flex min-h-[90vh] flex-col items-center justify-center overflow-hidden px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl text-center">
        {/* Animated Headline */}
        <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
          <TextScramble
            className="block text-zinc-950 dark:text-white font-extrabold"
            duration={1.2}
            speed={0.03}
            trigger={true}
          >
            Enterprise Voice Orchestration
          </TextScramble>
          <br />
          <span className="text-zinc-800 dark:text-zinc-200 font-semibold">
            for the Legal Industry
          </span>
        </h1>

        {/* Value Proposition */}
        <p className="mx-auto mb-10 max-w-2xl text-lg leading-8 text-zinc-600 dark:text-zinc-400 sm:text-xl">
          AI-powered voice assistants that answer calls, manage schedules, and
          integrate seamlessly with your legal CRM. Transform your law firm's
          communication workflow.
        </p>

        {/* CTAs */}
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href="/signup">Get Started</Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="w-full sm:w-auto">
            <Link href="/pricing">View Pricing</Link>
          </Button>
        </div>

        {/* Trust Indicators */}
        <div className="mt-12 flex flex-wrap items-center justify-center gap-8 text-sm text-zinc-500 dark:text-zinc-400">
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>Enterprise Security</span>
          </div>
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>HIPAA Compliant</span>
          </div>
          <div className="flex items-center gap-2">
            <svg
              className="h-5 w-5 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span>24/7 Support</span>
          </div>
        </div>
      </div>
    </section>
  );
}
