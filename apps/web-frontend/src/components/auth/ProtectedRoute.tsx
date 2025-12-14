"use client";

/**
 * Protected Route Component
 * 
 * Client-side route protection that ensures users are authenticated
 * before accessing protected routes. Works in conjunction with proxy.
 * 
 * This component:
 * - Checks authentication status using MSAL
 * - Redirects to login if not authenticated
 * - Shows loading state while checking authentication
 * - Handles redirect back to original route after login
 * 
 * @example
 * ```tsx
 * // In a protected page
 * export default function DashboardPage() {
 *   return (
 *     <ProtectedRoute>
 *       <DashboardContent />
 *     </ProtectedRoute>
 *   );
 * }
 * ```
 */

import { useEffect, useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /**
   * Optional redirect path after login
   * If not provided, uses current pathname
   */
  redirectTo?: string;
  /**
   * Show loading spinner while checking authentication
   */
  showLoading?: boolean;
}

export function ProtectedRoute({
  children,
  redirectTo,
  showLoading = true,
}: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading } = useAuth();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Wait for auth to finish loading
    if (isLoading) {
      return;
    }

    // Check authentication status
    if (!isAuthenticated) {
      // Build login URL with redirect parameter
      const loginUrl = new URL("/login", window.location.origin);
      const redirectPath = redirectTo || pathname;
      
      // Preserve query parameters if they exist
      if (searchParams.toString()) {
        loginUrl.searchParams.set("redirect", `${redirectPath}?${searchParams.toString()}`);
      } else {
        loginUrl.searchParams.set("redirect", redirectPath);
      }

      // Redirect to login
      router.push(loginUrl.toString());
      return;
    }

    // User is authenticated, allow access
    setIsChecking(false);
  }, [isAuthenticated, isLoading, router, pathname, searchParams, redirectTo]);

  // Show loading state while checking authentication
  if (isLoading || isChecking) {
    if (!showLoading) {
      return null;
    }

    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Checking authentication...
          </p>
        </div>
      </div>
    );
  }

  // User is authenticated, render children
  if (isAuthenticated) {
    return <>{children}</>;
  }

  // Fallback (shouldn't reach here, but just in case)
  return null;
}
