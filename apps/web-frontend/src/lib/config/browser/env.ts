/**
 * Client-side environment variable access (Browser)
 * 
 * ⚠️ IMPORTANT: This module is for CLIENT-SIDE variables only.
 * All variables here are prefixed with NEXT_PUBLIC_ and are exposed to the browser.
 * 
 * For server-side variables (secrets, API keys, etc.), use:
 * @see @/lib/config/server/env
 * 
 * Security Note: CLIENT_ID and TENANT_ID are safe to be public in OAuth/OIDC flows.
 * They are not secrets - only the CLIENT_SECRET would be secret (which we don't use
 * for browser-based MSAL authentication).
 * 
 * @example
 * ```typescript
 * // ✅ Use in Client Components, browser code
 * import { getEnv } from '@/lib/config/browser/env';
 * 
 * const env = getEnv();
 * const tenantId = env.entraId.tenantId;
 * const clientId = env.entraId.clientId;
 * ```
 */

/**
 * Type definitions for environment configuration
 */
export interface EntraIdConfig {
  /** Azure AD tenant ID (Directory ID) */
  tenantId: string;
  /** Azure AD application (client) ID */
  clientId: string;
  /** Azure AD authority URL (e.g., https://login.microsoftonline.com/common) */
  authority: string;
  /** Redirect URI for OAuth flow (must match Azure AD App Registration) */
  redirectUri: string;
}

export interface AppConfig {
  /** Application base URL */
  url: string;
  /** API Core service URL */
  apiUrl: string;
}

export interface GoogleOAuthConfig {
  /** Google OAuth client ID */
  clientId: string;
  /** Google OAuth redirect URI */
  redirectUri: string;
}

export interface FeatureFlags {
  /** Enable Google sign-in option */
  enableGoogleSignIn: boolean;
  /** Enable email one-time password (OTP) authentication */
  enableEmailOTP: boolean;
}

export interface EnvironmentConfig {
  /** Microsoft Entra ID configuration */
  entraId: EntraIdConfig;
  /** Google OAuth configuration */
  googleOAuth: GoogleOAuthConfig;
  /** Application URLs */
  app: AppConfig;
  /** Feature flags */
  features: FeatureFlags;
  /** Development environment flag */
  isDevelopment: boolean;
  /** Production environment flag */
  isProduction: boolean;
}

/**
 * Validates that a required environment variable is set
 * Only throws in runtime (browser), not during build time
 * 
 * @param key - Environment variable key
 * @param defaultValue - Optional default value
 * @returns The environment variable value or default
 * @throws Error if variable is missing and we're in browser runtime
 */
/**
 * Get environment variable value
 * 
 * ⚠️ IMPORTANT: Next.js inlines NEXT_PUBLIC_* variables at BUILD TIME.
 * This means:
 * 1. Variables must be available when you run `next dev` or `next build`
 * 2. You must restart the dev server after changing .env.local
 * 3. Dynamic lookups (like process.env[key]) work, but Next.js replaces
 *    static references (like process.env.NEXT_PUBLIC_APP_URL) at build time
 * 
 * @param key - Environment variable key (must start with NEXT_PUBLIC_)
 * @param defaultValue - Optional default value
 * @returns The environment variable value or default
 */
