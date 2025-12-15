"use client";

/**
 * Authentication Provider
 * 
 * MSAL provider wrapper that manages authentication state and provides
 * authentication methods to all child components.
 * 
 * This component:
 * - Initializes MSAL and handles authentication state
 * - Provides login/logout functionality
 * - Manages user account and profile information
 * - Handles token acquisition and refresh
 * - Provides loading and error states
 * 
 * @see @azure/msal-react for MSAL React integration
 * @see @/contexts/AuthContext for context definition
 */

import { useEffect, useState, useCallback } from "react";
import type { IPublicClientApplication } from "@azure/msal-browser";
import {
  MsalProvider as MsalProviderBase,
  useMsal,
  useAccount,
  useIsAuthenticated,
} from "@azure/msal-react";
import type { AccountInfo, AuthenticationResult } from "@azure/msal-browser";
import { getMsalInstance } from "@/lib/auth/msalInstance";
import {
  loginRequest,
  silentRequest,
  logoutRequest,
  tokenRequest,
} from "@/lib/auth/msalConfig";
import { AuthContext } from "@/contexts/AuthContext";
import type { AuthContextValue, UserProfile } from "@/types/auth";
import { removeAllTokens, getAuthToken } from "@/lib/api/client";
import {
  loginWithEmailPassword,
  signupWithEmailPassword,
  type LoginRequest,
  type SignupRequest,
} from "@/lib/api/auth";

/**
 * Default/fallback auth context value
 * Used during initial render before MSAL is initialized
 */
const defaultAuthContextValue: AuthContextValue = {
  isAuthenticated: false,
  isLoading: true,
  account: null,
  user: null,
  error: null,
  login: async () => {
    throw new Error("AuthProvider is not initialized yet");
  },
  loginRedirect: async () => {
    throw new Error("AuthProvider is not initialized yet");
  },
  logout: async () => {
    throw new Error("AuthProvider is not initialized yet");
  },
  getAccessToken: async () => null,
  clearError: () => {},
  refreshAuth: async () => {},
};

/**
 * Internal component that uses MSAL hooks and provides auth context
 */
