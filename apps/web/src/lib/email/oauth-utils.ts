/**
 * Email Transport Layer - OAuth Utilities
 *
 * Shared utilities for Microsoft Graph OAuth flows.
 * Enforces read/write app separation per doctrine.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { createHash } from 'crypto';

// ============================================================================
// AZURE APP CONFIGURATION
// ============================================================================

// READ APP - Mail.Read, User.Read, MailboxSettings.Read, offline_access
export const READ_APP = {
  appId: process.env.AZURE_READ_APP_ID || process.env.AZURE_APP_ID || '41f6dc82-8127-4330-97e0-c6b26e6aa967',
  clientSecret: process.env.AZURE_READ_CLIENT_SECRET || process.env.AZURE_CLIENT_SECRET || '',
  scopes: ['Mail.Read', 'User.Read', 'MailboxSettings.Read', 'offline_access'],
  redirectPath: '/api/integrations/outlook/callback',
};

// WRITE APP - Mail.Send, User.Read, offline_access (NO Mail.ReadWrite!)
const WRITE_APP = {
  appId: process.env.AZURE_WRITE_APP_ID || 'f0b8944b-8127-4f0f-8ed5-5487462df50c',
  clientSecret: process.env.AZURE_WRITE_CLIENT_SECRET || '',
  scopes: ['Mail.Send', 'User.Read', 'offline_access'],
  redirectPath: '/api/integrations/outlook/write/callback',
};

const AZURE_TENANT = 'common';
const TOKEN_URL = `https://login.microsoftonline.com/${AZURE_TENANT}/oauth2/v2.0/token`;
const GRAPH_ME_URL = 'https://graph.microsoft.com/v1.0/me';

// ============================================================================
// FORBIDDEN SCOPES (doctrine enforcement)
// ============================================================================

const FORBIDDEN_SCOPES = [
  'Mail.ReadWrite',
  'Mail.ReadWrite.All',
  'Mail.ReadWrite.Shared',
  'Mail.ReadBasic.All',
  'Files.Read.All',
  'Files.ReadWrite.All',
  'Sites.Read.All',
  'Sites.ReadWrite.All',
  'Group.Read.All',
  'Group.ReadWrite.All',
  'User.Read.All',
  'User.ReadWrite.All',
];

// ============================================================================
// TYPES
// ============================================================================

export type TokenPurpose = 'read' | 'write';

export interface TokenRecord {
  user_id: string;
  yacht_id: string;
  provider: string;
  token_purpose: TokenPurpose;
  microsoft_access_token: string;
  microsoft_refresh_token: string;
  token_expires_at: string;
  scopes: string[];
  provider_email_hash: string;
  provider_display_name: string;
  is_revoked: boolean;
}

export interface WatcherStatus {
  sync_status: 'pending' | 'active' | 'read_only' | 'write_only' | 'degraded' | 'disconnected';
  last_sync_at: string | null;
  subscription_expires_at: string | null;
  last_sync_error: string | null;
}

export interface ConnectionStatus {
  read: {
    connected: boolean;
    expires_at: string | null;
    scopes: string[];
    email?: string;
  };
  write: {
    connected: boolean;
    expires_at: string | null;
    scopes: string[];
    email?: string;
  };
  watcher: WatcherStatus | null;
}

export interface ScopeCheckResult {
  valid: boolean;
  forbidden: string[];
  warning?: string;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Generate cryptographically secure state for OAuth CSRF protection
 */
export function generateOAuthState(userId: string, purpose: TokenPurpose): string {
  const randomBytes = new Uint8Array(16);
  crypto.getRandomValues(randomBytes);
  const random = Array.from(randomBytes, b => b.toString(16).padStart(2, '0')).join('');
  return `${userId}:${purpose}:${random}`;
}

/**
 * Parse OAuth state to extract user_id and purpose
 */
