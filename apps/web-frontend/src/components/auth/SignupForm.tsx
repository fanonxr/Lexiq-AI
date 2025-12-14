"use client";

/**
 * Sign Up Form Component
 * 
 * Registration form with Microsoft Entra ID integration.
 * Supports multiple authentication methods:
 * - Microsoft Account (via MSAL)
 * - Google Account (if enabled)
 * - Email OTP (if enabled)
 * 
 * @example
 * ```tsx
 * <SignupForm />
 * ```
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { getEnv } from "@/lib/config/browser/env";
import { FormInput } from "@/components/forms/FormInput";
import { FormButton } from "@/components/forms/FormButton";
import { FormError } from "@/components/forms/FormError";
import { Button } from "@/components/ui/button";
import { validateForm, getFieldErrors, type SignupFormData, signupSchema } from "@/lib/validation/schemas";
import { Mail, Lock, User, Loader2 } from "lucide-react";

export function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const auth = useAuth() as any; // Extended auth context with email methods
  const { loginRedirect, isAuthenticated, isLoading: authLoading, error: authError, clearError, signupWithEmail } = auth;
  const env = getEnv();

  // Redirect parameter (where to go after signup)
  const redirectTo = searchParams.get("redirect") || "/dashboard";

  // Form state
  const [formData, setFormData] = useState<SignupFormData>({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);

  // Clear errors when component mounts or auth error changes
  useEffect(() => {
    if (authError) {
      setFormError(authError.message || "Registration failed. Please try again.");
    }
  }, [authError]);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      // Use replace to avoid redirect loops
      router.replace(redirectTo);
    }
  }, [isAuthenticated, authLoading, redirectTo, router]);

  // Handle Microsoft sign-up
  const handleMicrosoftSignup = async () => {
    try {
      clearError();
      setFormError(null);
      // With Microsoft Entra ID, sign-up and sign-in use the same flow
      // The user will be prompted to create an account if they don't have one
      await loginRedirect();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to sign up with Microsoft";
      setFormError(errorMessage);
    }
  };

  // Handle Google sign-up (if enabled)
  const handleGoogleSignup = async () => {
    // Note: Google sign-up would need additional configuration
    // For now, we'll show a message that it's not yet implemented
    setFormError("Google sign-up is not yet configured. Please use Microsoft sign-up.");
  };

  // Handle email/password form submission
  const handleEmailPasswordSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    // Validate terms acceptance
    if (!acceptedTerms || !acceptedPrivacy) {
      setFormError("Please accept the Terms of Service and Privacy Policy to continue.");
      return;
    }

    // Validate form
    const validation = validateForm(signupSchema, formData);
    if (!validation.success) {
      setFieldErrors(getFieldErrors(validation.errors));
      return;
    }

    setIsSubmitting(true);
    try {
      // Use email/password signup
      if (signupWithEmail) {
        await signupWithEmail({
          name: formData.name,
          email: formData.email,
          password: formData.password,
        });
        // Redirect will happen automatically via the useEffect that watches isAuthenticated
        router.replace(redirectTo);
      } else {
        setFormError("Email/password registration is not available. Please use Microsoft sign-up.");
      }
    } catch (error: any) {
      // Handle API errors
      if (error.status === 409) {
        setFormError("An account with this email already exists. Please sign in instead.");
      } else if (error.errors) {
        // Field-specific errors from API
        setFieldErrors(error.errors);
      } else {
        const errorMessage = error.message || "Failed to create account. Please try again.";
        setFormError(errorMessage);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear field error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // Handle checkbox changes
  const handleCheckboxChange = (type: "terms" | "privacy") => {
    if (type === "terms") {
      setAcceptedTerms(!acceptedTerms);
    } else {
      setAcceptedPrivacy(!acceptedPrivacy);
    }
    // Clear form error when user accepts terms
    if (formError && formError.includes("Terms of Service")) {
      setFormError(null);
    }
  };

  // Show loading state if auth is initializing
  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="mb-6 text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
        Create Account
      </h2>

      {/* Form-level error */}
      <div className="mb-6">
        <FormError error={formError} onDismiss={() => setFormError(null)} dismissible />
      </div>

      {/* Microsoft Sign-Up Button (Primary) */}
      <div className="mb-6">
        <Button
          type="button"
          onClick={handleMicrosoftSignup}
          className="w-full"
          size="lg"
          disabled={isSubmitting}
        >
          <svg
            className="mr-2 h-5 w-5"
            viewBox="0 0 23 23"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect x="0" y="0" width="11" height="11" fill="#F25022" />
            <rect x="12" y="0" width="11" height="11" fill="#7FBA00" />
            <rect x="0" y="12" width="11" height="11" fill="#00A4EF" />
            <rect x="12" y="12" width="11" height="11" fill="#FFB900" />
          </svg>
          Sign up with Microsoft
        </Button>
      </div>

      {/* Google Sign-Up Button (if enabled) */}
      {env.features.enableGoogleSignIn && (
        <div className="mb-6">
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleSignup}
            className="w-full"
            size="lg"
            disabled={isSubmitting}
          >
            <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Sign up with Google
          </Button>
        </div>
      )}

      {/* Divider for email/password form */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-zinc-300 dark:border-zinc-700" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-white px-2 text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
            Or sign up with email
          </span>
        </div>
      </div>

      {/* Registration Form */}
      <form onSubmit={handleEmailPasswordSubmit} className="space-y-4">
            <FormInput
              name="name"
              type="text"
              label="Full Name"
              value={formData.name}
              onChange={handleChange}
              error={fieldErrors.name}
              required
              placeholder="John Doe"
              leftElement={<User className="h-4 w-4" />}
            />

            <FormInput
              name="email"
              type="email"
              label="Email"
              value={formData.email}
              onChange={handleChange}
              error={fieldErrors.email}
              required
              placeholder="you@example.com"
              leftElement={<Mail className="h-4 w-4" />}
            />

            <FormInput
              name="password"
              type="password"
              label="Password"
              value={formData.password}
              onChange={handleChange}
              error={fieldErrors.password}
              required
              placeholder="Create a strong password"
              leftElement={<Lock className="h-4 w-4" />}
              helperText="Must be at least 8 characters with uppercase, lowercase, number, and special character"
            />

            <FormInput
              name="confirmPassword"
              type="password"
              label="Confirm Password"
              value={formData.confirmPassword}
              onChange={handleChange}
              error={fieldErrors.confirmPassword}
              required
              placeholder="Confirm your password"
              leftElement={<Lock className="h-4 w-4" />}
            />

            {/* Terms and Privacy Checkboxes */}
            <div className="space-y-3 pt-2">
              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={() => handleCheckboxChange("terms")}
                  className="mt-1 h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-800"
                />
                <span className="text-sm text-zinc-600 dark:text-zinc-400">
                  I agree to the{" "}
                  <Link
                    href="/terms"
                    className="font-medium text-zinc-900 hover:underline dark:text-zinc-100"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Terms of Service
                  </Link>
                </span>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={acceptedPrivacy}
                  onChange={() => handleCheckboxChange("privacy")}
                  className="mt-1 h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-800"
                />
                <span className="text-sm text-zinc-600 dark:text-zinc-400">
                  I agree to the{" "}
                  <Link
                    href="/privacy"
                    className="font-medium text-zinc-900 hover:underline dark:text-zinc-100"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Privacy Policy
                  </Link>
                </span>
              </label>
            </div>

            <FormButton
              type="submit"
              isLoading={isSubmitting}
              loadingText="Creating account..."
              className="w-full"
              size="lg"
              disabled={!acceptedTerms || !acceptedPrivacy}
            >
              Create Account
            </FormButton>
          </form>

      {/* Email Verification Notice */}
      <div className="mt-4 rounded-md bg-blue-50 p-3 dark:bg-blue-900/20">
          <p className="text-sm text-blue-800 dark:text-blue-200">
            <strong>Note:</strong> After creating your account, you'll receive an email verification link. Please check your inbox to verify your email address.
          </p>
        </div>

      {/* Sign In Link */}
      <div className="mt-6 text-center">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-zinc-900 hover:underline dark:text-zinc-100"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
