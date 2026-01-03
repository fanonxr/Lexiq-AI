"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { handleOutlookOAuthCallback } from "@/lib/api/calendar-integrations";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

function OutlookCallbackPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (error) {
      setStatus("error");
      setMessage(
        errorDescription || `OAuth error: ${error}`
      );
      return;
    }

    if (!code || !state) {
      setStatus("error");
      setMessage("Missing authorization code or state parameter");
      return;
    }

    const redirectUri = `${window.location.origin}/auth/outlook/callback`;

    handleOutlookOAuthCallback(code, state, redirectUri)
      .then(() => {
        setStatus("success");
        setMessage("Outlook calendar connected successfully!");
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
            : "Failed to connect Outlook calendar. Please try again."
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
              <h2 className="text-xl font-semibold">Connecting Outlook calendar...</h2>
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

export default function OutlookCallbackPage() {
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
      <OutlookCallbackPageContent />
    </Suspense>
  );
}

