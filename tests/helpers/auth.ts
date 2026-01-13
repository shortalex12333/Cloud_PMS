/**
 * Authentication Helpers for E2E Tests
 *
 * Provides login functionality against real Supabase Master DB
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as fs from 'fs';
import * as path from 'path';

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export interface UserBootstrap {
  userId: string;
  email: string;
  yachtId: string;
  tenantKeyAlias: string;
  role: string;
  status: string;
}

/**
 * Login to Supabase and get access token
 */
export async function login(
  email?: string,
  password?: string
): Promise<AuthTokens> {
  const supabaseUrl = process.env.MASTER_SUPABASE_URL;
  const supabaseKey = process.env.MASTER_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('MASTER_SUPABASE_URL and MASTER_SUPABASE_ANON_KEY must be set');
  }

  const userEmail = email || process.env.TEST_USER_EMAIL;
  const userPassword = password || process.env.TEST_USER_PASSWORD;

  if (!userEmail || !userPassword) {
    throw new Error('TEST_USER_EMAIL and TEST_USER_PASSWORD must be set');
  }

  const supabase = createClient(supabaseUrl, supabaseKey);

  const { data, error } = await supabase.auth.signInWithPassword({
    email: userEmail,
    password: userPassword,
  });

  if (error) {
    throw new Error(`Login failed: ${error.message}`);
  }

  if (!data.session) {
    throw new Error('Login succeeded but no session returned');
  }

  return {
    accessToken: data.session.access_token,
    refreshToken: data.session.refresh_token,
    expiresAt: data.session.expires_at || 0,
  };
}

/**
 * Get user bootstrap data from Master DB
 */
export async function getBootstrap(accessToken: string): Promise<UserBootstrap> {
  const supabaseUrl = process.env.MASTER_SUPABASE_URL;
  const supabaseKey = process.env.MASTER_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('MASTER_SUPABASE_URL and MASTER_SUPABASE_ANON_KEY must be set');
  }

  const response = await fetch(`${supabaseUrl}/rest/v1/rpc/get_my_bootstrap`, {
    method: 'POST',
    headers: {
      'apikey': supabaseKey,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Bootstrap RPC failed: ${response.status} - ${text}`);
  }

  const data = await response.json();

  return {
    userId: data.user_id,
    email: data.email,
    yachtId: data.yacht_id,
    tenantKeyAlias: data.tenant_key_alias,
    role: data.role,
    status: data.status,
  };
}

/**
 * Full login flow: authenticate + get bootstrap
 */
export async function fullLogin(): Promise<{
  tokens: AuthTokens;
  bootstrap: UserBootstrap;
}> {
  const tokens = await login();
  const bootstrap = await getBootstrap(tokens.accessToken);

  return { tokens, bootstrap };
}

/**
 * Get stored auth state (for reusing login across tests)
 */
export function getStoredAuthState(): AuthTokens | null {
  const statePath = path.join(process.cwd(), 'test-results', '.auth-state.json');

  if (fs.existsSync(statePath)) {
    const state = JSON.parse(fs.readFileSync(statePath, 'utf-8'));

    // Check if token is still valid (with 5 min buffer)
    if (state.expiresAt > Date.now() / 1000 + 300) {
      return state;
    }
  }

  return null;
}

/**
 * Store auth state for reuse
 */
export function storeAuthState(tokens: AuthTokens): void {
  const statePath = path.join(process.cwd(), 'test-results', '.auth-state.json');

  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(tokens, null, 2));
}

/**
 * Get access token (from cache or fresh login)
 */
export async function getAccessToken(): Promise<string> {
  const stored = getStoredAuthState();

  if (stored) {
    return stored.accessToken;
  }

  const tokens = await login();
  storeAuthState(tokens);

  return tokens.accessToken;
}
