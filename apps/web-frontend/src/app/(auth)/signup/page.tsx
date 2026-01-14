import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthRedirect } from "@/components/auth/AuthRedirect";
import { SignupForm } from "@/components/auth/SignupForm";
import { Loader2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Sign Up",
  description: "Create a new LexiqAI account to get started with AI-powered voice orchestration for your law firm.",
};

/**
 * Sign up page
 * Redirects authenticated users to dashboard
 * Provides registration form with Microsoft Entra ID integration
 * Wrapped in Suspense for static export compatibility
 */
export default function SignupPage() {
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
        <SignupForm />
      </AuthRedirect>
    </Suspense>
  );
}
