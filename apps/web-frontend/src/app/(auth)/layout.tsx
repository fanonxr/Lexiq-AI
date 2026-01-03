import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: {
    default: "Authentication",
    template: "%s | LexiqAI",
  },
  description: "Sign in or create an account to access LexiqAI",
  robots: {
    index: false, // Don't index auth pages
    follow: false,
  },
  icons: {
    icon: [
      { url: '/icons/lexiq-ai-icon.svg', type: 'image/svg+xml', sizes: '32x32' },
      { url: '/icons/lexiq-ai-icon.svg', type: 'image/svg+xml', sizes: '16x16' },
    ]
  },
};

/**
 * Authentication layout
 * Clean, centered layout for login, signup, and password reset pages
 * 
 * Features:
 * - Centered content with max-width constraint
 * - Branding/logo at top
 * - Minimal design with no navigation
 * - Responsive and mobile-friendly
 * - Consistent styling across all auth pages
 */
export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-2xl">
        {/* Logo/Branding */}
        <div className="mb-8 text-center">
          <Link
            href="/"
            className="inline-block transition-opacity hover:opacity-80"
            aria-label="LexiqAI Home"
          >
            <div className="flex flex-col items-center space-y-2">
              {/* Logo Text */}
              <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                LexiqAI
              </h1>
              {/* Tagline */}
              <p className="text-sm font-medium text-white/80">
                Enterprise Voice Orchestration
              </p>
            </div>
          </Link>
        </div>

        {/* Auth Form Content */}
        <div className="w-full">{children}</div>

        {/* Footer Links */}
        <div className="mt-8 text-center">
          <p className="text-xs text-white/60">
            By continuing, you agree to our{" "}
            <Link
              href="/terms"
              className="font-medium text-white underline hover:text-white/80"
            >
              Terms of Service
            </Link>{" "}
            and{" "}
            <Link
              href="/privacy"
              className="font-medium text-white underline hover:text-white/80"
            >
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
