/**
 * JWT Token Refresh Utility
 *
 * Ensures tokens are refreshed before expiry to prevent API failures.
 * Tokens are refreshed if they expire within 5 minutes (300 seconds).
 */

import { supabase } from './supabaseClient';

/**
 * Ensure fresh JWT token before API calls
 *
 * Automatically refreshes the token if it expires within 5 minutes.
 *
 * @returns Fresh JWT access token
 * @throws Error if not authenticated or refresh fails
 */
export async function ensureFreshToken(): Promise<string> {
  const { data: { session }, error } = await supabase.auth.getSession();

  if (error || !session) {
    throw new Error('Not authenticated');
  }

  // Check if token expires in less than 5 minutes (300 seconds)
  const expiresAt = session.expires_at || 0;
  const now = Math.floor(Date.now() / 1000);
  const timeUntilExpiry = expiresAt - now;

  if (timeUntilExpiry < 300) {
    console.log('🔄 Token expiring soon, refreshing...');
    const { data, error: refreshError } = await supabase.auth.refreshSession();

    if (refreshError || !data.session) {
      throw new Error('Failed to refresh token');
    }

    console.log('✅ Token refreshed successfully');
    return data.session.access_token;
  }

  return session.access_token;
}

/**
 * Get current session JWT (without auto-refresh)
 *
 * Use `ensureFreshToken()` instead if you need guaranteed fresh token.
 *
 * @returns Current JWT access token or null if not authenticated
 */
export async function getCurrentToken(): Promise<string | null> {
  const { data: { session }, error } = await supabase.auth.getSession();

  if (error || !session) {
    return null;
  }

  return session.access_token;
}

/**
 * Check if token is expired or expiring soon
 *
 * @param thresholdSeconds - Seconds before expiry to consider token stale (default: 300 = 5 minutes)
 * @returns true if token is expired or expiring soon
 */
export async function isTokenExpiring(thresholdSeconds: number = 300): Promise<boolean> {
  const { data: { session }, error } = await supabase.auth.getSession();

  if (error || !session) {
    return true; // No session = expired
  }

  const expiresAt = session.expires_at || 0;
  const now = Math.floor(Date.now() / 1000);
  const timeUntilExpiry = expiresAt - now;

  return timeUntilExpiry < thresholdSeconds;
}
