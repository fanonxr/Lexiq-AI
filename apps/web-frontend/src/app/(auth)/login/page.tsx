import type { Metadata } from "next";
import { AuthRedirect } from "@/components/auth/AuthRedirect";
import { LoginForm } from "@/components/auth/LoginForm";

// Force dynamic rendering because we use useSearchParams()
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Sign In",
  description: "Sign in to your LexiqAI account to access your dashboard and manage your voice orchestration settings.",
};

/**
 * Login page
 * Redirects authenticated users to dashboard
 * Provides login form with Microsoft Entra ID integration
 */
export default function LoginPage() {
  return (
    <AuthRedirect>
      <LoginForm />
    </AuthRedirect>
  );
}
