"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { handleGoogleOAuthCallback } from "@/lib/api/calendar-integrations";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

function GoogleCallbackPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const [hasProcessed, setHasProcessed] = useState(false);

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

    if (!code || !state) {
      setStatus("error");
      setMessage("Missing authorization code or state parameter");
      setHasProcessed(true);
      return;
    }

    // Mark as processed immediately to prevent duplicate calls
    setHasProcessed(true);

    // Normalize redirect_uri (remove trailing slash to match backend normalization)
    const redirectUri = `${window.location.origin}/auth/google/callback`.replace(/\/$/, "");

    handleGoogleOAuthCallback(code, state, redirectUri)
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
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
      <div className="w-full max-w-md rounded-lg border border-zinc-200 bg-white p-8 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          {status === "loading" && (
            <>
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <h2 className="text-xl font-semibold">Connecting Google Calendar...</h2>
              <p className="text-sm text-muted-foreground">
                Please wait while we complete the connection.
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
                Redirecting to appointments page...
              </p>
            </>
          )}

          {status === "error" && (
            <>
              <XCircle className="h-12 w-12 text-red-500" />
              <h2 className="text-xl font-semibold text-red-600 dark:text-red-400">
                Connection Failed
              </h2>
              <p className="text-sm text-muted-foreground">{message}</p>
              <button
                onClick={() => router.push("/appointments")}
                className="mt-4 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Return to Appointments
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

