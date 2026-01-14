"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { verifyCheckoutSession } from "@/lib/api/billing";
import { logger } from "@/lib/logger";

/**
 * Billing success page content
 * Shown after successful Stripe checkout
 */
function BillingSuccessPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error" | "verifying">("loading");
  const [message, setMessage] = useState<string>("");
  const [subscriptionCreated, setSubscriptionCreated] = useState<boolean>(false);
  const sessionId = searchParams.get("session_id");
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const maxAttempts = 20; // Poll for up to 20 attempts (20 seconds)
  const attemptCountRef = useRef(0);

  useEffect(() => {
    // Check if we have a session ID
    if (!sessionId) {
      setStatus("error");
      setMessage("Missing session ID. Please contact support if you completed a payment.");
      return;
    }

    // Start verifying the session
    const verifySession = async () => {
      try {
        setStatus("verifying");
        setMessage("Verifying your payment...");
        
        const result = await verifyCheckoutSession(sessionId);
        
        if (result.verified && result.subscription_created) {
          // Subscription is confirmed!
          setStatus("success");
          setMessage(result.message || "Your subscription has been activated successfully!");
          setSubscriptionCreated(true);
          
          // Redirect to dashboard after 3 seconds
          const redirectTimer = setTimeout(() => {
            router.push("/dashboard");
          }, 3000);
          
          return () => clearTimeout(redirectTimer);
        } else if (result.verified && !result.subscription_created) {
          // Payment successful but subscription not yet created (webhook delay)
          // Poll again in 1 second
          attemptCountRef.current += 1;
          
          if (attemptCountRef.current >= maxAttempts) {
            // Max attempts reached - show success but warn about delay
            setStatus("success");
            setMessage(
              "Payment successful! Your subscription is being activated. " +
              "This may take a few moments. You'll receive an email confirmation shortly."
            );
            setSubscriptionCreated(false);
            
            // Redirect after 5 seconds
            const redirectTimer = setTimeout(() => {
              router.push("/dashboard");
            }, 5000);
            
            return () => clearTimeout(redirectTimer);
          } else {
            // Continue polling
            setMessage(
              result.message || 
              `Payment successful, waiting for subscription activation... (${attemptCountRef.current}/${maxAttempts})`
            );
            
            pollIntervalRef.current = setTimeout(() => {
              verifySession();
            }, 1000);
          }
        } else {
          // Session not complete yet
          setMessage(result.message || "Processing your payment...");
          
          pollIntervalRef.current = setTimeout(() => {
            verifySession();
          }, 1000);
        }
      } catch (error) {
        logger.error("Error verifying checkout session", error instanceof Error ? error : new Error(String(error)));
        setStatus("error");
        setMessage(
          "We're having trouble verifying your payment. " +
          "If you completed the payment, your subscription should be activated shortly. " +
          "Please check your dashboard or contact support."
        );
      }
    };

    // Start verification
    verifySession();

    // Cleanup on unmount
    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
      }
    };
  }, [sessionId, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          {(status === "loading" || status === "verifying") && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <Loader2 className="h-12 w-12 animate-spin text-zinc-600 dark:text-zinc-400" />
              </div>
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                {status === "loading" ? "Processing your payment..." : "Verifying your payment..."}
              </h2>
              <p className="text-zinc-600 dark:text-zinc-400">
                {message || "Please wait while we confirm your subscription."}
              </p>
            </div>
          )}

          {status === "success" && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                Payment Successful!
              </h2>
              <p className="text-zinc-600 dark:text-zinc-400">{message}</p>
              <p className="text-sm text-zinc-500 dark:text-zinc-500">
                Redirecting to your dashboard...
              </p>
              <div className="pt-4">
                <Button
                  onClick={() => router.push("/dashboard")}
                  className="w-full"
                >
                  Go to Dashboard
                </Button>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="space-y-4">
              <div className="flex justify-center">
                <XCircle className="h-12 w-12 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                Something went wrong
              </h2>
              <p className="text-zinc-600 dark:text-zinc-400">{message}</p>
              <div className="pt-4 space-y-2">
                <Button
                  onClick={() => router.push("/dashboard")}
                  className="w-full"
                  variant="outline"
                >
                  Go to Dashboard
                </Button>
                <Button
                  onClick={() => router.push("/pricing")}
                  className="w-full"
                >
                  Try Again
                </Button>
              </div>
            </div>
          )}
        </div>

        {sessionId && (
          <div className="mt-8 text-center text-xs text-zinc-500 dark:text-zinc-500">
            Session ID: {sessionId}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Billing success page
 * Wrapped in Suspense for static export compatibility
 */
export default function BillingSuccessPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900 px-4 py-12 sm:px-6 lg:px-8">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <div className="space-y-4">
              <div className="flex justify-center">
                <Loader2 className="h-12 w-12 animate-spin text-zinc-600 dark:text-zinc-400" />
              </div>
              <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                Processing your payment...
              </h2>
              <p className="text-zinc-600 dark:text-zinc-400">
                Please wait while we confirm your subscription.
              </p>
            </div>
          </div>
        </div>
      </div>
    }>
      <BillingSuccessPageContent />
    </Suspense>
  );
}
