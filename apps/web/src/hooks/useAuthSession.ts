'use client';

import { useContext, useEffect, useState, useCallback } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import { supabase } from '@/lib/supabaseClient';

/**
 * useAuthSession - Single source of truth for session/token access
 *
 * Solves the race condition where getSession() returns null after hard refresh.
 * Consumers MUST await isReady before making authenticated API calls.
 *
 * Usage:
 *   const { accessToken, isReady, refreshToken } = useAuthSession();
 *   if (!isReady) return <Spinner />;
 *   await authFetch(url, accessToken);
 */

export interface AuthSessionState {
  accessToken: string | null;
  expiresAt: number | null;  // Unix timestamp in seconds
  isReady: boolean;
  isAuthenticated: boolean;
  refreshToken: () => Promise<string | null>;
}

export function useAuthSession(): AuthSessionState {
  const authContext = useContext(AuthContext);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<number | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Refresh token function - defined first so it can be used in effects
  const refreshTokenInternal = useCallback(async (): Promise<string | null> => {
    try {
      console.log('[useAuthSession] Refreshing session...');
      const { data, error } = await supabase.auth.refreshSession();

      if (error) {
        console.error('[useAuthSession] Refresh failed:', error.message);
        return null;
      }

      if (data.session) {
        setAccessToken(data.session.access_token);
        setExpiresAt(data.session.expires_at || null);
        console.log('[useAuthSession] Session refreshed, new expiry:',
          data.session.expires_at ? new Date(data.session.expires_at * 1000).toISOString() : 'N/A');
        return data.session.access_token;
      }

      return null;
    } catch (err) {
      console.error('[useAuthSession] Refresh error:', err);
      return null;
    }
  }, []);

  // Initialize from AuthContext session
  useEffect(() => {
    if (!authContext) return;

    if (authContext.session) {
      setAccessToken(authContext.session.access_token);
      setExpiresAt(authContext.session.expires_at || null);
      setIsReady(true);
      console.log('[useAuthSession] Initialized from AuthContext, token length:', authContext.session.access_token?.length);
    } else if (!authContext.loading) {
      // AuthContext loaded but no session = not authenticated
      setAccessToken(null);
      setExpiresAt(null);
      setIsReady(true);
      console.log('[useAuthSession] AuthContext loaded, no session');
    }
  }, [authContext]);

  // Proactive refresh if token is expiring soon
  useEffect(() => {
    if (!isReady || !accessToken || !expiresAt) return;

    const nowSec = Math.floor(Date.now() / 1000);
    const timeUntilExpiry = expiresAt - nowSec;

    // If expiring within 60 seconds, refresh now
    if (timeUntilExpiry < 60) {
      console.log('[useAuthSession] Token expiring soon, refreshing...');
      refreshTokenInternal();
    } else {
      // Schedule refresh 60s before expiry
      const refreshIn = (timeUntilExpiry - 60) * 1000;
      const timer = setTimeout(() => {
        console.log('[useAuthSession] Scheduled token refresh');
        refreshTokenInternal();
      }, refreshIn);
      return () => clearTimeout(timer);
    }
  }, [isReady, accessToken, expiresAt, refreshTokenInternal]);

  // Public refresh function that returns fresh token
  const refreshToken = useCallback(async (): Promise<string | null> => {
    const token = await refreshTokenInternal();
    return token;
  }, [refreshTokenInternal]);

  return {
    accessToken,
    expiresAt,
    isReady,
    isAuthenticated: !!accessToken,
    refreshToken,
  };
}

/**
 * waitForSession - Utility to wait for session to be ready
 * Use this in event handlers where you can't use hooks directly
 */
export async function waitForSession(timeoutMs: number = 5000): Promise<string | null> {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    const { data: { session } } = await supabase.auth.getSession();

    if (session?.access_token) {
      // Check if token is expiring soon
      const nowSec = Math.floor(Date.now() / 1000);
      if (session.expires_at && session.expires_at - nowSec < 60) {
        console.log('[waitForSession] Token expiring soon, refreshing...');
        const { data: refreshData } = await supabase.auth.refreshSession();
        if (refreshData.session?.access_token) {
          return refreshData.session.access_token;
        }
      }
      return session.access_token;
    }

    // Wait 100ms before retry
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  console.error('[waitForSession] Timeout waiting for session');
  return null;
}
