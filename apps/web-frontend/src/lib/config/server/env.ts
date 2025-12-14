/**
 * Server-side environment variable access
 * 
 * This module provides type-safe access to server-only environment variables.
 * These variables are NOT exposed to the browser and can contain secrets.
 * 
 * ⚠️ IMPORTANT: Only import this file in:
 * - Server Components
 * - API Routes (app/api/*)
 * - Server Actions
 * - Middleware (with caution)
 * 
 * ❌ DO NOT import in:
 * - Client Components ('use client')
 * - Browser-side code
 * 
 * @example
 * ```typescript
 * // In a Server Component or API Route
 * import { getServerEnv } from '@/lib/config/server/env';
 * 
 * const serverEnv = getServerEnv();
 * const apiKey = serverEnv.api.secretKey;
 * ```
 */

/**
 * Server-side environment configuration
 */
export interface ServerEnvironmentConfig {
  /** API and backend configuration */
  api: {
    /** Secret API key for backend communication (if needed) */
    secretKey?: string;
    /** Internal API URL (may differ from public URL) */
    internalUrl?: string;
  };
  /** Database configuration (if needed for server-side queries) */
  database?: {
    /** Database connection string (NEVER expose to client) */
    connectionString?: string;
  };
  /** Azure configuration for server-side operations */
  azure?: {
    /** Client secret (if using confidential client flow) - NOT for browser MSAL */
    clientSecret?: string;
  };
  /** Other server-only secrets */
  secrets?: {
    /** Encryption keys, JWT secrets, etc. */
    [key: string]: string | undefined;
  };
}

let serverEnvCache: ServerEnvironmentConfig | null = null;

/**
 * Get server-side environment configuration
 * 
 * Returns the server-side environment configuration. Creates it on first access.
 * 
 * ⚠️ SECURITY: Never import this in client-side code!
 * 
 * @returns Server environment configuration object
 */
export function getServerEnv(): ServerEnvironmentConfig {
  // Only allow on server side
  if (typeof window !== 'undefined') {
    throw new Error(
      'getServerEnv() should never be accessed in browser context. ' +
      'Use getEnv() from @/lib/config/browser/env instead for client-side variables.'
    );
  }

  if (!serverEnvCache) {
    serverEnvCache = {
      api: {
        secretKey: process.env.API_SECRET_KEY,
        internalUrl: process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL,
      },
      database: {
        connectionString: process.env.DATABASE_URL,
      },
      azure: {
        // Note: For browser-based MSAL, we don't use client secrets
        // This would only be needed for server-side token acquisition
        clientSecret: process.env.AZURE_CLIENT_SECRET,
      },
      secrets: {
        // Add other server-only secrets here
        // Example: encryptionKey: process.env.ENCRYPTION_KEY,
      },
    } as const;
  }

  return serverEnvCache;
}

/**
 * Validates that required server-side environment variables are set
 * 
 * @throws Error if required variables are missing
 */
export function validateServerEnv(): void {
  // Only validate in server context
  if (typeof window !== 'undefined') {
    throw new Error(
      'validateServerEnv() should never be accessed in browser context. ' +
      'Use validateEnv() from @/lib/config/browser/env instead for client-side variables.'
    );
  }

  const missing: string[] = [];

  // Add validation for required server-side variables here
  // Example:
  // const serverEnv = getServerEnv();
  // if (!serverEnv.api.secretKey) {
  //   missing.push('API_SECRET_KEY');
  // }

  if (missing.length > 0) {
    throw new Error(
      `Missing required server-side environment variables: ${missing.join(', ')}. ` +
      `Set them in your .env.local file (without NEXT_PUBLIC_ prefix).`
    );
  }
}
