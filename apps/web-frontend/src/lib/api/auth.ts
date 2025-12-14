/**
 * Authentication API
 * 
 * API functions for email/password authentication.
 */

import { apiPost, setAuthToken, removeAuthToken } from "./client";
import type { UserProfile } from "@/types/auth";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: UserProfile;
  expiresIn?: number;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
}

export interface SignupResponse {
  token: string;
  user: UserProfile;
  expiresIn?: number;
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
    const response = await apiPost<LoginResponse>("/auth/login", credentials, {
      requireAuth: false,
    });

    // Store token
    if (response.token) {
      setAuthToken(response.token);
    }

    return response;
  } catch (error) {
    // Remove token on error
    removeAuthToken();
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
    const response = await apiPost<SignupResponse>("/auth/signup", data, {
      requireAuth: false,
    });

    // Store token
    if (response.token) {
      setAuthToken(response.token);
    }

    return response;
  } catch (error) {
    // Remove token on error
    removeAuthToken();
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
    "/auth/reset-password",
    { email },
    { requireAuth: false }
  );
}

/**
 * Verify email (if email verification is required)
 */
export async function verifyEmail(token: string): Promise<{ message: string }> {
  return apiPost<{ message: string }>("/auth/verify-email", { token }, { requireAuth: false });
}
