"use client";

/**
 * Authentication Context
 * 
 * React context for managing authentication state throughout the application.
 * This context provides authentication state and methods to all components.
 * 
 * @see @/components/providers/AuthProvider for the provider implementation
 */

import { createContext, useContext } from "react";
import type { AuthContextValue } from "@/types/auth";

/**
 * Authentication Context
 * 
 * Provides authentication state and methods to all child components.
 * Use the `useAuth` hook to access this context.
 */
export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

/**
 * Hook to access authentication context
 * 
 * @returns Authentication context value
 * @throws Error if used outside of AuthProvider
 * 
 * @example
 * ```typescript
 * const { isAuthenticated, login, logout } = useAuth();
 * ```
 */
export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }

  return context;
}
