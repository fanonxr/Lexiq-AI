"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { handleGoogleOAuthCallback } from "@/lib/api/calendar-integrations";
import { handleGoogleCallback } from "@/lib/api/auth";
import { setAuthToken, setRefreshToken } from "@/lib/api/client";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";
import { getEnv } from "@/lib/config/browser/env";
import { logger } from "@/lib/logger";

function GoogleCallbackPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const [hasProcessed, setHasProcessed] = useState(false);
  const [authType, setAuthType] = useState<"user" | "calendar" | null>(null);

  useEffect(() => {
    // Prevent duplicate processing (React StrictMode in development causes double renders)
    if (hasProcessed) {
      return;
    }

    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (error) {
      setStatus("error");
      setMessage(
        errorDescription || `OAuth error: ${error}`
      );
      setHasProcessed(true);
      return;
    }

    if (!code) {
      setStatus("error");
      setMessage("Missing authorization code");
      setHasProcessed(true);
      return;
    }

    // Mark as processed immediately to prevent duplicate calls
    setHasProcessed(true);

    // Determine if this is user authentication or calendar integration
    // Calendar integration always requires state (user_id as UUID), user auth may or may not have state
    // Detection: If state is a UUID (36 chars with dashes), it's calendar integration
    // Otherwise, it's user authentication
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const isCalendarAuth = state && uuidPattern.test(state); // Calendar uses UUID as state
    const isUserAuth = !isCalendarAuth; // User auth if not calendar

    // Normalize redirect_uri (remove trailing slash to match backend normalization)
    // Use the same redirect URI that was used in the initiation (from environment or construct it)
    const env = getEnv();
    const redirectUri = env.googleOAuth.redirectUri || `${window.location.origin}/auth/google/callback`;
    const normalizedRedirectUri = redirectUri.replace(/\/$/, "");

    if (isUserAuth) {
      // User authentication flow
      setAuthType("user");
      logger.debug("Processing Google OAuth callback for user authentication", {
        codeLength: code.length,
        redirectUri: normalizedRedirectUri,
        hasState: !!state,
      });
      
      handleGoogleCallback(code, normalizedRedirectUri, state)
        .then((response) => {
          // Tokens are already stored by handleGoogleCallback
          logger.info("Google OAuth callback successful", {
            userId: response.user?.id,
            email: response.user?.email,
            hasToken: !!response.token,
          });
          
          // Verify tokens were actually stored
          const tokenStored = typeof window !== "undefined" && 
            sessionStorage.getItem("auth_token") !== null;
          
          if (!tokenStored && response.token) {
            // Token wasn't stored, try storing it again
            logger.warn("Token not found in storage, storing again");
            const { setAuthToken, setRefreshToken } = require("@/lib/api/client");
            setAuthToken(response.token);
            if (response.refresh_token) {
              setRefreshToken(response.refresh_token);
            }
          }
          
          setStatus("success");
          setMessage("Signed in with Google successfully!");
          
          // Use window.location.href for a full page reload to ensure AuthProvider detects tokens
          // Redirect immediately - authentication succeeded
          window.location.href = "/dashboard";
        })
        .catch((err) => {
          // Check if tokens were stored BEFORE showing error
          // This prevents the error page from flashing if authentication actually succeeded
          const tokenStored = typeof window !== "undefined" && 
            sessionStorage.getItem("auth_token") !== null;
          
          if (tokenStored) {
            // Tokens were stored, so authentication actually succeeded
            // The error might be from response parsing or something non-critical
            // Don't show error - go straight to success and redirect immediately
            logger.warn("Error occurred but tokens were stored - authentication succeeded", {
              error: err instanceof Error ? err.message : String(err),
            });
            setStatus("success");
            setMessage("Signed in with Google successfully!");
            // Redirect immediately - no delay needed since we know it succeeded
            window.location.href = "/dashboard";
          } else {
            // Real error - tokens weren't stored
            logger.error("Google OAuth callback failed", err instanceof Error ? err : new Error(String(err)), {
              codeLength: code.length,
              redirectUri: normalizedRedirectUri,
            });
            setStatus("error");
            setMessage(
              err instanceof Error
                ? err.message
                : "Failed to sign in with Google. Please try again."
            );
          }
        });
    } else if (isCalendarAuth) {
      // Calendar integration flow
      setAuthType("calendar");
      if (!state) {
        setStatus("error");
        setMessage("Missing state parameter for calendar integration");
        return;
      }
      handleGoogleOAuthCallback(code, state, normalizedRedirectUri)
        .then(() => {
          setStatus("success");
          setMessage("Google Calendar connected successfully!");
          // Redirect to appointments page after 2 seconds
          setTimeout(() => {
            router.push("/appointments");
          }, 2000);
        })
        .catch((err) => {
          setStatus("error");
          setMessage(
            err instanceof Error
              ? err.message
              : "Failed to connect Google Calendar. Please try again."
          );
        });
    } else {
      // Try user auth as default
      setAuthType("user");
      handleGoogleCallback(code, normalizedRedirectUri, state)
        .then((response) => {
          setStatus("success");
          setMessage("Signed in with Google successfully!");
          // Use window.location.href for full page reload
          setTimeout(() => {
            window.location.href = "/dashboard";
          }, 500);
        })
        .catch((err) => {
          // Check if tokens were stored despite the error
          const tokenStored = typeof window !== "undefined" && 
            sessionStorage.getItem("auth_token") !== null;
          
          if (tokenStored) {
            // Tokens were stored - authentication succeeded
            setStatus("success");
            setMessage("Signed in with Google successfully!");
            window.location.href = "/dashboard";
          } else {
            // Real error - tokens weren't stored
            setStatus("error");
            setMessage(
              err instanceof Error
                ? err.message
                : "Failed to authenticate. Please try again."
            );
          }
        });
    }
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
      <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-8 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          {status === "loading" && (
            <>
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <h2 className="text-xl font-semibold">
                {authType === "calendar" ? "Connecting Google Calendar..." : "Signing in with Google..."}
              </h2>
              <p className="text-sm text-muted-foreground">
                Please wait while we complete the {authType === "calendar" ? "connection" : "authentication"}.
              </p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle2 className="h-12 w-12 text-green-500" />
              <h2 className="text-xl font-semibold text-green-600 dark:text-green-400">
                Success!
              </h2>
              <p className="text-sm text-muted-foreground">{message}</p>
              <p className="text-xs text-muted-foreground">
                Redirecting {authType === "calendar" ? "to appointments page" : "to dashboard"}...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <XCircle className="h-12 w-12 text-red-500" />
              <h2 className="text-xl font-semibold text-red-600 dark:text-red-400">
                {authType === "calendar" ? "Connection Failed" : "Authentication Failed"}
              </h2>
              <p className="text-sm text-muted-foreground">{message}</p>
              <button
                onClick={() => router.push(authType === "calendar" ? "/appointments" : "/login")}
                className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                {authType === "calendar" ? "Return to Appointments" : "Return to Login"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-8 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex flex-col items-center justify-center space-y-4 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
            <h2 className="text-xl font-semibold">Loading...</h2>
          </div>
        </div>
      </div>
    }>
      <GoogleCallbackPageContent />
    </Suspense>
  );
}

