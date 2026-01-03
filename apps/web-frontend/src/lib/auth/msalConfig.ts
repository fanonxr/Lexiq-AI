/**
 * Microsoft Authentication Library (MSAL) Configuration
 * 
 * This file configures MSAL for browser-based authentication with Microsoft Entra ID.
 * 
 * @see https://github.com/AzureAD/microsoft-authentication-library-for-js
 * @see @/lib/env for environment variable access
 */

import { Configuration, BrowserCacheLocation, LogLevel } from "@azure/msal-browser";
import { getEnv } from "@/lib/config/browser/env";
import { logger } from "@/lib/logger";

/**
 * MSAL Configuration
 * 
 * This configuration is used to initialize the PublicClientApplication.
 * All settings are derived from environment variables for type safety.
 * 
 * ⚠️ Note: This configuration is created lazily to avoid SSR issues.
 * It's only used on the client side via getMsalInstance().
 */
export function getMsalConfig(): Configuration {
  // This function is only called from getMsalInstance() which ensures
  // we're on the client side, so window is guaranteed to be defined
  const env = getEnv();
  return {
    auth: {
      clientId: env.entraId.clientId,
      authority: env.entraId.authority,
      // Redirect URI - must match what's configured in Azure AD App Registration
      redirectUri: env.entraId.redirectUri,
      // Post logout redirect URI (use app URL for logout)
      postLogoutRedirectUri: env.app.url,
      // Navigate to login request URL (redirectStartPage) after successful login
      navigateToLoginRequestUrl: true,
    },
    cache: {
      // Store tokens in sessionStorage (more secure than localStorage)
      cacheLocation: BrowserCacheLocation.SessionStorage,
      // Don't store auth state in cookies (better for security)
      storeAuthStateInCookie: false,
    },
    system: {
      // Logging level (only in development)
      loggerOptions: {
        loggerCallback: (level, message, containsPii) => {
          if (containsPii) {
            return; // Don't log PII
          }
          const envConfig = getEnv();
        if (envConfig.isDevelopment) {
            switch (level) {
              case LogLevel.Error:
                console.error(message);
                break;
              case LogLevel.Warning:
                console.warn(message);
                break;
              case LogLevel.Info:
                console.info(message);
                break;
              case LogLevel.Verbose:
                console.debug(message);
                break;
            }
          }
        },
        logLevel: (() => {
          const envConfig = getEnv();
          return envConfig.isDevelopment ? LogLevel.Verbose : LogLevel.Error;
        })(),
        piiLoggingEnabled: false, // Never log PII
      },
      // Window timeout for redirects (30 seconds)
      windowHashTimeout: 30000,
    },
  };
}

/**
 * Login Request Configuration
 * 
 * Defines the scopes and parameters for authentication requests.
 */
export const loginRequest = {
  scopes: [
    "openid", // Required for OpenID Connect
    "profile", // User's profile information
    "email", // User's email address
    "User.Read", // Read user's profile (Microsoft Graph)
  ],
  // Prompt for account selection if multiple accounts exist
  prompt: "select_account" as const,
  // Redirect to start page after login
  redirectStartPage: "/dashboard",
};

/**
 * Silent Request Configuration
 * 
 * Used for silent token acquisition (token refresh).
 */
export const silentRequest = {
  scopes: [
    "openid",
    "profile",
    "email",
    "User.Read",
  ],
  // Force refresh token acquisition
  forceRefresh: false,
};

/**
 * Logout Request Configuration
 * 
 * Defines parameters for logout requests.
 */
export const logoutRequest = {
  // Redirect to home page after logout
  // This will be set dynamically using getEnv().app.url
  postLogoutRedirectUri: "",
  // Clear account from cache
  account: undefined, // Will be set dynamically
};

/**
 * Token Request Configuration
 * 
 * Used for acquiring tokens for API calls.
 * 
 * For Microsoft Entra ID (Azure AD), there are two scenarios:
 * 
 * 1. **Same App Registration** (Frontend and Backend use same client ID):
 *    - Use the client ID directly: `{client-id}`
 *    - This is what we're using by default
 * 
 * 2. **Separate App Registrations** (Frontend and Backend use different client IDs):
 *    - Expose an API in the backend app registration
 *    - Use API scope format: `api://{backend-client-id}/.default`
 *    - Set NEXT_PUBLIC_API_CLIENT_ID to the backend's client ID
 * 
 * The backend validates that the token's audience (aud claim) matches:
 * - The backend's client_id (if using client ID directly)
 * - The API identifier (if using api:// format)
 */
