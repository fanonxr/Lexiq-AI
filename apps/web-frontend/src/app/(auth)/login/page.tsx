import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthRedirect } from "@/components/auth/AuthRedirect";
import { LoginForm } from "@/components/auth/LoginForm";
import { Loader2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Sign In",
  description: "Sign in to your LexiqAI account to access your dashboard and manage your voice orchestration settings.",
};

/**
 * Login page
 * Redirects authenticated users to dashboard
 * Provides login form with Microsoft Entra ID integration
 * Wrapped in Suspense for static export compatibility
 */
export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-zinc-600 dark:text-zinc-400 mx-auto mb-4" />
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Loading...</p>
        </div>
      </div>
    }>
      <AuthRedirect>
        <LoginForm />
      </AuthRedirect>
    </Suspense>
  );
}
