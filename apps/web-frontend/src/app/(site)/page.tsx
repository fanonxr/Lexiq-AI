import type { Metadata } from "next";
import { Hero, Features, HowItWorks, Testimonials, CTASection } from "@/components/landing";

export const metadata: Metadata = {
  title: "Home",
  description:
    "LexiqAI - Enterprise-grade voice orchestration platform for the legal industry. AI-powered assistants that answer calls, manage schedules, and integrate with legal CRMs.",
};

/**
 * Landing page - Marketing site home
 * Complete landing page with all sections
 */
export default function Home() {
  return (
    <>
      <Hero />
      <Features />
      <HowItWorks />
      <Testimonials />
      <CTASection />
    </>
  );
}
