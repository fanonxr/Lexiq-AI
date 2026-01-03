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
import { removeAllTokens, getAuthToken, setTokenGetter } from "@/lib/api/client";
import {
  loginWithEmailPassword,
  signupWithEmailPassword,
  type LoginRequest,
  type SignupRequest,
} from "@/lib/api/auth";
import { fetchUserProfile } from "@/lib/api/users";
import { logger } from "@/lib/logger";

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
  const [isAcquiringToken, setIsAcquiringToken] = useState(false); // Prevent multiple simultaneous token requests

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
    
    if (hasRedirectParams) {
      logger.debug("Detected redirect callback, processing...");
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
          logger.debug("MSAL redirect handled successfully", {
            account: response.account?.username,
            hasAccessToken: !!response.accessToken,
            accountId: response.account?.homeAccountId,
          });
          // Clear any errors on successful redirect
          setError(null);
        } else {
          // No redirect response - this is normal if user didn't come from a redirect
          setIsProcessingRedirect(false);
          logger.debug("MSAL handleRedirectPromise: No redirect response (normal)");
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        
        setIsProcessingRedirect(false);
        
        // Redirect failed or was cancelled
        const error = err instanceof Error ? err : new Error("Authentication redirect failed");
        logger.error("MSAL redirect error", error);
        setError(error);
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
   * Get access token for API calls
   * Defined early so it can be used in other hooks
   * 
   * Note: For backend API calls, we don't pass scopes - tokenRequest()
   * will use the backend's client ID as the scope automatically.
   */
  const getAccessToken = useCallback(
    async (scopes?: string[]): Promise<string | null> => {
      if (!account) {
        return null;
      }

      // If token acquisition is already in progress, wait for it to complete
      // instead of returning null immediately (prevents race conditions)
      if (isAcquiringToken) {
        logger.debug("Token acquisition already in progress, waiting...");
        // Wait up to 5 seconds for the current acquisition to complete
        let waitCount = 0;
        const maxWait = 50; // 50 * 100ms = 5 seconds
        while (isAcquiringToken && waitCount < maxWait) {
          await new Promise(resolve => setTimeout(resolve, 100));
          waitCount++;
        }
        // If still acquiring after waiting, proceed with new request
        if (isAcquiringToken) {
          logger.warn("Token acquisition still in progress after waiting, proceeding anyway...");
        }
      }

      try {
        setIsAcquiringToken(true);
        setError(null);
        
        // Request token for backend API (no scopes = uses backend client ID)
        const request = tokenRequest(scopes);
        
        logger.debug("Requesting token", {
          scopes: request.scopes,
          accountId: account?.homeAccountId,
          forceRefresh: request.forceRefresh,
        });
        
        const response: AuthenticationResult | null =
          await instance.acquireTokenSilent({
            ...request,
            account: account,
          });

        if (response) {
          logger.debug("Token acquired successfully", {
            hasToken: !!response.accessToken,
            tokenLength: response.accessToken?.length || 0,
            scopes: response.scopes,
          });
        }

        setIsAcquiringToken(false);
        return response?.accessToken || null;
      } catch (err: any) {
        // Check if this is a consent error
        const isConsentError = err?.errorCode === "consent_required" || 
                              err?.errorCode === "interaction_required" ||
                              err?.message?.includes("consent") ||
                              err?.message?.includes("AADSTS65001");

        // Check if this is an iframe timeout error
        const isIframeTimeout = err?.errorCode === "monitor_window_timeout" ||
                                err?.message?.includes("monitor_window_timeout") ||
                                err?.message?.includes("iframe") ||
                                err?.message?.includes("Token acquisition in iframe failed");

        logger.warn("Silent token acquisition failed", {
          errorCode: err?.errorCode,
          errorMessage: err?.message,
          isConsentError,
          isIframeTimeout,
        });

        // If iframe timeout, try interactive popup immediately (don't wait for consent check)
        if (isIframeTimeout) {
          logger.debug("Iframe timeout detected, trying interactive popup...");
          try {
            const request = tokenRequest(scopes);
            const response: AuthenticationResult | null =
              await instance.acquireTokenPopup({
                ...request,
                account: account,
              });

            if (response?.accessToken) {
              setIsAcquiringToken(false);
              logger.debug("Interactive popup succeeded after iframe timeout");
              return response.accessToken;
            }
          } catch (popupErr: any) {
            logger.warn("Interactive popup failed after iframe timeout", {
              errorCode: popupErr?.errorCode,
              errorMessage: popupErr?.message,
            });
            // Continue to consent error handling below
          }
        }

        // If it's a consent error, we need admin consent in Azure Portal
        // However, for same app registration, we might need to expose an API first
        // Try interactive popup once to see if user consent helps, but don't loop
        if (isConsentError) {
          // Check if we've already tried interactive - if so, don't try again
          const hasTriedInteractive = sessionStorage.getItem("auth_consent_tried") === "true";
          
          if (!hasTriedInteractive) {
            // Mark that we've tried interactive
            sessionStorage.setItem("auth_consent_tried", "true");
            
            // Try interactive popup once
            try {
              logger.debug("Consent error detected, trying interactive popup once...");
              
              const request = tokenRequest(scopes);
              const response: AuthenticationResult | null =
                await instance.acquireTokenPopup({
                  ...request,
                  account: account,
                  prompt: "consent", // Force consent prompt
                });

              // If successful, clear the flag
              if (response?.accessToken) {
                sessionStorage.removeItem("auth_consent_tried");
                setIsAcquiringToken(false);
                return response.accessToken;
              }
            } catch (popupErr) {
              // Popup failed, continue to show error
              logger.warn("Interactive popup also failed", {
                error: popupErr instanceof Error ? popupErr.message : String(popupErr),
              });
            }
          }
          
          // Show error message
          setIsAcquiringToken(false);
          const error = new Error(
            "Consent is required. If you've already granted admin consent, you may need to:\n" +
            "1. Expose an API in Azure Portal (App registrations → Expose an API)\n" +
            "2. Set Application ID URI to: api://1fabcd74-ddc8-45ae-a7ed-fe017ae6b5ce\n" +
            "3. Grant admin consent again\n" +
            "4. Wait 1-2 minutes for changes to propagate\n" +
            "See /docs/connection/AZURE_AD_SETUP.md for detailed instructions."
          );
          setError(error);
          logger.error("Consent required - check Azure Portal configuration", error);
          return null;
        }

        // For other errors, try interactive popup (but only once)
        try {
          logger.debug("Attempting interactive token acquisition...");
          
          const request = tokenRequest(scopes);
          const response: AuthenticationResult | null =
            await instance.acquireTokenPopup({
              ...request,
              account: account,
            });

          setIsAcquiringToken(false);
          return response?.accessToken || null;
        } catch (interactiveErr: any) {
          setIsAcquiringToken(false);
          
          // Check if this is also a consent error
          const isInteractiveConsentError = interactiveErr?.errorCode === "consent_required" || 
                                            interactiveErr?.errorCode === "interaction_required" ||
                                            interactiveErr?.message?.includes("consent") ||
                                            interactiveErr?.message?.includes("AADSTS65001");

          if (isInteractiveConsentError) {
            const error = new Error(
              "Admin consent is required. Please ask your administrator to grant consent in Azure Portal. " +
              "See /docs/connection/GRANT_CONSENT_QUICK.md for instructions."
            );
            setError(error);
            logger.error("Consent required after interactive attempt", error);
            return null;
          }

          const error =
            interactiveErr instanceof Error
              ? interactiveErr
              : new Error("Failed to acquire token");
          setError(error);
          logger.error("Interactive token acquisition failed", error);
          return null;
        }
      }
    },
    [instance, account, isAcquiringToken]
  );

  /**
   * Set up token getter for API client
   * This allows the API client to get MSAL tokens
   */
  useEffect(() => {
    if (account && instance) {
      // Set token getter to use MSAL
      const tokenGetter = async () => {
        try {
          logger.debug("Token getter called, requesting token...", {
            accountId: account.homeAccountId,
            accountName: account.name,
            hasInstance: !!instance,
            isAcquiringToken,
          });
          
          // Ensure account is still valid
          if (!account) {
            logger.warn("No account available for token acquisition");
            return null;
          }
          
          // If token acquisition is already in progress, wait and retry
          if (isAcquiringToken) {
            logger.debug("Token acquisition in progress, waiting 500ms...");
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Try again after waiting
            if (isAcquiringToken) {
              logger.debug("Still acquiring token, using direct MSAL call");
              // Bypass getAccessToken and call MSAL directly to avoid deadlock
              try {
                const request = tokenRequest();
                const result = await instance.acquireTokenSilent({
                  ...request,
                  account: account,
                });
                if (result?.accessToken) {
                  logger.debug("Direct MSAL token acquisition successful");
                  return result.accessToken;
                }
              } catch (directError: any) {
                logger.error("Direct MSAL call failed", directError instanceof Error ? directError : new Error(String(directError)), {
                  errorCode: directError?.errorCode,
                  errorMessage: directError?.message,
                });
              }
              return null;
            }
          }
          
          // Call getAccessToken to get a fresh token
          const token = await getAccessToken();
          
          if (token) {
            logger.debug("Token retrieved for API client", {
              hasToken: !!token,
              tokenLength: token.length,
              accountId: account.homeAccountId,
            });
            return token;
          }
          
          // If getAccessToken returned null, try direct MSAL call as fallback
          logger.warn("getAccessToken returned null, trying direct MSAL call");
          try {
            const request = tokenRequest();
            const result = await instance.acquireTokenSilent({
              ...request,
              account: account,
            });
            if (result?.accessToken) {
              logger.debug("Fallback token acquisition successful");
              return result.accessToken;
            } else {
              logger.error("Fallback MSAL call returned no token");
            }
          } catch (fallbackError: any) {
            logger.error("Fallback token acquisition failed", fallbackError instanceof Error ? fallbackError : new Error(String(fallbackError)), {
              errorCode: fallbackError?.errorCode,
              errorMessage: fallbackError?.message,
            });
          }
          
          return null;
        } catch (error: any) {
          logger.error("Failed to get access token in token getter", error instanceof Error ? error : new Error(String(error)), {
            errorCode: error?.errorCode,
            errorMessage: error?.message,
          });
          return null;
        }
      };
      
      setTokenGetter(tokenGetter);
      logger.debug("Token getter set for account", { accountId: account.homeAccountId });
    } else {
      // Clear token getter if no account or instance
      setTokenGetter(null);
      logger.debug("Token getter cleared (no account or instance)");
    }

    // Cleanup on unmount
    return () => {
      setTokenGetter(null);
    };
  }, [account, instance, getAccessToken, isAcquiringToken]);

  /**
   * Check for email/password authentication token on mount
   */
  useEffect(() => {
    // Check if we have an email auth token (synchronous check)
    const token = getAuthToken();
    if (token && !account) {
      // Token exists but no MSAL account - user is authenticated via email/password
      // We'll need to fetch user info from the API
      // For now, we'll check the token and set a basic authenticated state
      // The actual user info should come from the API
    }
  }, [account]);

  /**
   * Fetch user profile from API when authenticated
   * This ensures we have complete user information including name
   */
  useEffect(() => {
    let isMounted = true;
    let timeoutId: NodeJS.Timeout | null = null;
    
    const loadUserProfile = async () => {
      // Wait until authentication is complete (not loading)
      if (isLoading || isProcessingRedirect) {
        return;
      }

      // Only fetch if we're authenticated (have account or email auth token)
      const hasAuth = account || emailAuthUser || getAuthToken() !== null;
      if (!hasAuth) {
        setUser(null);
        return;
      }

      try {
        // Try to fetch full user profile from API
        const profile = await fetchUserProfile();
        
        if (isMounted && profile) {
          // Use API profile which has complete information
          setUser({
            id: profile.id,
            name: profile.name,
            email: profile.email,
            username: profile.username,
          });
        }
      } catch (error) {
        // If API call fails, fall back to MSAL/email auth profile
        if (isMounted) {
          if (account) {
            // MSAL authentication - use extracted profile
            setUser(extractUserProfile(account));
            setEmailAuthUser(null);
          } else if (emailAuthUser) {
            // Email/password authentication
            setUser(emailAuthUser);
          } else {
            // Try to extract from token if available
            const token = getAuthToken();
            if (token) {
              // For email auth, we might not have full profile yet
              // Keep user as null and let it be set elsewhere
              setUser(null);
            } else {
              setUser(null);
            }
          }
        }
        
        // Only log error if we're actually authenticated (not just a network issue)
        if (account || emailAuthUser || getAuthToken()) {
          logger.warn("Failed to fetch user profile from API, using fallback", {
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    };

    // Small delay to ensure auth state is stable
    timeoutId = setTimeout(() => {
      loadUserProfile();
    }, 100);

    return () => {
      isMounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [account, emailAuthUser, extractUserProfile, isLoading, isProcessingRedirect]);

  /**
   * Update loading state
   */
  useEffect(() => {
    // Loading is true when:
    // 1. MSAL is processing (redirect, login, etc.)
    // 2. We're still processing a redirect callback
    const isProcessing = inProgress !== "none";
    
    // Check for email auth token (synchronous check)
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
    logger.debug("Auth state", {
      isAuthenticated,
      isAuthenticatedEnhanced,
      isLoading,
      hasAccount: !!account,
      accountsCount: accounts.length,
      inProgress,
      isProcessingRedirect,
      hasEmailToken: getAuthToken() !== null,
    });
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
        logger.error("Failed to initialize MSAL", error instanceof Error ? error : new Error(String(error)));
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
