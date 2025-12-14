import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "LexiqAI - Enterprise Voice Orchestration for Legal Industry",
    template: "%s | LexiqAI",
  },
  description:
    "AI-powered voice assistant for law firms. Answer calls, manage schedules, and integrate with legal CRMs.",
  keywords: [
    "legal tech",
    "AI assistant",
    "voice orchestration",
    "law firm software",
    "legal CRM",
    "attorney technology",
  ],
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "LexiqAI",
    title: "LexiqAI - Enterprise Voice Orchestration for Legal Industry",
    description:
      "AI-powered voice assistant for law firms. Answer calls, manage schedules, and integrate with legal CRMs.",
  },
  twitter: {
    card: "summary_large_image",
    title: "LexiqAI - Enterprise Voice Orchestration for Legal Industry",
    description:
      "AI-powered voice assistant for law firms. Answer calls, manage schedules, and integrate with legal CRMs.",
  },
};

import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";

/**
 * Marketing site layout
 * Includes navbar and footer for public-facing pages
 */
export default function SiteLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
