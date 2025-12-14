import type { Metadata } from "next";
import { AuthRedirect } from "@/components/auth/AuthRedirect";
import { SignupForm } from "@/components/auth/SignupForm";

// Force dynamic rendering because we use useSearchParams()
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Sign Up",
  description: "Create a new LexiqAI account to get started with AI-powered voice orchestration for your law firm.",
};

/**
 * Sign up page
 * Redirects authenticated users to dashboard
 * Provides registration form with Microsoft Entra ID integration
 */
export default function SignupPage() {
  return (
    <AuthRedirect>
      <SignupForm />
    </AuthRedirect>
  );
}
