/**
 * Authentication Types
 * 
 * Type definitions for authentication state, user data, and auth operations.
 */

import type { AccountInfo, AuthenticationResult } from "@azure/msal-browser";

/**
 * User profile information
 */
export interface UserProfile {
  /** User's display name */
  name?: string;
  /** User's email address */
  email?: string;
  /** User's unique identifier */
  id?: string;
  /** User's username */
  username?: string;
}

/**
 * Authentication state
 */
export interface AuthState {
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Whether authentication is being checked */
  isLoading: boolean;
  /** Current user account (MSAL AccountInfo) */
  account: AccountInfo | null;
  /** User profile information */
  user: UserProfile | null;
  /** Authentication error, if any */
  error: Error | null;
}

/**
 * Authentication context value
 */
export interface AuthContextValue extends AuthState {
  /** Login function (popup) */
  login: () => Promise<void>;
  /** Login function (redirect) */
  loginRedirect: () => Promise<void>;
  /** Logout function */
  logout: () => Promise<void>;
  /** Get access token for API calls */
  getAccessToken: (scopes?: string[]) => Promise<string | null>;
  /** Clear authentication error */
  clearError: () => void;
  /** Refresh authentication state */
  refreshAuth: () => Promise<void>;
}