function getEnvVar(key: string, defaultValue?: string): string {
  // ⚠️ CRITICAL: Access process.env directly using the exact key name
  // Next.js will inline this at build time if the variable exists
  // Using process.env[key] works, but static access is preferred for inlining
  
  // Direct access - Next.js will inline these at build time
  let value: string | undefined;
  
  // Try direct property access first (Next.js inlines these)
  switch (key) {
    case 'NEXT_PUBLIC_ENTRA_ID_TENANT_ID':
      value = process.env.NEXT_PUBLIC_ENTRA_ID_TENANT_ID;
      break;
    case 'NEXT_PUBLIC_ENTRA_ID_CLIENT_ID':
      value = process.env.NEXT_PUBLIC_ENTRA_ID_CLIENT_ID;
      break;
    case 'NEXT_PUBLIC_ENTRA_ID_AUTHORITY':
      value = process.env.NEXT_PUBLIC_ENTRA_ID_AUTHORITY;
      break;
    case 'NEXT_PUBLIC_ENTRA_ID_REDIRECT_URI':
      value = process.env.NEXT_PUBLIC_ENTRA_ID_REDIRECT_URI;
      break;
    case 'NEXT_PUBLIC_APP_URL':
      value = process.env.NEXT_PUBLIC_APP_URL;
      break;
    case 'NEXT_PUBLIC_API_URL':
      value = process.env.NEXT_PUBLIC_API_URL;
      break;
    default:
      // Fallback to dynamic lookup for other variables
      value = process.env[key];
  }
  
  // During SSR/build, return value or default (no validation)
  if (typeof window === 'undefined') {
    return value || defaultValue || '';
  }
  
  // In browser runtime, check if value exists
  const finalValue = value || defaultValue || '';
  
  // Only validate if we're actually in the browser AND the value is missing
  if (!finalValue || finalValue.trim() === '') {
    // Only throw if it's a required variable (no default provided)
    if (defaultValue === undefined) {
      // Check if Next.js has loaded env vars yet
      // If process.env has no NEXT_PUBLIC_ vars at all, Next.js hasn't embedded them
      const allEnvKeys = Object.keys(process.env).filter(k => k.startsWith('NEXT_PUBLIC_'));
      
      if (allEnvKeys.length === 0) {
        // Next.js hasn't embedded the variables - this means dev server needs restart
        throw new Error(
          `Environment variables not loaded: ${key}\n\n` +
          `Next.js hasn't embedded any NEXT_PUBLIC_* variables.\n\n` +
          `According to Next.js docs, NEXT_PUBLIC_* variables are inlined at BUILD TIME.\n` +
          `This usually means:\n` +
          `1. The dev server was started before .env.local was created\n` +
          `2. The dev server wasn't restarted after editing .env.local\n` +
          `3. The .env.local file is in the wrong location\n\n` +
          `Solution:\n` +
          `1. Stop the dev server (Ctrl+C)\n` +
          `2. Verify .env.local exists in: apps/web-frontend/.env.local\n` +
          `3. Clear Next.js cache: rm -rf apps/web-frontend/.next\n` +
          `4. Restart: cd apps/web-frontend && npm run dev\n\n` +
          `See: https://nextjs.org/docs/pages/guides/environment-variables`
        );
      }
      
      // Variables are embedded but this one is missing
      throw new Error(
        `Missing required environment variable: ${key}\n\n` +
        `Troubleshooting:\n` +
        `1. Make sure .env.local exists in apps/web-frontend/ directory\n` +
        `2. Variable must start with NEXT_PUBLIC_ prefix\n` +
        `3. Restart the dev server after creating/editing .env.local\n` +
        `4. Check for typos in variable name\n` +
        `5. Clear Next.js cache: rm -rf .next\n\n` +
        `Found NEXT_PUBLIC_* variables: ${allEnvKeys.join(', ')}\n\n` +
        `See env.example for all required variables.`
      );
    }
  }
  
  return finalValue;
}

/**
 * Validates that a URL is properly formatted
 * 
 * @param url - URL string to validate
 * @param key - Environment variable key for error messages
 * @returns The validated URL
 * @throws Error if URL is invalid
 */
function validateUrl(url: string, key: string): string {
  if (typeof window !== 'undefined' && url) {
    try {
      new URL(url);
    } catch {
      throw new Error(
        `Invalid URL for environment variable ${key}: ${url}. ` +
        `Please provide a valid URL (e.g., http://localhost:3000 or https://example.com)`
      );
    }
  }
  return url;
}

/**
 * Validates that an Azure AD authority URL is properly formatted
 * 
 * @param authority - Authority URL to validate
 * @returns The validated authority URL
 */
function validateAuthority(authority: string): string {
  if (typeof window !== 'undefined' && authority) {
    const validPatterns = [
      /^https:\/\/login\.microsoftonline\.com\/(common|organizations|consumers|\w{8}-\w{4}-\w{4}-\w{4}-\w{12})$/,
      /^https:\/\/login\.microsoftonline\.com\/[^/]+\/v2\.0$/,
    ];
    
    const isValid = validPatterns.some(pattern => pattern.test(authority));
    
    if (!isValid) {
      console.warn(
        `Warning: Authority URL may be invalid: ${authority}. ` +
        `Expected format: https://login.microsoftonline.com/{tenant-id|common}`
      );
    }
  }
  return authority;
}

/**
 * Validates that a UUID/GUID is properly formatted (for tenant/client IDs)
 * 
 * @param id - ID string to validate
 * @param key - Environment variable key for error messages
 * @returns The validated ID
 */
function validateId(id: string, key: string): string {
  if (typeof window !== 'undefined' && id && id !== 'your-tenant-id' && id !== 'your-client-id') {
    const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidPattern.test(id)) {
      console.warn(
        `Warning: ${key} may be invalid. Expected UUID format: 00000000-0000-0000-0000-000000000000`
      );
    }
  }
  return id;
}

/**
 * Lazy-loaded environment configuration
 * 
 * This function creates the environment configuration object on first access.
 * This ensures environment variables are available when accessed.
 */