export const tokenRequest = (scopes?: string[]) => {
  const env = getEnv();
  
  // Get API client ID (backend's client ID, or frontend's if same app)
  const apiClientId = process.env.NEXT_PUBLIC_API_CLIENT_ID || env.entraId.clientId;
  const frontendClientId = env.entraId.clientId;
  
  // Check if frontend and backend use the same app registration
  const sameAppRegistration = apiClientId === frontendClientId;
  
  // Check if we should use API scope format
  // If API is exposed in Azure Portal (which is required for AADSTS90009 fix),
  // we MUST use api:// format, not {client-id}/.default
  const useApiScope = process.env.NEXT_PUBLIC_USE_API_SCOPE === "true";
  
  // Check if custom scope is specified (e.g., access_as_user)
  const customScope = process.env.NEXT_PUBLIC_API_SCOPE_NAME; // e.g., "access_as_user"
  
  let defaultScope: string;
  
  // IMPORTANT: If you exposed an API in Azure Portal (set Application ID URI),
  // you MUST use api:// format, even for same app registration.
  // This is required to fix AADSTS90009 error.
  // 
  // When API is exposed, Azure AD expects: api://{client-id}/.default
  // NOT: {client-id}/.default
  if (useApiScope || (sameAppRegistration && process.env.NEXT_PUBLIC_FORCE_API_SCOPE === "true")) {
    // Use API scope format (required when API is exposed in Azure Portal)
    if (customScope) {
      // Use custom scope if specified (e.g., api://{client-id}/access_as_user)
      defaultScope = `api://${apiClientId}/${customScope}`;
    } else {
      // Use .default scope (e.g., api://{client-id}/.default)
      defaultScope = `api://${apiClientId}/.default`;
    }
  } else if (sameAppRegistration) {
    // Same app registration WITHOUT exposed API: Use client ID with /.default
    // Format: {client-id}/.default (e.g., "61e4d2bb-02df-4de1-8bd4-b26d5e2b53d9/.default")
    // NOTE: This will fail with AADSTS90009 if API is exposed in Azure Portal
    // If you get AADSTS90009, set NEXT_PUBLIC_FORCE_API_SCOPE=true
    defaultScope = `${apiClientId}/.default`;
  } else {
    // Different app registrations: Use API scope format
    if (customScope) {
      defaultScope = `api://${apiClientId}/${customScope}`;
    } else {
      defaultScope = `api://${apiClientId}/.default`;
    }
  }
  
  // Log token request configuration
  logger.debug("Token request configuration", {
    defaultScope,
    sameAppRegistration,
    apiClientId,
    frontendClientId,
    useApiScope,
    customScope,
    hasApiClientIdEnv: !!process.env.NEXT_PUBLIC_API_CLIENT_ID,
    forceApiScope: process.env.NEXT_PUBLIC_FORCE_API_SCOPE === "true",
  });
  
  return {
    scopes: scopes || [defaultScope],
    // Force refresh if needed
    forceRefresh: false,
  };
};

/**
 * Validate MSAL Configuration
 * 
 * Checks that all required configuration values are set.
 * 
 * @throws Error if configuration is invalid
 */
export function validateMsalConfig(): void {
  // Skip validation during build/SSR
  if (typeof window === "undefined") {
    return;
  }

  const env = getEnv();
  const clientId = env.entraId.clientId;
  const tenantId = env.entraId.tenantId;
  const authority = env.entraId.authority;

  if (!clientId || clientId === "your-client-id" || clientId.trim() === "") {
    throw new Error(
      "MSAL Configuration Error: NEXT_PUBLIC_ENTRA_ID_CLIENT_ID is not set. " +
      "Please set it in your .env.local file in the apps/web-frontend directory."
    );
  }

  if (!tenantId || tenantId === "your-tenant-id" || tenantId.trim() === "") {
    throw new Error(
      "MSAL Configuration Error: NEXT_PUBLIC_ENTRA_ID_TENANT_ID is not set. " +
      "Please set it in your .env.local file in the apps/web-frontend directory."
    );
  }

  if (!authority || authority.trim() === "") {
    throw new Error(
      "MSAL Configuration Error: Authority URL is invalid. " +
      "Please check your NEXT_PUBLIC_ENTRA_ID_TENANT_ID."
    );
  }

  // Validate authority URL format
  const authorityPattern =
    /^https:\/\/login\.microsoftonline\.com\/(common|organizations|consumers|\w{8}-\w{4}-\w{4}-\w{4}-\w{12})$/;
  if (!authorityPattern.test(authority)) {
    throw new Error(
      `MSAL Configuration Error: Invalid authority URL format: ${authority}. ` +
      "Expected format: https://login.microsoftonline.com/{tenant-id}"
    );
  }
}
