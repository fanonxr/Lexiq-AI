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
 * Get authentication token from storage
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return sessionStorage.getItem("auth_token");
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
    const token = getAuthToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }
  }

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers: requestHeaders,
    });

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
        data?.error ||
        `Request failed with status ${response.status}`;
      const errorCode = data?.code;
      const errors = data?.errors;

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
