"use client";

/**
 * Login Form Component
 * 
 * Login form with Microsoft Entra ID integration.
 * Supports multiple authentication methods:
 * - Microsoft Account (via MSAL)
 * - Google Account (if enabled)
 * - Email OTP (if enabled)
 * 
 * @example
 * ```tsx
 * <LoginForm />
 * ```
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { getEnv } from "@/lib/config/browser/env";
import { initiateGoogleAuth } from "@/lib/api/auth";
import { FormInput } from "@/components/forms/FormInput";
import { FormButton } from "@/components/forms/FormButton";
import { FormError } from "@/components/forms/FormError";
import { Button } from "@/components/ui/button";
import { validateForm, getFieldErrors, type LoginFormData, loginSchema } from "@/lib/validation/schemas";
import { Mail, Lock, Loader2 } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const auth = useAuth() as any; // Extended auth context with email methods
  const { loginRedirect, isAuthenticated, isLoading: authLoading, error: authError, clearError, loginWithEmail } = auth;
  const env = getEnv();

  // Redirect parameter (where to go after login)
  const redirectTo = searchParams.get("redirect") || "/dashboard";

  // Form state
  const [formData, setFormData] = useState<LoginFormData>({
    email: "",
    password: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Clear errors when component mounts or auth error changes
  useEffect(() => {
    if (authError) {
      setFormError(authError.message || "Authentication failed. Please try again.");
    }
  }, [authError]);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      // Use replace to avoid redirect loops
      router.replace(redirectTo);
    }
  }, [isAuthenticated, authLoading, redirectTo, router]);

  // Handle Microsoft sign-in
  const handleMicrosoftLogin = async () => {
    try {
      clearError();
      setFormError(null);
      await loginRedirect();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to sign in with Microsoft";
      setFormError(errorMessage);
    }
  };

  // Handle Google sign-in (if enabled)
  const handleGoogleLogin = async () => {
    try {
      clearError();
      setFormError(null);
      setIsSubmitting(true);
      
      // Get redirect URI from environment
      const redirectUri = env.googleOAuth.redirectUri;
      
      // Initiate Google OAuth flow and get authorization URL
      const authUrl = await initiateGoogleAuth(redirectUri);
      
      // Redirect to Google OAuth page
      if (authUrl) {
        window.location.href = authUrl;
      } else {
        throw new Error("No authorization URL received from server");
      }
      
      // Note: User will be redirected to Google, then back to /auth/google/callback
      // The callback page will handle the rest
      // We don't reset isSubmitting here because we're redirecting away
    } catch (error) {
      setIsSubmitting(false);
      const errorMessage = error instanceof Error ? error.message : "Failed to sign in with Google";
      setFormError(errorMessage);
    }
  };

  // Handle email/password form submission
  const handleEmailPasswordSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    // Validate form
    const validation = validateForm(loginSchema, formData);
    if (!validation.success) {
      setFieldErrors(getFieldErrors(validation.errors));
      return;
    }

    setIsSubmitting(true);
    try {
      // Use email/password authentication
      if (loginWithEmail) {
        await loginWithEmail({
          email: formData.email,
          password: formData.password,
        });
        // Redirect will happen automatically via the useEffect that watches isAuthenticated
        router.replace(redirectTo);
      } else {
        setFormError("Email/password authentication is not available. Please use Microsoft sign-in.");
      }
    } catch (error: any) {
      // Handle API errors
      if (error.status === 401) {
        setFormError("Invalid email or password. Please try again.");
      } else if (error.errors) {
        // Field-specific errors from API
        setFieldErrors(error.errors);
      } else {
        const errorMessage = error.message || "Failed to sign in. Please try again.";
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

  // Show loading state if auth is initializing
  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="w-full rounded-lg border border-zinc-800 bg-zinc-900 p-6 sm:p-8">
      <h2 className="mb-6 text-2xl font-semibold text-white">
        Sign In
      </h2>

      {/* Form-level error */}
      <div className="mb-6">
        <FormError error={formError} onDismiss={() => setFormError(null)} dismissible />
      </div>

      {/* Microsoft Sign-In Button (Primary) */}
      <div className="mb-6 w-full min-w-0">
        <Button
          type="button"
          onClick={handleMicrosoftLogin}
          className="w-full bg-white text-zinc-900 hover:bg-zinc-100"
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
          Sign in with Microsoft
        </Button>
      </div>

      {/* Google Sign-In Button (if enabled) */}
      {env.features.enableGoogleSignIn && (
        <div className="mb-6 w-full min-w-0">
          <Button
            type="button"
            variant="outline"
            onClick={handleGoogleLogin}
            className="w-full bg-white text-zinc-900 border-zinc-300 hover:bg-zinc-100"
            size="lg"
            disabled={isSubmitting}
          >
            <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Sign in with Google
          </Button>
        </div>
      )}

      {/* Divider for email/password form */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-zinc-700" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-zinc-900 px-2 text-white/60">
            Or continue with email
          </span>
        </div>
      </div>

      {/* Email/Password Form */}
      <form onSubmit={handleEmailPasswordSubmit} className="space-y-4 w-full min-w-0">
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
              placeholder="Enter your password"
              leftElement={<Lock className="h-4 w-4" />}
            />

            <div className="flex items-center justify-between">
              <Link
                href="/reset-password"
                className="text-sm text-white/70 hover:text-white"
              >
                Forgot password?
              </Link>
            </div>

            <FormButton
              type="submit"
              isLoading={isSubmitting}
              loadingText="Signing in..."
              className="w-full bg-white text-zinc-900 hover:bg-zinc-100"
              size="lg"
            >
              Sign In
            </FormButton>
          </form>

      {/* Sign Up Link */}
      <div className="mt-6 text-center">
        <p className="text-sm text-white/70">
          Don't have an account?{" "}
          <Link
            href="/signup"
            className="font-medium text-white hover:underline"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
