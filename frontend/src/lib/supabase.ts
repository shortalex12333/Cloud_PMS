/**
 * CelesteOS Supabase Integration
 *
 * Handles:
 * - Supabase client initialization
 * - JWT authentication
 * - Token refresh
 * - Session management
 *
 * IMPORTANT: Frontend NEVER calls Supabase directly for business logic.
 * All data operations go through Cloud API.
 * Supabase is used ONLY for authentication.
 */

import { createClient, SupabaseClient, Session, User as SupabaseUser } from '@supabase/supabase-js';
import { AuthTokens, User } from '../types';

// ============================================================================
// CONFIGURATION
// ============================================================================

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error('Missing Supabase environment variables');
}

// ============================================================================
// SUPABASE CLIENT
// ============================================================================

let supabaseClient: SupabaseClient | null = null;

/**
 * Get or create Supabase client (singleton)
 */
export function getSupabaseClient(): SupabaseClient {
  if (!supabaseClient) {
    supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    });
  }
  return supabaseClient;
}

// ============================================================================
// AUTHENTICATION
// ============================================================================

/**
 * Sign in with email and password
 */
export async function signIn(email: string, password: string): Promise<{
  session: Session;
  user: SupabaseUser;
}> {
  const supabase = getSupabaseClient();

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    throw new Error(`Authentication failed: ${error.message}`);
  }

  if (!data.session || !data.user) {
    throw new Error('Authentication failed: No session returned');
  }

  return {
    session: data.session,
    user: data.user,
  };
}

/**
 * Sign out current user
 */
export async function signOut(): Promise<void> {
  const supabase = getSupabaseClient();
  const { error } = await supabase.auth.signOut();

  if (error) {
    throw new Error(`Sign out failed: ${error.message}`);
  }
}

/**
 * Get current session
 */
export async function getSession(): Promise<Session | null> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    console.error('Failed to get session:', error);
    return null;
  }

  return data.session;
}

/**
 * Refresh session tokens
 */
export async function refreshSession(): Promise<Session | null> {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase.auth.refreshSession();

  if (error) {
    console.error('Failed to refresh session:', error);
    return null;
  }

  return data.session;
}

/**
 * Get current access token (JWT)
 */
export async function getAccessToken(): Promise<string | null> {
  const session = await getSession();
  return session?.access_token || null;
}

/**
 * Subscribe to auth state changes
 */
export function onAuthStateChange(
  callback: (event: string, session: Session | null) => void
) {
  const supabase = getSupabaseClient();

  const { data: { subscription } } = supabase.auth.onAuthStateChange(callback);

  return subscription;
}

// ============================================================================
// USER PROFILE (from Supabase Auth metadata)
// ============================================================================

/**
 * Get current user from Supabase Auth
 */
export async function getCurrentUser(): Promise<SupabaseUser | null> {
  const supabase = getSupabaseClient();
  const { data: { user }, error } = await supabase.auth.getUser();

  if (error) {
    console.error('Failed to get user:', error);
    return null;
  }

  return user;
}

// ============================================================================
// TOKEN UTILITIES
// ============================================================================

/**
 * Extract yacht_id from JWT token claims
 */
export function extractYachtIdFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.yacht_id || null;
  } catch (error) {
    console.error('Failed to parse JWT:', error);
    return null;
  }
}

/**
 * Extract user role from JWT token claims
 */
export function extractRoleFromToken(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.role || null;
  } catch (error) {
    console.error('Failed to parse JWT:', error);
    return null;
  }
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= exp;
  } catch (error) {
    console.error('Failed to parse JWT:', error);
    return true;
  }
}

/**
 * Convert Supabase session to AuthTokens format
 */
export function sessionToAuthTokens(session: Session): AuthTokens {
  return {
    access_token: session.access_token,
    refresh_token: session.refresh_token || '',
    expires_at: session.expires_at || 0,
  };
}

// ============================================================================
// RPC HELPERS (for direct Supabase queries if needed)
// ============================================================================

/**
 * Call Supabase RPC function
 *
 * IMPORTANT: Use sparingly. Most data should go through Cloud API.
 */
export async function callSupabaseRPC<T>(
  functionName: string,
  params: Record<string, any> = {}
): Promise<T> {
  const supabase = getSupabaseClient();

  const { data, error } = await supabase.rpc(functionName, params);

  if (error) {
    throw new Error(`RPC call failed: ${error.message}`);
  }

  return data as T;
}

// ============================================================================
// YACHT CONTEXT (from users table)
// ============================================================================

/**
 * Fetch user details from Cloud API (not Supabase directly)
 * This function is a placeholder - actual implementation should call Cloud API
 */
export async function fetchUserContext(userId: string): Promise<User | null> {
  // This should call Cloud API /v1/users/me
  // NOT implemented here - handled in api.ts
  console.warn('fetchUserContext should be called through Cloud API');
  return null;
}

// ============================================================================
// EXPORTS
// ============================================================================

export const supabase = {
  getClient: getSupabaseClient,
  auth: {
    signIn,
    signOut,
    getSession,
    refreshSession,
    getAccessToken,
    onAuthStateChange,
    getCurrentUser,
  },
  tokens: {
    extractYachtId: extractYachtIdFromToken,
    extractRole: extractRoleFromToken,
    isExpired: isTokenExpired,
    sessionToAuthTokens,
  },
  rpc: callSupabaseRPC,
};
