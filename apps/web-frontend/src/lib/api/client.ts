/**
 * API Client
 * 
 * Base HTTP client for making API requests to the backend.
 * Handles authentication headers, error handling, and request/response transformation.
 * 
 * Supports all three authentication types:
 * - Microsoft (Azure AD B2C/Entra ID) via MSAL
 * - Google OAuth
 * - Email/Password (internal JWT)
 * 
 * The client uses a unified token getter pattern that automatically handles
 * token retrieval for all authentication methods.
 */

import { getEnv } from "@/lib/config/browser/env";
import { logger } from "@/lib/logger";

export class ApiClientError extends Error {
  status?: number;
  code?: string;
  errors?: Record<string, string[]>;

  constructor(message: string, status?: number, code?: string, errors?: Record<string, string[]>) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

/**
 * Get the base API URL
 */
function getApiUrl(): string {
  const env = getEnv();
  return env.app.apiUrl;
}

/**
 * Token getter function type
 * This allows the AuthProvider to inject a token getter function
 */
type TokenGetter = () => Promise<string | null>;

/**
 * Global token getter function
 * Set by AuthProvider to provide tokens from all authentication methods
 * Supports: Microsoft (MSAL), Google OAuth, Email/Password
 */
let globalTokenGetter: TokenGetter | null = null;

/**
 * Set the global token getter function
 * Called by AuthProvider to inject unified token retrieval
 * The token getter handles all three auth types automatically
 */
export function setTokenGetter(getter: TokenGetter | null): void {
  globalTokenGetter = getter;
}

/**
 * Get authentication token synchronously (for checks)
 * This checks sessionStorage only - use getAuthTokenAsync for API calls
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return sessionStorage.getItem("auth_token");
}

/**
 * Get authentication token asynchronously (for API calls)
 * 
 * Priority:
 * 1. Try to get token via globalTokenGetter (if set by AuthProvider)
 *    - This handles all three auth types: Microsoft (MSAL), Google OAuth, Email/Password
 * 2. Fallback: Try to get token directly from MSAL instance (for Microsoft auth)
 * 3. Fallback: Get token from sessionStorage (for Google OAuth and Email/Password)
 * 
 * The globalTokenGetter uses the unified getAccessToken() function which automatically
 * detects and handles the appropriate authentication method.
 */
export async function getAuthTokenAsync(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  // Priority 1: Try unified token getter (handles all auth types)
  if (globalTokenGetter) {
    try {
      logger.debug("Calling globalTokenGetter (unified token getter)...");
      const token = await globalTokenGetter();
      if (token) {
        logger.debug("Token retrieved from globalTokenGetter", {
          hasToken: !!token,
          tokenLength: token.length,
        });
        return token;
      } else {
        logger.warn("globalTokenGetter returned null/undefined");
      }
    } catch (error) {
      logger.error("Failed to get token from unified token getter", error instanceof Error ? error : new Error(String(error)));
      // Fall through to fallback methods
    }
  } else {
    logger.debug("No globalTokenGetter set, trying fallback methods...");
    
    // Priority 2: Fallback - Try to get token directly from MSAL instance (Microsoft auth only)
    try {
      const { getMsalInstance } = await import("@/lib/auth/msalInstance");
      const { tokenRequest } = await import("@/lib/auth/msalConfig");
      const instance = await getMsalInstance();
      const accounts = instance.getAllAccounts();
      
      if (accounts.length > 0) {
        const account = accounts[0];
        logger.debug("Found MSAL account, attempting token acquisition...");
        
        try {
          const request = tokenRequest();
          const result = await instance.acquireTokenSilent({
            ...request,
            account: account,
          });
          
          if (result?.accessToken) {
            logger.debug("Token acquired directly from MSAL instance");
            return result.accessToken;
          }
        } catch (silentError: any) {
          logger.warn("Silent token acquisition failed, trying interactive", {
            errorCode: silentError?.errorCode,
            errorMessage: silentError?.message,
          });
          
          // Try interactive popup as last resort (but this will show a popup)
          try {
            const request = tokenRequest();
            const result = await instance.acquireTokenPopup({
              ...request,
              account: account,
            });
            
            if (result?.accessToken) {
              logger.debug("Token acquired via interactive popup");
              return result.accessToken;
            }
          } catch (popupError) {
            logger.error("Interactive token acquisition also failed", popupError instanceof Error ? popupError : new Error(String(popupError)));
          }
        }
      } else {
        logger.debug("No MSAL accounts found");
      }
    } catch (msalError) {
      logger.warn("Could not access MSAL instance", {
        error: msalError instanceof Error ? msalError.message : String(msalError),
      });
    }
  }

  // Priority 3: Fall back to sessionStorage (for Google OAuth and Email/Password)
  // Both Google and Email/Password use internal JWT tokens stored in sessionStorage
  const sessionToken = sessionStorage.getItem("auth_token");
  logger.debug("SessionStorage token (Google/Email/Password)", {
    hasToken: !!sessionToken,
    tokenLength: sessionToken?.length || 0,
  });
  return sessionToken;
}

/**
 * Set authentication token in storage
 */
export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem("auth_token", token);
  }
}

