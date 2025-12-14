/**
 * MSAL Instance Factory
 * 
 * Creates and manages the MSAL PublicClientApplication instance.
 * This instance is used throughout the application for authentication.
 * 
 * @see @/lib/auth/msalConfig for configuration
 */

import {
  PublicClientApplication,
  type IPublicClientApplication,
} from "@azure/msal-browser";
import { getMsalConfig, validateMsalConfig } from "./msalConfig";

/**
 * MSAL Instance
 * 
 * Singleton instance of PublicClientApplication.
 * Only created once and reused throughout the application.
 */
let msalInstance: IPublicClientApplication | null = null;
let initializationPromise: Promise<void> | null = null;

/**
 * Get or create MSAL instance
 * 
 * Creates a new MSAL instance if one doesn't exist, or returns the existing one.
 * Validates configuration before creating the instance.
 * 
 * ⚠️ This function should only be called on the client side (browser).
 * During SSR/build, it will throw an error. Use in client components only.
 * 
 * ⚠️ IMPORTANT: This function is async and must be awaited.
 * The instance is returned only after initialization completes.
 * 
 * @returns Promise that resolves to MSAL PublicClientApplication instance
 * @throws Error if called during SSR or if configuration is invalid
 */
export async function getMsalInstance(): Promise<IPublicClientApplication> {
  // MSAL only works in the browser - throw error during SSR/build
  if (typeof window === "undefined") {
    throw new Error(
      "getMsalInstance() can only be called on the client side. " +
      "Make sure you're using it in a client component ('use client')."
    );
  }

  // Validate configuration first
  validateMsalConfig();

  // Return existing instance if available and initialized
  if (msalInstance && initializationPromise === null) {
    return msalInstance;
  }

  // If initialization is in progress, wait for it
  if (initializationPromise) {
    await initializationPromise;
    if (msalInstance) {
      return msalInstance;
    }
  }

  // Create new instance
  try {
    const config = getMsalConfig();
    msalInstance = new PublicClientApplication(config);

    // Initialize the application and await completion
    // This must complete before any other MSAL APIs are called
    initializationPromise = msalInstance
      .initialize()
      .then(() => {
        if (process.env.NODE_ENV === "development") {
          console.log("MSAL initialized successfully");
        }
        initializationPromise = null; // Mark as complete
      })
      .catch((error) => {
        console.error("MSAL initialization error:", error);
        initializationPromise = null; // Reset on error
        msalInstance = null; // Clear instance on error
        throw error;
      });

    // Wait for initialization to complete
    await initializationPromise;

    // Return the initialized instance
    if (!msalInstance) {
      throw new Error("MSAL instance was cleared during initialization");
    }

    return msalInstance;
  } catch (error) {
    console.error("Failed to create MSAL instance:", error);
    msalInstance = null;
    initializationPromise = null;
    throw error;
  }
}

/**
 * Reset MSAL instance
 * 
 * Clears the current instance. Useful for testing or re-initialization.
 * 
 * @internal
 */
export function resetMsalInstance(): void {
  msalInstance = null;
  initializationPromise = null;
}

/**
 * Check if MSAL is initialized
 * 
 * @returns true if MSAL instance exists and initialization is complete
 */
export function isMsalInitialized(): boolean {
  return msalInstance !== null && initializationPromise === null;
}
