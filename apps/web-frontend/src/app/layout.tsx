import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { AuthProvider } from "@/components/providers/AuthProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "LexiqAI - Enterprise Voice Orchestration for Legal Industry",
    template: "%s | LexiqAI",
  },
  description:
    "AI-powered voice assistant for law firms. Answer calls, manage schedules, and integrate with legal CRMs.",
  keywords: ["legal tech", "AI assistant", "voice orchestration", "law firm software"],
  authors: [{ name: "LexiqAI" }],
  creator: "LexiqAI",
  metadataBase: new URL(
    typeof process !== "undefined" && process.env.NEXT_PUBLIC_APP_URL
      ? process.env.NEXT_PUBLIC_APP_URL
      : "http://localhost:3000"
  ),
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "/",
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