let envCache: EnvironmentConfig | null = null;

function createEnvConfig(): EnvironmentConfig {
  const appUrl = validateUrl(
    getEnvVar('NEXT_PUBLIC_APP_URL', 'http://localhost:3000'),
    'NEXT_PUBLIC_APP_URL'
  );
  
  return {
    // Microsoft Entra ID
    entraId: {
      tenantId: validateId(
        getEnvVar('NEXT_PUBLIC_ENTRA_ID_TENANT_ID'),
        'NEXT_PUBLIC_ENTRA_ID_TENANT_ID'
      ),
      clientId: validateId(
        getEnvVar('NEXT_PUBLIC_ENTRA_ID_CLIENT_ID'),
        'NEXT_PUBLIC_ENTRA_ID_CLIENT_ID'
      ),
      authority: validateAuthority(
        getEnvVar(
          'NEXT_PUBLIC_ENTRA_ID_AUTHORITY',
          'https://login.microsoftonline.com/common'
        )
      ),
      redirectUri: validateUrl(
        getEnvVar(
          'NEXT_PUBLIC_ENTRA_ID_REDIRECT_URI',
          'http://localhost:3000'
        ),
        'NEXT_PUBLIC_ENTRA_ID_REDIRECT_URI'
      ),
    },
    
    // Google OAuth
    googleOAuth: {
      clientId: getEnvVar('NEXT_PUBLIC_GOOGLE_CLIENT_ID', ''),
      redirectUri: validateUrl(
        getEnvVar(
          'NEXT_PUBLIC_GOOGLE_REDIRECT_URI',
          `${appUrl}/auth/google/callback`
        ),
        'NEXT_PUBLIC_GOOGLE_REDIRECT_URI'
      ),
    },
    
    // Application URLs
    app: {
      url: appUrl,
      apiUrl: validateUrl(
        getEnvVar('NEXT_PUBLIC_API_URL', 'http://localhost:8000'),
        'NEXT_PUBLIC_API_URL'
      ),
    },
    
    // Feature Flags
    features: {
      enableGoogleSignIn: process.env.NEXT_PUBLIC_ENABLE_GOOGLE_SIGNIN === 'true',
      enableEmailOTP: process.env.NEXT_PUBLIC_ENABLE_EMAIL_OTP === 'true',
    },
    
    // Environment
    isDevelopment: process.env.NODE_ENV === 'development',
    isProduction: process.env.NODE_ENV === 'production',
  } as const;
}

/**
 * Get environment configuration
 * 
 * Returns the environment configuration object. Creates it on first access
 * to ensure environment variables are loaded.
 * 
 * ⚠️ IMPORTANT: This function should only be called on the client side (browser).
 * During SSR/build, it returns a minimal config. Always use this in client components.
 * 
 * @returns Environment configuration object
 */
export function getEnv(): EnvironmentConfig {
  // During SSR/build, return a minimal config (no validation)
  if (typeof window === 'undefined') {
    return {
      entraId: {
        tenantId: '',
        clientId: '',
        authority: 'https://login.microsoftonline.com/common',
        redirectUri: process.env.NEXT_PUBLIC_ENTRA_ID_REDIRECT_URI || 'http://localhost:3000',
      },
      googleOAuth: {
        clientId: '',
        redirectUri: process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI || 'http://localhost:3000/auth/google/callback',
      },
      app: {
        url: 'http://localhost:3000',
        apiUrl: 'http://localhost:8000',
      },
      features: {
        enableGoogleSignIn: false,
        enableEmailOTP: false,
      },
      isDevelopment: false,
      isProduction: true,
    } as EnvironmentConfig;
  }

  // In browser, create config on first access (lazy loading)
  if (!envCache) {
    envCache = createEnvConfig();
  }
  return envCache;
}

/**
 * Validates that all required environment variables are set
 * Call this function early in your application to catch missing variables
 * 
 * @throws Error if any required environment variables are missing
 */
export function validateEnv(): void {
  if (typeof window === 'undefined') {
    // Skip validation during build/SSR
    return;
  }

  const env = getEnv();
  const required: Array<keyof EntraIdConfig> = ['tenantId', 'clientId'];
  const missing: string[] = [];

  for (const key of required) {
    if (!env.entraId[key] || env.entraId[key] === 'your-tenant-id' || env.entraId[key] === 'your-client-id') {
      missing.push(`NEXT_PUBLIC_ENTRA_ID_${key.toUpperCase().replace('ID', '_ID')}`);
    }
  }

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}. ` +
      `Please set them in your .env.local file. ` +
      `See env.example for all required variables.`
    );
  }
}

// Types are already exported above, no need to re-export
