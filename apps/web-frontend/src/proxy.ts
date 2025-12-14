/**
 * Next.js Proxy for Route Protection
 * 
 * This proxy handles authentication-based route protection and redirects.
 * 
 * ⚠️ IMPORTANT: Proxy runs in the Node.js runtime (not Edge Runtime).
 * We use a hybrid approach:
 * 1. Proxy handles route matching and basic redirects
 * 2. Client-side components handle actual authentication checks
 * 
 * ⚠️ SECURITY NOTE: Proxy-based authentication checks have known vulnerabilities.
 * Always perform critical security checks at the data layer (API routes, server actions).
 * This proxy is primarily for user experience (redirects), not security.
 * 
 * Protected routes:
 * - /dashboard/* - Requires authentication
 * - /settings/* - Requires authentication
 * - /recordings/* - Requires authentication
 * 
 * Auth routes (redirect if authenticated):
 * - /login - Redirect to /dashboard if authenticated
 * - /signup - Redirect to /dashboard if authenticated
 * - /reset-password - Allow access (needed for password reset flow)
 * 
 * Public routes:
 * - / - Home page
 * - /pricing - Pricing page
 * - /debug-env - Debug page (development only)
 * 
 * @see https://nextjs.org/docs/app/guides/upgrading/version-16
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Check if a route requires authentication
 */
function isProtectedRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/recordings")
  );
}

/**
 * Check if a route is an auth route (login/signup)
 */
function isAuthRoute(pathname: string): boolean {
  return (
    pathname.startsWith("/login") ||
    pathname.startsWith("/signup")
  );
}

/**
 * Check if a route is public (no authentication required)
 */
function isPublicRoute(pathname: string): boolean {
  return (
    pathname === "/" ||
    pathname.startsWith("/pricing") ||
    pathname.startsWith("/debug-env")
  );
}

/**
 * ⚠️ DEPRECATED: This function is no longer used.
 * 
 * MSAL is configured to use sessionStorage (not cookies) for token storage.
 * This means we cannot check authentication server-side in the proxy.
 * 
 * All authentication checks are handled client-side via:
 * - ProtectedRoute component (for protected routes)
 * - AuthRedirect component (for auth routes)
 * 
 * For server-side authentication validation, use API routes or server actions
 * that can validate tokens from the Authorization header.
 */
function hasAuthCookie(request: NextRequest): boolean {
  // This function is kept for reference but not used
  // MSAL uses sessionStorage, so cookies won't be available server-side
  return false;
}

/**
 * Proxy function
 * 
 * Runs on every request to handle route protection and redirects.
 * 
 * ⚠️ IMPORTANT: MSAL uses sessionStorage (not cookies) for token storage.
 * This means we CANNOT check authentication server-side in the proxy.
 * All authentication checks must happen client-side via ProtectedRoute component.
 * 
 * ⚠️ Note: This runs in Node.js runtime (not Edge Runtime).
 * For security-critical checks, use API routes or server actions.
 * 
 * Since we can't check sessionStorage server-side, we allow all routes through
 * and rely on client-side protection (ProtectedRoute component) for security.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow static files and API routes to pass through
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/static") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // ⚠️ IMPORTANT: Since MSAL uses sessionStorage (not cookies),
  // we cannot check authentication server-side. All routes are allowed through,
  // and client-side components (ProtectedRoute) handle actual authentication checks.
  
  // Allow all routes through - client-side will handle protection
  // This prevents redirect loops when MSAL redirects back from Microsoft
  return NextResponse.next();
}

/**
 * Note: Proxy configuration is handled automatically by Next.js.
 * The proxy runs on all routes by default. Route filtering is done
 * within the proxy function itself for better control.
 * 
 * Proxy always runs in Node.js runtime (not Edge Runtime).
 */
