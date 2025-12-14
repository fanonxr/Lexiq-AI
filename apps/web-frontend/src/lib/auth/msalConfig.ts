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
 * Can be customized per API endpoint.
 */
export const tokenRequest = (scopes: string[] = ["User.Read"]) => ({
  scopes,
  // Force refresh if needed
  forceRefresh: false,
});

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
