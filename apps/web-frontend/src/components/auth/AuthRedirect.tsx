"use client";

/**
 * Auth Redirect Component
 * 
 * Redirects authenticated users away from auth pages (login/signup)
 * to the dashboard. Used in login and signup pages.
 * 
 * @example
 * ```tsx
 * // In login page
 * export default function LoginPage() {
 *   return (
 *     <AuthRedirect>
 *       <LoginForm />
 *     </AuthRedirect>
 *   );
 * }
 * ```
 */

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

interface AuthRedirectProps {
  children: React.ReactNode;
  /**
   * Where to redirect authenticated users
   * @default "/dashboard"
   */
  redirectTo?: string;
}

export function AuthRedirect({
  children,
  redirectTo = "/dashboard",
}: AuthRedirectProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    // Wait for auth to finish loading
    if (isLoading) {
      if (process.env.NODE_ENV === "development") {
        console.log("[AuthRedirect] Waiting for auth to load...");
      }
      return;
    }

    // If user is authenticated, redirect to dashboard
    // Use replace instead of push to avoid adding to history stack
    if (isAuthenticated) {
      // Check if there's a redirect parameter (from protected route)
      const redirect = searchParams.get("redirect");
      const finalRedirect = redirect || redirectTo;
      
      if (process.env.NODE_ENV === "development") {
        console.log("[AuthRedirect] User authenticated, redirecting to:", finalRedirect);
      }
      
      // Use replace to avoid redirect loops
      router.replace(finalRedirect);
    } else {
      if (process.env.NODE_ENV === "development") {
        console.log("[AuthRedirect] User not authenticated, showing form");
      }
    }
  }, [isAuthenticated, isLoading, router, searchParams, redirectTo]);

  // Show children if not authenticated or still loading
  if (isLoading || !isAuthenticated) {
    return <>{children}</>;
  }

  // User is authenticated, show loading while redirecting
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Redirecting...
        </p>
      </div>
    </div>
  );
}
