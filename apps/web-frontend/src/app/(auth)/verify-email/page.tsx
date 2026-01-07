"use client";

import type { Metadata } from "next";
import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { verifyEmail, resendVerificationEmail } from "@/lib/api/auth";
import { logger } from "@/lib/logger";

/**
 * Email verification page
 * Verifies user email address using token from query parameter
 */
export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"verifying" | "success" | "error" | "idle">("idle");
  const [message, setMessage] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [isResending, setIsResending] = useState(false);

  useEffect(() => {
    const token = searchParams.get("token");
    
    if (!token) {
      setStatus("error");
      setMessage("Verification token is missing. Please check your email for the verification link.");
      return;
    }

    // Verify email
    setStatus("verifying");
    verifyEmail(token)
      .then((response) => {
        setStatus("success");
        setMessage(response.message || "Email verified successfully!");
        // Redirect to dashboard after 3 seconds
        setTimeout(() => {
          router.push("/dashboard");
        }, 3000);
      })
      .catch((error) => {
        setStatus("error");
        const errorMessage = error instanceof Error ? error.message : "Failed to verify email";
        setMessage(errorMessage);
        logger.error("Email verification failed", error);
      });
  }, [searchParams, router]);

  const handleResend = async () => {
    if (!email) {
      setMessage("Please enter your email address to resend the verification email.");
      return;
    }

    setIsResending(true);
    try {
      const response = await resendVerificationEmail(email);
      setMessage(response.message || "Verification email sent! Please check your inbox.");
      setStatus("idle");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to resend verification email";
      setMessage(errorMessage);
      logger.error("Resend verification failed", error);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Verify Your Email
          </h2>
        </div>

        <div className="mt-8 space-y-6">
          {status === "verifying" && (
            <div className="rounded-md bg-blue-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-blue-400 animate-spin"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" opacity="0.25" />
                    <path d="M12 2a10 10 0 0 1 10 10" opacity="0.75" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-blue-800">
                    Verifying your email address...
                  </p>
                </div>
              </div>
            </div>
          )}

          {status === "success" && (
            <div className="rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-green-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-800">{message}</p>
                  <p className="mt-2 text-sm text-green-700">
                    Redirecting to dashboard...
                  </p>
                </div>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="space-y-4">
              <div className="rounded-md bg-red-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-red-400"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-red-800">{message}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-md bg-gray-50 p-4">
                <h3 className="text-sm font-medium text-gray-900 mb-2">
                  Resend Verification Email
                </h3>
                <div className="space-y-3">
                  <div>
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium text-gray-700"
                    >
                      Email address
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                      placeholder="Enter your email"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={isResending}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isResending ? "Sending..." : "Resend Verification Email"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {status === "idle" && message && (
            <div className="rounded-md bg-blue-50 p-4">
              <p className="text-sm font-medium text-blue-800">{message}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

