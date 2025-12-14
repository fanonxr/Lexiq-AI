"use client";

/**
 * useAuth Hook
 * 
 * Custom hook for accessing authentication state and methods.
 * This is the primary way to interact with authentication in your components.
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isAuthenticated, user, login, logout } = useAuth();
 * 
 *   if (!isAuthenticated) {
 *     return <button onClick={login}>Sign In</button>;
 *   }
 * 
 *   return (
 *     <div>
 *       <p>Welcome, {user?.name}!</p>
 *       <button onClick={logout}>Sign Out</button>
 *     </div>
 *   );
 * }
 * ```
 */

import { useAuthContext } from "@/contexts/AuthContext";
import type { AuthContextValue } from "@/types/auth";

/**
 * Hook to access authentication state and methods
 * 
 * @returns Authentication context value with state and methods
 * 
 * @example
 * ```typescript
 * const {
 *   isAuthenticated,  // boolean - whether user is authenticated
 *   isLoading,        // boolean - whether auth is being checked
 *   user,             // UserProfile | null - current user info
 *   account,           // AccountInfo | null - MSAL account
 *   error,             // Error | null - auth error if any
 *   login,             // () => Promise<void> - login with popup
 *   loginRedirect,     // () => Promise<void> - login with redirect
 *   logout,            // () => Promise<void> - logout
 *   getAccessToken,    // (scopes?) => Promise<string | null> - get token
 *   clearError,        // () => void - clear error
 *   refreshAuth,        // () => Promise<void> - refresh auth state
 * } = useAuth();
 * ```
 */
export function useAuth(): AuthContextValue {
  return useAuthContext();
}
