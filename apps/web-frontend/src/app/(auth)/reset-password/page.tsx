import type { Metadata } from "next";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";

export const metadata: Metadata = {
  title: "Reset Password",
  description: "Reset your LexiqAI account password to regain access to your account.",
};

/**
 * Reset password page
 * Provides password reset form for requesting a reset link
 */
export default function ResetPasswordPage() {
  return <ResetPasswordForm />;
}
