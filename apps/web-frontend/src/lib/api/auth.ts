/**
 * Authentication API
 * 
 * API functions for email/password authentication.
 */

import { apiPost, setAuthToken, setRefreshToken, removeAuthToken, removeRefreshToken, removeAllTokens } from "./client";
import type { UserProfile } from "@/types/auth";
import { logger } from "@/lib/logger";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  refresh_token?: string;
  user: UserProfile;
  expires_in?: number; // Backend uses snake_case
  expiresIn?: number; // Support both for compatibility
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
}

export interface SignupResponse {
  token: string;
  refresh_token?: string;
  user: UserProfile;
  expires_in?: number; // Backend uses snake_case
  expiresIn?: number; // Support both for compatibility
}

export interface ResetPasswordRequest {
  email: string;
}

export interface ResetPasswordResponse {
  message: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface VerifyEmailResponse {
  message: string;
}

export interface ResendVerificationRequest {
  email: string;
}

export interface ResendVerificationResponse {
  message: string;
}

export interface ConfirmPasswordResetRequest {
  token: string;
  new_password: string;
}

export interface ConfirmPasswordResetResponse {
  message: string;
}

/**
 * Login with email and password
 */
export async function loginWithEmailPassword(
  credentials: LoginRequest
): Promise<LoginResponse> {
  try {
    const response = await apiPost<LoginResponse>("/api/v1/auth/login", credentials, {
      requireAuth: false,
    });

    // Store tokens
    if (response.token) {
      setAuthToken(response.token);
    }
    if (response.refresh_token) {
      setRefreshToken(response.refresh_token);
    }

    // Normalize expires_in to expiresIn for compatibility
    if (response.expires_in && !response.expiresIn) {
      response.expiresIn = response.expires_in;
    }

    return response;
  } catch (error) {
    // Remove tokens on error
    removeAllTokens();
    throw error;
  }
}

/**
 * Sign up with email and password
 */
export async function signupWithEmailPassword(
  data: SignupRequest
): Promise<SignupResponse> {
  try {
    const response = await apiPost<SignupResponse>("/api/v1/auth/signup", data, {
      requireAuth: false,
    });

    // Store tokens
    if (response.token) {
      setAuthToken(response.token);
    }
    if (response.refresh_token) {
      setRefreshToken(response.refresh_token);
    }

    // Normalize expires_in to expiresIn for compatibility
    if (response.expires_in && !response.expiresIn) {
      response.expiresIn = response.expires_in;
    }

    return response;
  } catch (error) {
    // Remove tokens on error
    removeAllTokens();
    throw error;
  }
}

/**
 * Request password reset
 */
export async function requestPasswordReset(
  email: string
): Promise<ResetPasswordResponse> {
  try {
    const response = await apiPost<ResetPasswordResponse>(
      "/api/v1/auth/reset-password",
      { email },
      { requireAuth: false }
    );
    return response;
  } catch (error) {
    throw error;
  }
}

/**
 * Confirm password reset with token and new password
 */
export async function confirmPasswordReset(
  token: string,
  newPassword: string
): Promise<ConfirmPasswordResetResponse> {
  try {
    const response = await apiPost<ConfirmPasswordResetResponse>(
      "/api/v1/auth/reset-password/confirm",
      { token, new_password: newPassword },
      { requireAuth: false }
    );
    return response;
  } catch (error) {
    throw error;
  }
}

/**
 * Verify email address with token
 */
export async function verifyEmail(token: string): Promise<VerifyEmailResponse> {
  try {
    const response = await apiPost<VerifyEmailResponse>(
      "/api/v1/auth/verify-email",
      { token },
      { requireAuth: false }
    );
    return response;
  } catch (error) {
    removeAllTokens();
    throw error;
  }
}

/**
 * Resend verification email
 */
export async function resendVerificationEmail(
  email: string
): Promise<ResendVerificationResponse> {
  try {
    const response = await apiPost<ResendVerificationResponse>(
      "/api/v1/auth/resend-verification",
      { email },
      { requireAuth: false }
    );
    return response;
  } catch (error) {
    throw error;
  }
}

/**
 * Logout request/response types
 */
export interface LogoutResponse {
  message: string;
}

/**
 * Logout current user
 * 
 * Calls the backend logout endpoint for logging/auditing purposes.
 * The actual logout (token removal) is handled client-side.
 */
export async function logout(): Promise<LogoutResponse> {
  try {
    // Call backend logout endpoint (for logging/auditing)
    // This works for all auth types (Microsoft, Google, Email/Password)
    // since they all use tokens that can be validated
    return await apiPost<LogoutResponse>("/api/v1/auth/logout", {}, { requireAuth: true });
  } catch (error) {
    // Even if backend call fails, we should still remove tokens client-side
    // This ensures logout works even if backend is unavailable
    logger.warn("Backend logout call failed, but continuing with client-side logout", {
      error: error instanceof Error ? error.message : String(error),
    });
    return { message: "Logged out successfully" };
  }
}

/**
 * Google OAuth Authentication
 */

export interface InitiateGoogleAuthRequest {
  redirect_uri: string;
}

export interface InitiateGoogleAuthResponse {
  authUrl: string;
}

export interface GoogleCallbackRequest {
  code: string;
  state?: string;
  redirect_uri: string;
}

/**
 * Initiate Google OAuth flow
 * 
 * Gets the authorization URL from the backend and returns it.
 * The frontend should redirect to this URL.
 */
export async function initiateGoogleAuth(
  redirectUri: string,
  state?: string
): Promise<string> {
  try {
    const response = await apiPost<InitiateGoogleAuthResponse>(
      "/api/v1/auth/google/initiate",
      { redirect_uri: redirectUri },
      { requireAuth: false }
    );
    return response.authUrl;
  } catch (error) {
    removeAllTokens();
    throw error;
  }
}

/**
 * Handle Google OAuth callback
 * 
 * Exchanges the authorization code for tokens and stores them.
 */
export async function handleGoogleCallback(
  code: string,
  redirectUri: string,
  state?: string
): Promise<LoginResponse> {
  let tokensStored = false;
  
  try {
    const response = await apiPost<LoginResponse>(
      "/api/v1/auth/google/callback",
      {
        code,
        redirect_uri: redirectUri,
        state,
      },
      { requireAuth: false }
    );

    // Store tokens
    if (response.token) {
      setAuthToken(response.token);
      tokensStored = true;
    }
    if (response.refresh_token) {
      setRefreshToken(response.refresh_token);
    }

    // Normalize expires_in to expiresIn for compatibility
    if (response.expires_in && !response.expiresIn) {
      response.expiresIn = response.expires_in;
    }

    return response;
  } catch (error) {
    // Only remove tokens if they weren't successfully stored
    // If tokens were stored, the API call succeeded - don't remove them
    if (!tokensStored) {
      removeAllTokens();
    } else {
      logger.warn("Error occurred after tokens were stored - authentication may have succeeded", {
        error: error instanceof Error ? error.message : String(error),
      });
    }
    throw error;
  }
}
