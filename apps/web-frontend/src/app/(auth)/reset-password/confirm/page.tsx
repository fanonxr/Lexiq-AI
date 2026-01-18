"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { confirmPasswordReset } from "@/lib/api/auth";
import { FormInput } from "@/components/forms/FormInput";
import { FormButton } from "@/components/forms/FormButton";
import { FormError } from "@/components/forms/FormError";
import { Lock, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { logger } from "@/lib/logger";
import { validateForm, getFieldErrors, resetPasswordSchema } from "@/lib/validation/schemas";

/**
 * Confirm password reset page content
 * Allows user to set a new password using the reset token from the email
 */
function ConfirmPasswordResetPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [token, setToken] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    const tokenParam = searchParams.get("token");
    if (!tokenParam) {
      setFormError("Reset token is missing. Please check your email for the reset link.");
      return;
    }
    setToken(tokenParam);
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    if (!token) {
      setFormError("Reset token is missing. Please check your email for the reset link.");
      return;
    }

    // Validate form using schema
    const validation = validateForm(resetPasswordSchema, {
      password,
      confirmPassword,
      token,
    });
    
    if (!validation.success) {
      setFieldErrors(getFieldErrors(validation.errors));
      return;
    }

    setIsSubmitting(true);
    try {
      await confirmPasswordReset(token, password);
      setIsSuccess(true);
      // Redirect to login after 3 seconds
      setTimeout(() => {
        router.push("/login");
      }, 3000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to reset password";
      setFormError(errorMessage);
      logger.error("Password reset confirmation failed", error instanceof Error ? error : new Error(String(error)));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: "password" | "confirmPassword") => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.value;
    if (field === "password") {
      setPassword(value);
    } else {
      setConfirmPassword(value);
    }
    // Clear field errors when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  if (!token && !formError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          <div className="rounded-md bg-yellow-50 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-yellow-400" />
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-yellow-800">
                  Loading reset token...
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isSuccess) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-6 sm:p-8">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-900/20">
                <CheckCircle2 className="h-6 w-6 text-green-400" />
              </div>
              <h2 className="mb-2 text-2xl font-semibold text-white">
                Password Reset Successful
              </h2>
              <p className="mb-6 text-sm text-white/80">
                Your password has been reset successfully. You can now sign in with your new password.
              </p>
              <p className="mb-6 text-xs text-white/60">
                Redirecting to sign in page...
              </p>
              <Link
                href="/login"
                className="block w-full rounded-md bg-white px-4 py-2 text-center text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-100"
              >
                Go to Sign In
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-6 sm:p-8">
          <h2 className="mb-2 text-2xl font-semibold text-white">
            Set New Password
          </h2>
          <p className="mb-6 text-sm text-white/80">
            Enter your new password below. Make sure it's at least 8 characters long.
          </p>

          {/* Form-level error */}
          <div className="mb-6">
            <FormError error={formError} onDismiss={() => setFormError(null)} dismissible />
          </div>

          {/* Reset Password Form */}
          <form onSubmit={handleSubmit} className="space-y-4 w-full min-w-0">
            <FormInput
              name="password"
              type="password"
              label="New Password"
              value={password}
              onChange={handleChange("password")}
              error={fieldErrors.password}
              required
              placeholder="Enter your new password"
              leftElement={<Lock className="h-4 w-4" />}
              autoFocus
            />

            <FormInput
              name="confirmPassword"
              type="password"
              label="Confirm New Password"
              value={confirmPassword}
              onChange={handleChange("confirmPassword")}
              error={fieldErrors.confirmPassword}
              required
              placeholder="Confirm your new password"
              leftElement={<Lock className="h-4 w-4" />}
            />

            <FormButton
              type="submit"
              isLoading={isSubmitting}
              loadingText="Resetting password..."
              className="w-full bg-white text-zinc-900 hover:bg-zinc-100"
              size="lg"
            >
              Reset Password
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
        </div>
      </div>
    </div>
  );
}

/**
 * Confirm password reset page
 * Wrapped in Suspense for static export compatibility
 */
export default function ConfirmPasswordResetPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md">
          <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-6 sm:p-8">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <Loader2 className="h-12 w-12 animate-spin text-white" />
              <h2 className="text-xl font-semibold text-white">Loading...</h2>
            </div>
          </div>
        </div>
      </div>
    }>
      <ConfirmPasswordResetPageContent />
    </Suspense>
  );
}