function AuthProviderInner({ children }: { children: React.ReactNode }) {
  const { instance, accounts, inProgress } = useMsal();
  const account = useAccount(accounts[0] || null);
  const isAuthenticated = useIsAuthenticated();

  const [user, setUser] = useState<UserProfile | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [emailAuthUser, setEmailAuthUser] = useState<UserProfile | null>(null);
  const [isProcessingRedirect, setIsProcessingRedirect] = useState(true);

  /**
   * Handle redirect promise - CRITICAL for redirect flow
   * This must be called when the component mounts to process redirect responses
   */
  useEffect(() => {
    let isMounted = true;
    
    // Check if we're coming from a redirect (has hash or code in URL)
    const hasRedirectParams = typeof window !== "undefined" && (
      window.location.hash.includes("code") ||
      window.location.hash.includes("id_token") ||
      window.location.search.includes("code")
    );
    
    if (hasRedirectParams && process.env.NODE_ENV === "development") {
      console.log("[AuthProvider] Detected redirect callback, processing...");
    }
    
    // Handle redirect promise on mount
    // This processes the authentication result after redirect from Microsoft
    instance
      .handleRedirectPromise()
      .then((response) => {
        if (!isMounted) return;
        
        setIsProcessingRedirect(false);
        
        if (response) {
          // Redirect was successful
          if (process.env.NODE_ENV === "development") {
            console.log("[AuthProvider] MSAL redirect handled successfully", {
              account: response.account?.username,
              hasAccessToken: !!response.accessToken,
              accountId: response.account?.homeAccountId,
            });
          }
          // Clear any errors on successful redirect
          setError(null);
        } else {
          // No redirect response - this is normal if user didn't come from a redirect
          setIsProcessingRedirect(false);
          if (process.env.NODE_ENV === "development") {
            console.log("[AuthProvider] MSAL handleRedirectPromise: No redirect response (normal)");
          }
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        
        setIsProcessingRedirect(false);
        
        // Redirect failed or was cancelled
        console.error("[AuthProvider] MSAL redirect error:", err);
        setError(err instanceof Error ? err : new Error("Authentication redirect failed"));
      });
    
    // If no redirect params, we're not processing a redirect
    if (!hasRedirectParams) {
      setIsProcessingRedirect(false);
    }
    
    return () => {
      isMounted = false;
    };
  }, [instance]);

  /**
   * Extract user profile from account information
   */
  const extractUserProfile = useCallback(
    (account: AccountInfo | null): UserProfile | null => {
      if (!account) return null;

      return {
        name: account.name || undefined,
        email: account.username || account.idTokenClaims?.email as string | undefined,
        id: account.homeAccountId || account.localAccountId,
        username: account.username || undefined,
      };
    },
    []
  );

  /**
   * Check for email/password authentication token on mount
   */
  useEffect(() => {
    // Check if we have an email auth token
    const token = getAuthToken();
    if (token && !account) {
      // Token exists but no MSAL account - user is authenticated via email/password
      // We'll need to fetch user info from the API
      // For now, we'll check the token and set a basic authenticated state
      // The actual user info should come from the API
    }
  }, [account]);

  /**
   * Update user profile from account (MSAL) or email auth
   */
  useEffect(() => {
    if (account) {
      // MSAL authentication
      setUser(extractUserProfile(account));
      setEmailAuthUser(null);
    } else if (emailAuthUser) {
      // Email/password authentication
      setUser(emailAuthUser);
    } else {
      setUser(null);
    }
  }, [account, emailAuthUser, extractUserProfile]);

  /**
   * Update loading state
   */
  useEffect(() => {
    // Loading is true when:
    // 1. MSAL is processing (redirect, login, etc.)
    // 2. We're still processing a redirect callback
    const isProcessing = inProgress !== "none";
    
    // Check for email auth token
    const hasEmailAuth = getAuthToken() !== null;
    
    // If we have email auth but no MSAL account, we're authenticated via email
    if (hasEmailAuth && !account && inProgress === "none" && !isProcessingRedirect) {
      setIsLoading(false);
      return;
    }
    
    // If MSAL is processing or we're handling a redirect, show loading
    if (isProcessing || isProcessingRedirect) {
      setIsLoading(true);
      return;
    }
    
    // MSAL is done processing and redirect is handled
    // If we have accounts, we're authenticated and ready
    if (accounts.length > 0) {
      // Small delay to ensure state is fully updated
      const timer = setTimeout(() => {
        setIsLoading(false);
      }, 100);
      return () => clearTimeout(timer);
    }
    
    // No accounts and not processing - not authenticated
    setIsLoading(false);
  }, [inProgress, accounts.length, account, isProcessingRedirect]);

  /**
   * Handle authentication errors
   */
  useEffect(() => {
    if (inProgress === "none" && !isAuthenticated && accounts.length === 0) {
      // Not an error - just not authenticated
      setError(null);
    }
  }, [inProgress, isAuthenticated, accounts.length]);

  /**
   * Login with popup
   */
  const login = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      await instance.loginPopup(loginRequest);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Login failed");
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [instance]);

  /**
   * Login with redirect
   */
  const loginRedirect = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      await instance.loginRedirect(loginRequest);
      // Note: After redirect, this component will re-render with new auth state
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Login redirect failed");
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [instance]);

  /**
   * Logout
   */
  const logout = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      
      // Get app URL for logout redirect
      const { getEnv } = await import("@/lib/config/browser/env");
      const env = getEnv();
      
      const logoutConfig = {
        ...logoutRequest,
        postLogoutRedirectUri: env.app.url,
        account: account || undefined,
      };
      
      await instance.logoutPopup(logoutConfig);
      setUser(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Logout failed");
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [instance, account]);

  /**
   * Get access token for API calls
   */
  const getAccessToken = useCallback(
    async (scopes: string[] = ["User.Read"]): Promise<string | null> => {
      if (!account) {
        return null;
      }

      try {
        setError(null);
        
        const request = tokenRequest(scopes);
        const response: AuthenticationResult | null =
          await instance.acquireTokenSilent({
            ...request,
            account: account,
          });

        return response?.accessToken || null;
      } catch (err) {
        // If silent token acquisition fails, try interactive
        try {
          const request = tokenRequest(scopes);
          const response: AuthenticationResult | null =
            await instance.acquireTokenPopup({
              ...request,
              account: account,
            });

          return response?.accessToken || null;
        } catch (interactiveErr) {
          const error =
            interactiveErr instanceof Error
              ? interactiveErr
              : new Error("Failed to acquire token");
          setError(error);
          return null;
        }
      }
    },
    [instance, account]
  );

  /**
   * Clear authentication error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Refresh authentication state
   */
  const refreshAuth = useCallback(async () => {
    if (!account) {
      return;
    }

    try {
      setError(null);
      setIsLoading(true);
      
      // Attempt to acquire token silently to refresh state
      await instance.acquireTokenSilent({
        ...silentRequest,
        account: account,
      });
    } catch (err) {
      // Silent refresh failed - user may need to re-authenticate
      const error =
        err instanceof Error ? err : new Error("Failed to refresh authentication");
      setError(error);
    } finally {
      setIsLoading(false);
    }
  }, [instance, account]);

  /**
   * Login with email and password
   */
  const loginWithEmail = useCallback(async (credentials: LoginRequest) => {
    try {
      setError(null);
      setIsLoading(true);
      const response = await loginWithEmailPassword(credentials);
      setEmailAuthUser(response.user);
      setUser(response.user);
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Login failed");
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Signup with email and password
   */
  const signupWithEmail = useCallback(async (data: SignupRequest) => {
    try {
      setError(null);
      setIsLoading(true);
      const response = await signupWithEmailPassword(data);
      setEmailAuthUser(response.user);
      setUser(response.user);
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Signup failed");
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Enhanced logout that handles both MSAL and email auth
   */
  const logoutEnhanced = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      
      // If we have MSAL account, logout from MSAL
      if (account) {
        // Get app URL for logout redirect
        const { getEnv } = await import("@/lib/config/browser/env");
        const env = getEnv();
        
        const logoutConfig = {
          ...logoutRequest,
          postLogoutRedirectUri: env.app.url,
          account: account || undefined,
        };
        await instance.logoutPopup(logoutConfig);
      }
      
      // Remove all auth tokens (access and refresh)
      removeAllTokens();
      
      // Clear user state
      setUser(null);
      setEmailAuthUser(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Logout failed");
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [instance, account]);

  /**
   * Enhanced isAuthenticated check
   * Check both MSAL isAuthenticated hook AND direct account presence
   * This ensures we catch authentication immediately after redirect
   */
  const isAuthenticatedEnhanced = 
    isAuthenticated || 
    accounts.length > 0 || 
    !!account || 
    getAuthToken() !== null;
  
  // Debug logging in development
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.log("[AuthProvider] Auth state:", {
        isAuthenticated,
        isAuthenticatedEnhanced,
        isLoading,
        hasAccount: !!account,
        accountsCount: accounts.length,
        inProgress,
        isProcessingRedirect,
        hasEmailToken: getAuthToken() !== null,
      });
    }
  }, [isAuthenticated, isAuthenticatedEnhanced, isLoading, account, accounts.length, inProgress, isProcessingRedirect]);

  /**
   * Context value
   */
  const contextValue: AuthContextValue & {
    loginWithEmail?: (credentials: LoginRequest) => Promise<any>;
    signupWithEmail?: (data: SignupRequest) => Promise<any>;
  } = {
    isAuthenticated: isAuthenticatedEnhanced,
    isLoading,
    account,
    user,
    error,
    login,
    loginRedirect,
    logout: logoutEnhanced,
    getAccessToken,
    clearError,
    refreshAuth,
    loginWithEmail,
    signupWithEmail,
  };

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
}

/**
 * Authentication Provider Component
 * 
 * Wraps the application with MSAL provider and authentication context.
 * This should be placed at the root of your application (in layout.tsx).
 * 
 * This component handles SSR gracefully by only initializing MSAL on the client side.
 * 
 * @example
 * ```tsx
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 * ```
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Only initialize MSAL on the client side
  // During SSR/build, we'll render children without MSAL provider
  const [msalInstance, setMsalInstance] = useState<IPublicClientApplication | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    // Mark that component is mounted (client-side only)
    setIsMounted(true);
    
    // Initialize MSAL instance on client side only
    // getMsalInstance() is async and must be awaited
    (async () => {
      try {
        const instance = await getMsalInstance();
        setMsalInstance(instance);
      } catch (error) {
        console.error("Failed to initialize MSAL:", error);
        // Continue without MSAL - auth will not work but app won't crash
      }
    })();
  }, []);

  // During SSR and initial client render (before hydration completes),
  // always render the same structure to prevent hydration mismatches
  // We'll provide default context initially, then switch to real context after mount
  if (!isMounted || !msalInstance) {
    return (
      <AuthContext.Provider value={defaultAuthContextValue}>
        {children}
      </AuthContext.Provider>
    );
  }

  // After hydration and MSAL initialization, wrap with MSAL provider
  // This only happens after the first render, so no hydration mismatch
  return (
    <MsalProviderBase instance={msalInstance}>
      <AuthProviderInner>{children}</AuthProviderInner>
    </MsalProviderBase>
  );
}