function parseOAuthState(state: string): { userId: string; purpose: TokenPurpose } | null {
  const parts = state.split(':');
  if (parts.length < 2) return null;

  const userId = parts[0];
  const purpose = parts[1] as TokenPurpose;

  if (!userId || (purpose !== 'read' && purpose !== 'write')) {
    return null;
  }

  return { userId, purpose };
}

/**
 * SHA256 hash of email address for privacy
 */
function hashEmail(email: string): string {
  return createHash('sha256').update(email.toLowerCase().trim()).digest('hex');
}

/**
 * Check scopes against forbidden list (doctrine enforcement)
 */
function checkScopes(scopes: string[]): ScopeCheckResult {
  const forbidden = scopes.filter(s =>
    FORBIDDEN_SCOPES.some(f => s.toLowerCase() === f.toLowerCase())
  );

  if (forbidden.length > 0) {
    return {
      valid: false,
      forbidden,
      warning: `Forbidden scopes detected: ${forbidden.join(', ')}. Token stored but watcher marked degraded.`,
    };
  }

  return { valid: true, forbidden: [] };
}

/**
 * Get Supabase client with service role
 */
function getServiceClient(): SupabaseClient {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY || '';
  return createClient(url, key);
}

/**
 * Get base URL for redirects
 */
function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai';
}

/**
 * Build Microsoft OAuth authorization URL
 */
export function buildAuthUrl(purpose: TokenPurpose, state: string): string {
  const app = purpose === 'read' ? READ_APP : WRITE_APP;
  const redirectUri = `${getBaseUrl()}${app.redirectPath}`;

  const authUrl = new URL(`https://login.microsoftonline.com/${AZURE_TENANT}/oauth2/v2.0/authorize`);
  authUrl.searchParams.set('client_id', app.appId);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('redirect_uri', redirectUri);
  authUrl.searchParams.set('scope', app.scopes.join(' '));
  authUrl.searchParams.set('state', state);
  authUrl.searchParams.set('response_mode', 'query');
  // Force account picker - don't auto-select cached Microsoft session
  authUrl.searchParams.set('prompt', 'select_account');

  return authUrl.toString();
}

/**
 * Exchange authorization code for tokens
 */
async function exchangeCodeForTokens(
  code: string,
  purpose: TokenPurpose
): Promise<{
  success: boolean;
  data?: {
    access_token: string;
    refresh_token: string;
    expires_in: number;
    scope: string;
  };
  error?: string;
}> {
  const app = purpose === 'read' ? READ_APP : WRITE_APP;
  const redirectUri = `${getBaseUrl()}${app.redirectPath}`;

  if (!app.clientSecret) {
    return {
      success: false,
      error: `Missing client secret for ${purpose} app`
    };
  }

  const response = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: app.appId,
      client_secret: app.clientSecret,
      code,
      grant_type: 'authorization_code',
      redirect_uri: redirectUri,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    return {
      success: false,
      error: errorData.error_description || errorData.error || 'Token exchange failed'
    };
  }

  const data = await response.json();
  return { success: true, data };
}

/**
 * Fetch user profile from Microsoft Graph
 */