/**
 * Remove authentication token from storage
 */
export function removeAuthToken(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem("auth_token");
  }
}

/**
 * Get refresh token from storage
 */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return sessionStorage.getItem("refresh_token");
}

/**
 * Set refresh token in storage
 */
export function setRefreshToken(token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem("refresh_token", token);
  }
}

/**
 * Remove refresh token from storage
 */
export function removeRefreshToken(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem("refresh_token");
  }
}

/**
 * Remove all authentication tokens (access and refresh)
 */
export function removeAllTokens(): void {
  removeAuthToken();
  removeRefreshToken();
}

/**
 * API Request Options
 */
export interface ApiRequestOptions extends RequestInit {
  /**
   * Whether to include authentication token
   * @default true
   */
  requireAuth?: boolean;
  /**
   * Custom headers to add
   */
  headers?: HeadersInit;
}

/**
 * Make an API request
 * 
 * @param endpoint - API endpoint (e.g., "/auth/login")
 * @param options - Request options
 * @returns Response data
 * @throws ApiClientError if request fails
 */
export async function apiRequest<T = unknown>(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  logger.debug("apiRequest called", {
    endpoint,
    method: options.method || "GET",
    requireAuth: options.requireAuth !== false,
  });
  
  const { requireAuth = true, headers = {}, ...fetchOptions } = options;

  // Build URL
  const baseUrl = getApiUrl();
  const url = endpoint.startsWith("http") ? endpoint : `${baseUrl}${endpoint}`;

  // Build headers
  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };

  // Add authentication token if required
  if (requireAuth) {
    logger.debug("Getting token for authenticated request", {
      endpoint,
      hasGlobalTokenGetter: !!globalTokenGetter,
      method: fetchOptions.method || "GET",
    });
    
    let token: string | null = null;
    let tokenError: Error | null = null;
    
    try {
      // Retry token acquisition up to 3 times with exponential backoff
      let retries = 0;
      const maxRetries = 3;
      
      while (retries < maxRetries && !token) {
        try {
          token = await getAuthTokenAsync();
          if (token) {
            break;
          }
          
          // If token is null and we have a token getter, wait a bit and retry
          if (globalTokenGetter && retries < maxRetries - 1) {
            const delay = Math.min(1000 * Math.pow(2, retries), 2000); // Max 2 seconds
            logger.debug(`Token is null, retrying in ${delay}ms`, {
              attempt: retries + 1,
              maxRetries,
            });
            await new Promise(resolve => setTimeout(resolve, delay));
          }
        } catch (err) {
          tokenError = err instanceof Error ? err : new Error(String(err));
          if (retries < maxRetries - 1) {
            const delay = Math.min(1000 * Math.pow(2, retries), 2000);
            await new Promise(resolve => setTimeout(resolve, delay));
          }
        }
        retries++;
      }
    } catch (error) {
      tokenError = error instanceof Error ? error : new Error(String(error));
      logger.error("Error getting token", tokenError);
    }
    
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
      logger.debug("Token attached to request", {
        endpoint,
        hasToken: !!token,
        tokenLength: token.length,
      });
    } else {
      logger.error("No token available for authenticated request", undefined, {
        endpoint,
        hasGlobalTokenGetter: !!globalTokenGetter,
        sessionStorageToken: typeof window !== "undefined" ? !!sessionStorage.getItem("auth_token") : "N/A (SSR)",
        method: fetchOptions.method || "GET",
        tokenError: tokenError?.message,
      });
      
      // Try to get more info about why token is null
      if (globalTokenGetter) {
        try {
          logger.debug("Attempting to call token getter directly for debugging...");
          const directToken = await globalTokenGetter();
          logger.debug("Direct token getter result", {
            hasToken: !!directToken,
            tokenLength: directToken?.length || 0,
          });
        } catch (directError) {
          logger.error("Direct token getter error", directError instanceof Error ? directError : new Error(String(directError)));
        }
      }
      
      // Don't fail silently - this will cause 401 errors which is expected
      // The backend will return proper error messages
    }
  }

  logger.debug("Final headers before request", {
    hasAuth: !!requestHeaders["Authorization"],
    method: fetchOptions.method || "GET",
  });

  try {
    logger.debug("Making request", {
      method: fetchOptions.method || "GET",
      url,
      hasAuth: !!requestHeaders["Authorization"],
    });

    const response = await fetch(url, {
      ...fetchOptions,
      headers: requestHeaders,
    });

    logger.debug("Response received", {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
    });

    // Parse response (204 No Content has no body; parsing would throw)
    let data: any;
    if (response.status === 204) {
      data = undefined;
    } else {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        data = await response.text();
      }
    }

    // Handle error responses
    if (!response.ok) {
      const errorMessage =
        data?.message ||
        data?.error?.message ||
        data?.error ||
        `Request failed with status ${response.status}`;
      const errorCode = data?.code || data?.error?.code;
      const errors = data?.errors || data?.error?.details;

      // Log detailed error
      logger.error("Request failed", undefined, {
        url,
        status: response.status,
        statusText: response.statusText,
        error: errorMessage,
        code: errorCode,
      });

      throw new ApiClientError(errorMessage, response.status, errorCode, errors);
    }

    return data as T;
  } catch (error) {
    // Re-throw ApiClientError as-is
    if (error instanceof ApiClientError) {
      throw error;
    }

    // Handle network errors
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new ApiClientError(
        "Network error: Unable to connect to the server. Please check your connection.",
        0,
        "NETWORK_ERROR"
      );
    }

    // Handle other errors
    const message = error instanceof Error ? error.message : "An unexpected error occurred";
    throw new ApiClientError(message, 0, "UNKNOWN_ERROR");
  }
}

/**
 * GET request
 */
export function apiGet<T = unknown>(endpoint: string, options?: ApiRequestOptions): Promise<T> {
  return apiRequest<T>(endpoint, { ...options, method: "GET" });
}

/**
 * POST request
 */
export function apiPost<T = unknown>(
  endpoint: string,
  data?: unknown,
  options?: ApiRequestOptions
): Promise<T> {
  return apiRequest<T>(endpoint, {
    ...options,
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * PUT request
 */
export function apiPut<T = unknown>(
  endpoint: string,
  data?: unknown,
  options?: ApiRequestOptions
): Promise<T> {
  return apiRequest<T>(endpoint, {
    ...options,
    method: "PUT",
    body: data ? JSON.stringify(data) : undefined,
  });
}

/**
 * DELETE request
 */
export function apiDelete<T = unknown>(endpoint: string, options?: ApiRequestOptions): Promise<T> {
  return apiRequest<T>(endpoint, { ...options, method: "DELETE" });
}
