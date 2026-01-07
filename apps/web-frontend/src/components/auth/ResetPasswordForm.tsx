"use client";

/**
 * Reset Password Form Component
 * 
 * Password reset form for requesting a password reset link.
 * With Microsoft Entra ID, password reset is typically handled by the identity provider.
 * 
 * @example
 * ```tsx
 * <ResetPasswordForm />
 * ```
 */

import { useState } from "react";
import Link from "next/link";
import { FormInput } from "@/components/forms/FormInput";
import { FormButton } from "@/components/forms/FormButton";
import { FormError } from "@/components/forms/FormError";
import { validateForm, getFieldErrors, type ResetPasswordRequestFormData, resetPasswordRequestSchema } from "@/lib/validation/schemas";
import { requestPasswordReset } from "@/lib/api/auth";
import { Mail, CheckCircle2 } from "lucide-react";

export function ResetPasswordForm() {
  // Form state
  const [email, setEmail] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    // Validate form
    const validation = validateForm(resetPasswordRequestSchema, { email });
    if (!validation.success) {
      setFieldErrors(getFieldErrors(validation.errors));
      return;
    }

    setIsSubmitting(true);
    try {
      await requestPasswordReset(email);
      setIsSuccess(true);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to send reset link";
      setFormError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value);
    // Clear field error when user starts typing
    if (fieldErrors.email) {
      setFieldErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors.email;
        return newErrors;
      });
    }
  };

  // If success, show success message
  if (isSuccess) {
    return (
      <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-6 sm:p-8">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-900/20">
            <CheckCircle2 className="h-6 w-6 text-green-400" />
          </div>
          <h2 className="mb-2 text-2xl font-semibold text-white">
            Check your email
          </h2>
          <p className="mb-6 text-sm text-white/80">
            We've sent a password reset link to <strong className="text-white">{email}</strong>. Please check your inbox and follow the instructions to reset your password.
          </p>
          <p className="mb-6 text-xs text-white/60">
            Didn't receive the email? Check your spam folder or try again.
          </p>
          <div className="space-y-3">
            <Link
              href="/login"
              className="block w-full rounded-md bg-white px-4 py-2 text-center text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-100"
            >
              Back to Sign In
            </Link>
            <button
              type="button"
              onClick={() => {
                setIsSuccess(false);
                setEmail("");
              }}
              className="block w-full rounded-md border border-zinc-700 bg-zinc-800 px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-zinc-700"
            >
              Try a different email
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-6 sm:p-8">
      <h2 className="mb-2 text-2xl font-semibold text-white">
        Reset Password
      </h2>
      <p className="mb-6 text-sm text-white/80">
        Enter your email address and we'll send you a link to reset your password.
      </p>

      {/* Form-level error */}
      <div className="mb-6">
        <FormError error={formError} onDismiss={() => setFormError(null)} dismissible />
      </div>

      {/* Reset Password Form */}
      <form onSubmit={handleSubmit} className="space-y-4 w-full min-w-0">
        <FormInput
          name="email"
          type="email"
          label="Email"
          value={email}
          onChange={handleChange}
          error={fieldErrors.email}
          required
          placeholder="you@example.com"
          leftElement={<Mail className="h-4 w-4" />}
          autoFocus
        />

        <FormButton
          type="submit"
          isLoading={isSubmitting}
          loadingText="Sending reset link..."
          className="w-full bg-white text-zinc-900 hover:bg-zinc-100"
          size="lg"
        >
          Send Reset Link
        </FormButton>
      </form>

      {/* Back to Login Link */}
      <div className="mt-6 text-center">
        <Link
          href="/login"
          className="text-sm font-medium text-white hover:underline"
        >
          ← Back to Sign In
        </Link>
      </div>

      {/* Microsoft Entra ID Note */}
      <div className="mt-6 rounded-md bg-blue-900/20 p-3">
        <p className="text-xs text-blue-200">
          <strong>Note:</strong> If you signed up with Microsoft or Google, please use the password reset option provided by your identity provider.
        </p>
      </div>
    </div>
  );
}