async function fetchGraphProfile(accessToken: string): Promise<{
  email: string;
  displayName: string;
} | null> {
  try {
    const response = await fetch(GRAPH_ME_URL, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (!response.ok) return null;

    const data = await response.json();
    return {
      email: data.mail || data.userPrincipalName || '',
      displayName: data.displayName || '',
    };
  } catch {
    return null;
  }
}

/**
 * Get user's yacht_id from auth_users_profiles
 */
async function getUserYachtId(
  supabase: SupabaseClient,
  userId: string
): Promise<string | null> {
  const { data, error } = await supabase
    .from('auth_users_profiles')
    .select('yacht_id')
    .eq('id', userId)
    .single();

  if (error || !data) return null;
  return data.yacht_id;
}

/**
 * Upsert token record
 */
async function upsertToken(
  supabase: SupabaseClient,
  token: TokenRecord
): Promise<{ success: boolean; error?: string }> {
  const { error } = await supabase
    .from('auth_microsoft_tokens')
    .upsert(token, {
      onConflict: 'user_id,yacht_id,provider,token_purpose',
    });

  if (error) {
    return { success: false, error: error.message };
  }
  return { success: true };
}

/**
 * Get token by purpose
 */
async function getToken(
  supabase: SupabaseClient,
  userId: string,
  yachtId: string,
  purpose: TokenPurpose
): Promise<TokenRecord | null> {
  const { data, error } = await supabase
    .from('auth_microsoft_tokens')
    .select('*')
    .eq('user_id', userId)
    .eq('yacht_id', yachtId)
    .eq('provider', 'microsoft_graph')
    .eq('token_purpose', purpose)
    .eq('is_revoked', false)
    .single();

  if (error || !data) return null;
  return data as TokenRecord;
}

/**
 * Determine watcher sync_status based on token states
 */
function determineWatcherStatus(
  readToken: TokenRecord | null,
  writeToken: TokenRecord | null,
  hasForbiddenScopes: boolean
): WatcherStatus['sync_status'] {
  if (hasForbiddenScopes) return 'degraded';

  const readConnected = readToken && !readToken.is_revoked &&
    new Date(readToken.token_expires_at) > new Date();
  const writeConnected = writeToken && !writeToken.is_revoked &&
    new Date(writeToken.token_expires_at) > new Date();

  if (readConnected && writeConnected) return 'active';
  if (readConnected && !writeConnected) return 'read_only';
  if (!readConnected && writeConnected) return 'write_only';
  return 'disconnected';
}

/**
 * Upsert email_watchers record
 */
async function upsertWatcher(
  supabase: SupabaseClient,
  userId: string,
  yachtId: string,
  emailHash: string,
  syncStatus: WatcherStatus['sync_status']
): Promise<{ success: boolean; error?: string }> {
  const { error } = await supabase
    .from('email_watchers')
    .upsert({
      user_id: userId,
      yacht_id: yachtId,
      provider: 'microsoft_graph',
      mailbox_address_hash: emailHash,
      sync_status: syncStatus,
      updated_at: new Date().toISOString(),
    }, {
      onConflict: 'user_id,yacht_id,provider',
    });

  if (error) {
    return { success: false, error: error.message };
  }
  return { success: true };
}

/**
 * Get watcher status
 */
async function getWatcher(
  supabase: SupabaseClient,
  userId: string,
  yachtId: string
): Promise<WatcherStatus | null> {
  const { data, error } = await supabase
    .from('email_watchers')
    .select('sync_status, last_sync_at, subscription_expires_at, last_sync_error')
    .eq('user_id', userId)
    .eq('yacht_id', yachtId)
    .eq('provider', 'microsoft_graph')
    .single();

  if (error || !data) return null;
  return data as WatcherStatus;
}

/**
 * Revoke all tokens for user (soft delete)
 */
async function revokeAllTokens(
  supabase: SupabaseClient,
  userId: string,
  yachtId: string,
  revokedBy: string
): Promise<{ success: boolean; error?: string }> {
  const { error } = await supabase
    .from('auth_microsoft_tokens')
    .update({
      is_revoked: true,
      revoked_at: new Date().toISOString(),
      revoked_by: revokedBy,
    })
    .eq('user_id', userId)
    .eq('yacht_id', yachtId)
    .eq('provider', 'microsoft_graph')
    .eq('is_revoked', false);

  if (error) {
    return { success: false, error: error.message };
  }
  return { success: true };
}

/**
 * Mark watcher as disconnected
 */
async function disconnectWatcher(
  supabase: SupabaseClient,
  userId: string,
  yachtId: string
): Promise<{ success: boolean; error?: string }> {
  const { error } = await supabase
    .from('email_watchers')
    .update({
      sync_status: 'disconnected',
      updated_at: new Date().toISOString(),
    })
    .eq('user_id', userId)
    .eq('yacht_id', yachtId)
    .eq('provider', 'microsoft_graph');

  if (error) {
    return { success: false, error: error.message };
  }
  return { success: true };
}
