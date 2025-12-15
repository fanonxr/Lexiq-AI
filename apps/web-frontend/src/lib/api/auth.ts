/**
 * Authentication API
 * 
 * API functions for email/password authentication.
 */

import { apiPost, setAuthToken, setRefreshToken, removeAuthToken, removeRefreshToken, removeAllTokens } from "./client";
import type { UserProfile } from "@/types/auth";

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
  return apiPost<ResetPasswordResponse>(
    "/api/v1/auth/reset-password",
    { email },
    { requireAuth: false }
  );
}

/**
 * Verify email (if email verification is required)
 */
export async function verifyEmail(token: string): Promise<{ message: string }> {
  return apiPost<{ message: string }>("/api/v1/auth/verify-email", { token }, { requireAuth: false });
}
