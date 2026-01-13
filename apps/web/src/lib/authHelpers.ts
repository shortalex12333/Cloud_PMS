/**
 * Secure Authentication Helpers
 *
 * Central auth utilities for JWT management.
 * All backend calls MUST use these helpers to ensure proper authentication.
 *
 * Architecture (2026-01-13):
 * - Frontend sends ONLY Authorization: Bearer <master_jwt>
 * - Backend verifies JWT using MASTER_SUPABASE_JWT_SECRET
 * - Backend extracts user_id and looks up tenant in MASTER DB
 * - Backend routes to correct per-yacht DB using tenant credentials
 *
 * Security Requirements:
 * - Never store JWT in localStorage/sessionStorage (Supabase handles this)
 * - Never log JWT or raw tokens
 * - Auto-refresh expired tokens
 * - Fail fast if authentication is unavailable
 */

import { supabase } from './supabaseClient';

// Environment variable for yacht salt (DO NOT HARDCODE)
// Backend should validate signatures using the same salt
const YACHT_SALT = process.env.NEXT_PUBLIC_YACHT_SALT || '';

if (!YACHT_SALT && process.env.NODE_ENV === 'production') {
  console.error('[authHelpers] CRITICAL: YACHT_SALT not configured in production');
}

/**
 * Auth error for authentication failures
 */
export class AuthError extends Error {
  constructor(
    message: string,
    public code: 'NO_SESSION' | 'EXPIRED_TOKEN' | 'REFRESH_FAILED' | 'NO_YACHT_ID'
  ) {
    super(message);
    this.name = 'AuthError';
  }
}

/**
 * JWT metadata (without exposing raw token)
 */
export type JWTMetadata = {
  userId: string;
  email: string;
  expiresAt: number; // Unix timestamp
  isExpired: boolean;
};

/**
 * Get valid JWT with auto-refresh
 *
 * This function ensures we always have a valid, non-expired JWT.
 * - Checks current session
 * - Refreshes if expired
 * - Throws AuthError if user is not logged in
 *
 * @returns Valid JWT token
 * @throws AuthError if no session or refresh fails
 */
export async function getValidJWT(): Promise<string> {
  // Get current session
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError) {
    throw new AuthError('Failed to get session', 'NO_SESSION');
  }

  if (!session) {
    throw new AuthError('No active session', 'NO_SESSION');
  }

  // Check if token is expired or about to expire (within 60 seconds)
  const expiresAt = session.expires_at || 0;
  const now = Math.floor(Date.now() / 1000);
  const isExpiredOrExpiring = expiresAt - now < 60;

  if (isExpiredOrExpiring) {
    // Token is expired or expiring soon, refresh it
    const { data, error: refreshError } = await supabase.auth.refreshSession();

    if (refreshError || !data.session) {
      throw new AuthError('Failed to refresh session', 'REFRESH_FAILED');
    }

    return data.session.access_token;
  }

  return session.access_token;
}

/**
 * Get JWT metadata without exposing raw token
 *
 * Useful for debugging or UI display (e.g., showing token expiry time)
 *
 * @returns JWT metadata
 * @throws AuthError if no session
 */
export async function getJWTMetadata(): Promise<JWTMetadata> {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error || !session) {
    throw new AuthError('No active session', 'NO_SESSION');
  }

  const expiresAt = session.expires_at || 0;
  const now = Math.floor(Date.now() / 1000);

  return {
    userId: session.user.id,
    email: session.user.email || '',
    expiresAt,
    isExpired: expiresAt < now,
  };
}

/**
 * Generate yacht signature
 *
 * Computes SHA-256 hash of yacht_id + YACHT_SALT.
 * Backend must validate signatures using the same algorithm.
 * Returns null if yacht_id is missing (allows requests without yacht scope).
 *
 * @param yachtId - Yacht ID from user session
 * @returns Hex-encoded SHA-256 signature, or null if no yacht_id
 */
export async function getYachtSignature(yachtId: string | null): Promise<string | null> {
  if (!yachtId) {
    console.warn('[authHelpers] No yacht_id, skipping yacht signature');
    return null;
  }

  // Compute SHA-256 hash of yacht_id + salt
  const message = yachtId + YACHT_SALT;
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');

  return hashHex;
}

/**
 * Get authentication headers for backend requests
 *
 * This is the primary function that all API calls should use.
 * Returns ONLY the JWT - backend handles tenant routing.
 *
 * @param yachtId - DEPRECATED: ignored, backend looks up tenant from JWT
 * @returns Headers object with Authorization
 * @throws AuthError if JWT is unavailable
 */
export async function getAuthHeaders(yachtId?: string | null): Promise<HeadersInit> {
  const jwt = await getValidJWT();

  // Only send JWT - backend handles tenant routing via user_id lookup
  return {
    Authorization: `Bearer ${jwt}`,
  };
}

/**
 * Check if current session is valid
 *
 * Non-throwing version for UI guards (e.g., show login button)
 *
 * @returns true if user has valid session
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    await getValidJWT();
    return true;
  } catch {
    return false;
  }
}

/**
 * Get yacht ID from current session
 *
 * DEPRECATED: Frontend no longer queries yacht_id directly.
 * Use AuthContext.user.yachtId instead.
 * Backend handles tenant routing via JWT verification.
 *
 * @deprecated Use AuthContext instead
 * @returns yacht_id from user metadata or null
 */
export async function getYachtId(): Promise<string | null> {
  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.user) {
      return null;
    }

    // Only check user metadata - no database query
    // Backend handles tenant routing via JWT user_id lookup
    const meta = session.user.user_metadata || {};
    return meta.yacht_id || meta.yachtId || null;
  } catch (err) {
    console.warn('[authHelpers] Failed to get yacht_id:', err);
    return null;
  }
}

/**
 * Handle 401 Unauthorized errors
 *
 * Attempts to refresh token and retry the request.
 * If refresh fails, throws AuthError to force logout.
 *
 * @param retryFn - Function to retry after token refresh
 * @returns Result of retry function
 * @throws AuthError if refresh fails
 */
export async function handle401<T>(retryFn: () => Promise<T>): Promise<T> {
  try {
    // Try to refresh token
    const { error } = await supabase.auth.refreshSession();

    if (error) {
      throw new AuthError('Session expired, please login again', 'REFRESH_FAILED');
    }

    // Retry the original request with new token
    return await retryFn();
  } catch (error) {
    // If retry also fails, propagate error
    throw error;
  }
}
