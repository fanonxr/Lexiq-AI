/**
 * API Client
 * 
 * Base HTTP client for making API requests to the backend.
 * Handles authentication headers, error handling, and request/response transformation.
 */

import { getEnv } from "@/lib/config/browser/env";

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
 * Set by AuthProvider to provide MSAL tokens
 */
let globalTokenGetter: TokenGetter | null = null;

/**
 * Set the global token getter function
 * Called by AuthProvider to inject MSAL token retrieval
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
 * 1. Try to get token from MSAL via globalTokenGetter (if set)
 * 2. Fall back to sessionStorage for backward compatibility
 */
export async function getAuthTokenAsync(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  // Try MSAL token getter first (if set by AuthProvider)
  if (globalTokenGetter) {
    try {
      if (process.env.NODE_ENV === "development") {
        console.log("[API Client] Calling globalTokenGetter...");
      }
      const token = await globalTokenGetter();
      if (token) {
        if (process.env.NODE_ENV === "development") {
          console.log("[API Client] Token retrieved from globalTokenGetter:", {
            hasToken: !!token,
            tokenLength: token.length,
          });
        }
        return token;
      } else {
        if (process.env.NODE_ENV === "development") {
          console.warn("[API Client] globalTokenGetter returned null/undefined");
        }
      }
    } catch (error) {
      console.error("[API Client] Failed to get token from MSAL:", error);
      // Fall through to sessionStorage
    }
  } else {
    if (process.env.NODE_ENV === "development") {
      console.warn("[API Client] No globalTokenGetter set, trying MSAL instance directly...");
    }
    
    // Fallback: Try to get token directly from MSAL instance if available
    try {
      const { getMsalInstance } = await import("@/lib/auth/msalInstance");
      const { tokenRequest } = await import("@/lib/auth/msalConfig");
      const instance = await getMsalInstance();
      const accounts = instance.getAllAccounts();
      
      if (accounts.length > 0) {
        const account = accounts[0];
        if (process.env.NODE_ENV === "development") {
          console.log("[API Client] Found account in MSAL instance, attempting token acquisition...");
        }
        
        try {
          const request = tokenRequest();
          const result = await instance.acquireTokenSilent({
            ...request,
            account: account,
          });
          
          if (result?.accessToken) {
            if (process.env.NODE_ENV === "development") {
              console.log("[API Client] Token acquired directly from MSAL instance");
            }
            return result.accessToken;
          }
        } catch (silentError: any) {
          if (process.env.NODE_ENV === "development") {
            console.warn("[API Client] Silent token acquisition failed, trying interactive:", {
              errorCode: silentError?.errorCode,
              errorMessage: silentError?.message,
            });
          }
          
          // Try interactive popup as last resort (but this will show a popup)
          try {
            const request = tokenRequest();
            const result = await instance.acquireTokenPopup({
              ...request,
              account: account,
            });
            
            if (result?.accessToken) {
              if (process.env.NODE_ENV === "development") {
                console.log("[API Client] Token acquired via interactive popup");
              }
              return result.accessToken;
            }
          } catch (popupError) {
            console.error("[API Client] Interactive token acquisition also failed:", popupError);
          }
        }
      } else {
        if (process.env.NODE_ENV === "development") {
          console.warn("[API Client] No accounts found in MSAL instance");
        }
      }
    } catch (msalError) {
      if (process.env.NODE_ENV === "development") {
        console.warn("[API Client] Could not access MSAL instance:", msalError);
      }
    }
  }

  // Fall back to sessionStorage (for backward compatibility)
  const sessionToken = sessionStorage.getItem("auth_token");
  if (process.env.NODE_ENV === "development") {
    console.log("[API Client] SessionStorage token:", {
      hasToken: !!sessionToken,
      tokenLength: sessionToken?.length || 0,
    });
  }
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
  console.log("[API Client] apiRequest called:", {
    endpoint,
    options: { ...options, body: options.body ? "[body present]" : undefined },
  });
  
  const { requireAuth = true, headers = {}, ...fetchOptions } = options;
  
  console.log("[API Client] requireAuth:", requireAuth);

  // Build URL
  const baseUrl = getApiUrl();
  const url = endpoint.startsWith("http") ? endpoint : `${baseUrl}${endpoint}`;
  
  console.log("[API Client] Request URL:", url);

  // Build headers
  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };
  
  console.log("[API Client] Initial headers:", Object.keys(requestHeaders));

  // Add authentication token if required
  console.log("[API Client] Checking requireAuth:", requireAuth);
  if (requireAuth) {
    console.log("[API Client] requireAuth is true, entering token retrieval block");
    if (process.env.NODE_ENV === "development") {
      console.log("[API Client] Getting token for authenticated request:", {
        endpoint,
        hasGlobalTokenGetter: !!globalTokenGetter,
        method: fetchOptions.method || "GET",
      });
    }
    
    let token: string | null = null;
    try {
      token = await getAuthTokenAsync();
    } catch (tokenError) {
      console.error("[API Client] Error getting token:", tokenError);
      token = null;
    }
    
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
      console.log("[API Client] Token attached to request:", {
        token,
        requestHeaders,
      });
      if (process.env.NODE_ENV === "development") {
        console.log("[API Client] ✅ Token attached to request:", {
          endpoint,
          hasToken: !!token,
          tokenLength: token.length,
          tokenPreview: token.substring(0, 20) + "...",
          headerSet: !!requestHeaders["Authorization"],
          headerValue: requestHeaders["Authorization"].substring(0, 30) + "...",
        });
      }
    } else {
      console.error("[API Client] ❌ No token available for authenticated request:", {
        endpoint,
        hasGlobalTokenGetter: !!globalTokenGetter,
        sessionStorageToken: typeof window !== "undefined" ? !!sessionStorage.getItem("auth_token") : "N/A (SSR)",
        method: fetchOptions.method || "GET",
      });
      
      // Try to get more info about why token is null
      if (globalTokenGetter) {
        try {
          console.log("[API Client] Attempting to call token getter directly for debugging...");
          const directToken = await globalTokenGetter();
          console.log("[API Client] Direct token getter result:", {
            hasToken: !!directToken,
            tokenLength: directToken?.length || 0,
          });
        } catch (directError) {
          console.error("[API Client] Direct token getter error:", directError);
        }
      }
      
      // Don't fail silently - this will cause 401 errors which is expected
      // The backend will return proper error messages
    }
  } else {
    console.log("[API Client] requireAuth is false, skipping token retrieval");
  }

  console.log("[API Client] Final headers before request:", {
    ...requestHeaders,
    Authorization: requestHeaders["Authorization"] ? `${requestHeaders["Authorization"].substring(0, 30)}...` : "none",
  });

  try {
    if (process.env.NODE_ENV === "development") {
      console.log("[API Client] Making request:", {
        method: fetchOptions.method || "GET",
        url,
        hasAuth: !!requestHeaders["Authorization"],
        authHeaderPreview: requestHeaders["Authorization"]
          ? `${requestHeaders["Authorization"].substring(0, 20)}...`
          : "none",
      });
    }

    const response = await fetch(url, {
      ...fetchOptions,
      headers: requestHeaders,
    });

    if (process.env.NODE_ENV === "development") {
      console.log("[API Client] Response received:", {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries()),
      });
    }

    // Parse response
    let data: any;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
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

      // Log detailed error in development
      if (process.env.NODE_ENV === "development") {
        console.error("[API Client] Request failed:", {
          url,
          status: response.status,
          statusText: response.statusText,
          error: errorMessage,
          code: errorCode,
          data: data,
        });
      }

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
