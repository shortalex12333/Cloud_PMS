'use client';

import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { Session, User } from '@supabase/supabase-js';

/**
 * AuthContext - Non-blocking authentication context
 *
 * Architecture (2026-01-13):
 * - Session existence = authenticated (fast path)
 * - Bootstrap data (yacht context) loaded in background
 * - Never blocks UI on slow RPCs
 * - PENDING state shows "Awaiting activation" screen
 */

export type BootstrapStatus =
  | 'loading'      // Initial state, fetching bootstrap
  | 'active'       // User has active yacht assignment
  | 'pending'      // User exists but account pending activation
  | 'inactive'     // Yacht is inactive
  | 'error';       // Bootstrap failed (will retry)

export type CelesteUser = {
  id: string;
  email: string | null;
  role: string;
  yachtId: string | null;
  yachtName: string | null;
  tenantKeyAlias: string | null;  // For backend DB routing (e.g., "y85fe1119...")
  displayName: string | null;
  bootstrapStatus: BootstrapStatus;
  validatedAt: number;
};

export type AuthContextValue = {
  user: CelesteUser | null;
  session: Session | null;  // Raw session for direct access
  loading: boolean;
  bootstrapping: boolean;   // True while loading yacht context
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshBootstrap: () => Promise<void>;
};

export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'eto', 'captain', 'manager'].includes(user.role);
}

export function isAuthenticated(user: CelesteUser | null): boolean {
  return user !== null;
}

export function isFullyActivated(user: CelesteUser | null): boolean {
  return user !== null && user.bootstrapStatus === 'active' && user.yachtId !== null;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Build minimal user from session (fast, no RPC)
 * Used for immediate auth state without blocking on bootstrap
 */
function buildUserFromSession(session: Session): CelesteUser {
  const authUser = session.user;
  const meta = authUser.user_metadata || {};

  return {
    id: authUser.id,
    email: authUser.email || null,
    role: (meta.role as string) || 'member',
    yachtId: (meta.yacht_id as string) || null,
    yachtName: null,
    tenantKeyAlias: null,  // Set from bootstrap RPC
    displayName: authUser.email || null,
    bootstrapStatus: 'loading',
    validatedAt: Date.now(),
  };
}

/**
 * Render API URL for bootstrap endpoint
 * Bootstrap MUST go through Render because:
 * - Frontend only has TENANT Supabase credentials
 * - get_my_bootstrap() RPC only exists on MASTER DB
 * - Render has MASTER DB credentials
 */
const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * Fetch bootstrap data from Render API with exponential backoff
 * Returns enriched user with yacht context
 *
 * Architecture (2026-01-16):
 * - Frontend calls Render: POST /v1/bootstrap with JWT
 * - Render looks up tenant from MASTER DB
 * - Returns yacht_id, tenant_key_alias, role, status
 *
 * Retry strategy: 2s, 4s, 8s, 16s timeouts (30s total before giving up)
 * This prevents tab-resume logout on slow connections
 */
async function fetchBootstrap(baseUser: CelesteUser, accessToken: string): Promise<CelesteUser> {
  const RETRY_TIMEOUTS = [2000, 4000, 8000, 16000]; // Exponential backoff
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < RETRY_TIMEOUTS.length; attempt++) {
    const timeout = RETRY_TIMEOUTS[attempt];

    try {
      console.log(`[AuthContext] Bootstrap attempt ${attempt + 1}/${RETRY_TIMEOUTS.length} (timeout: ${timeout}ms)`);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(`${RENDER_API_URL}/v1/bootstrap`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        console.warn(`[AuthContext] Bootstrap API error (attempt ${attempt + 1}): ${response.status} - ${errorText}`);

        // 403 = user not assigned to tenant or inactive - don't retry
        if (response.status === 403) {
          console.log('[AuthContext] User not assigned to tenant or inactive');
          return { ...baseUser, bootstrapStatus: 'pending', yachtId: null };
        }

        // 401 = invalid/expired token - don't retry
        if (response.status === 401) {
          console.log('[AuthContext] Token invalid or expired');
          return { ...baseUser, bootstrapStatus: 'error', yachtId: null };
        }

        lastError = new Error(`API error: ${response.status}`);
        continue; // Retry on other errors
      }

      const data = await response.json();
      console.log('[AuthContext] Bootstrap API success:', data.yacht_id, data.role);

      // Success - process the data
      return processBootstrapData(baseUser, data);

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        lastError = new Error(`Bootstrap timeout after ${timeout}ms`);
      } else {
        lastError = err instanceof Error ? err : new Error(String(err));
      }
      console.warn(`[AuthContext] Bootstrap attempt ${attempt + 1} failed:`, lastError.message);

      // Don't retry on last attempt
      if (attempt < RETRY_TIMEOUTS.length - 1) {
        // Small delay before retry
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  }

  // All retries exhausted - return error state but KEEP USER LOGGED IN
  console.error('[AuthContext] Bootstrap failed after all retries:', lastError?.message);
  return { ...baseUser, bootstrapStatus: 'error' };
}

/**
 * Process bootstrap response data
 */
function processBootstrapData(baseUser: CelesteUser, data: any): CelesteUser {
  if (!data) {
    console.log('[AuthContext] No bootstrap data, user pending');
    return { ...baseUser, bootstrapStatus: 'pending', yachtId: null };
  }

  // Handle different status values
  const status = data.status?.toUpperCase() || 'PENDING';

  if (status === 'PENDING_ACTIVATION' || status === 'PENDING') {
    console.log('[AuthContext] User pending activation');
    return {
      ...baseUser,
      bootstrapStatus: 'pending',
      yachtId: null,
      yachtName: null,
      tenantKeyAlias: null,
    };
  }

  if (status === 'YACHT_INACTIVE') {
    console.log('[AuthContext] Yacht inactive');
    return {
      ...baseUser,
      bootstrapStatus: 'inactive',
      yachtId: data.yacht_id,
      yachtName: data.yacht_name,
      tenantKeyAlias: data.tenant_key_alias || null,
    };
  }

  if (status !== 'ACTIVE') {
    console.log('[AuthContext] Account status:', status);
    return {
      ...baseUser,
      bootstrapStatus: 'pending',
      yachtId: data.yacht_id,
      yachtName: data.yacht_name,
      tenantKeyAlias: data.tenant_key_alias || null,
    };
  }

  // Success - user is fully active
  console.log('[AuthContext] Bootstrap success:', data.yacht_id, data.role, data.tenant_key_alias);
  return {
    ...baseUser,
    role: data.role || baseUser.role,
    yachtId: data.yacht_id,
    yachtName: data.yacht_name,
    tenantKeyAlias: data.tenant_key_alias || null,
    bootstrapStatus: 'active',
    validatedAt: Date.now(),
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);
  const bootstrapRetryRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Refresh bootstrap data (can be called manually to retry after error)
   */
  const refreshBootstrap = useCallback(async () => {
    if (!user || !session) return;

    setBootstrapping(true);
    const enrichedUser = await fetchBootstrap(user, session.access_token);
    setUser(enrichedUser);
    setBootstrapping(false);

    // If error, schedule retry
    if (enrichedUser.bootstrapStatus === 'error') {
      bootstrapRetryRef.current = setTimeout(() => {
        console.log('[AuthContext] Retrying bootstrap...');
        refreshBootstrap();
      }, 10000); // Retry in 10s
    }
  }, [user, session]);

  /**
   * Handle session changes - fast path, sets user immediately from session
   * Then triggers background bootstrap for yacht context
   */
  const handleSession = useCallback(async (newSession: Session | null) => {
    setSession(newSession);

    if (!newSession) {
      setUser(null);
      setLoading(false);
      setBootstrapping(false);
      return;
    }

    // FAST PATH: Build user from session immediately (no RPC)
    const baseUser = buildUserFromSession(newSession);
    setUser(baseUser);
    setLoading(false);

    // BACKGROUND: Fetch bootstrap data (yacht context) via Render API
    setBootstrapping(true);
    const enrichedUser = await fetchBootstrap(baseUser, newSession.access_token);
    setUser(enrichedUser);
    setBootstrapping(false);

    // Schedule retry if bootstrap failed
    if (enrichedUser.bootstrapStatus === 'error') {
      bootstrapRetryRef.current = setTimeout(() => {
        console.log('[AuthContext] Retrying bootstrap after error...');
        refreshBootstrap();
      }, 10000);
    }
  }, []);

  useEffect(() => {
    // Only run on client-side
    if (typeof window === 'undefined') {
      return;
    }

    if (initialized.current) return;
    initialized.current = true;

    console.log('[AuthContext] Init - non-blocking auth');

    let subscription: { unsubscribe: () => void } | null = null;

    const initAuth = async () => {
      try {
        // Set up auth state listener
        const { data } = supabase.auth.onAuthStateChange(async (event, eventSession) => {
          console.log('[AuthContext] Auth event:', event, '| Session:', !!eventSession);

          if (event === 'SIGNED_OUT') {
            setUser(null);
            setSession(null);
            setError(null);
            setLoading(false);
            setBootstrapping(false);
          } else if (event === 'INITIAL_SESSION' || event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
            await handleSession(eventSession);
          }
        });

        subscription = data.subscription;

        // Also check current session immediately (don't wait for event)
        const { data: { session: currentSession } } = await supabase.auth.getSession();
        if (currentSession && !user) {
          await handleSession(currentSession);
        } else if (!currentSession) {
          setLoading(false);
        }

      } catch (err) {
        console.error('[AuthContext] Init error:', err);
        setLoading(false);
      }
    };

    initAuth();

    return () => {
      if (subscription) subscription.unsubscribe();
      if (bootstrapRetryRef.current) clearTimeout(bootstrapRetryRef.current);
    };
  }, [handleSession]);

  /**
   * Tab visibility handler - re-check session when user returns to tab
   * This prevents logout after tab-switching on mobile or slow connections
   */
  useEffect(() => {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }

    const handleVisibilityChange = async () => {
      if (document.visibilityState !== 'visible') {
        return; // Tab is hidden, no action needed
      }

      console.log('[AuthContext] Tab became visible, checking session...');

      try {
        // Quick session check (no RPC, fast)
        const { data: { session: currentSession } } = await supabase.auth.getSession();

        if (!currentSession) {
          // User is actually logged out - clear state
          console.log('[AuthContext] No session on tab resume - user logged out');
          setUser(null);
          setSession(null);
          setLoading(false);
          return;
        }

        // Session exists - update session state
        setSession(currentSession);

        // If we have a user but bootstrap failed/errored, retry bootstrap
        if (user && (user.bootstrapStatus === 'error' || user.bootstrapStatus === 'loading')) {
          console.log('[AuthContext] Tab resume: retrying bootstrap...');
          setBootstrapping(true);
          const enrichedUser = await fetchBootstrap(user, currentSession.access_token);
          setUser(enrichedUser);
          setBootstrapping(false);
        } else if (!user && currentSession) {
          // Edge case: session exists but no user (shouldn't happen, but handle it)
          console.log('[AuthContext] Tab resume: session exists but no user, re-initializing...');
          await handleSession(currentSession);
        }

      } catch (err) {
        console.warn('[AuthContext] Tab resume check failed:', err);
        // Don't logout on error - keep existing state
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, handleSession]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    console.log('[AuthContext] Login attempt:', email);

    const { data, error: loginError } = await supabase.auth.signInWithPassword({ email, password });

    if (loginError) {
      console.error('[AuthContext] Login error:', loginError.message);
      throw new Error(loginError.message);
    }

    if (!data.session) {
      console.error('[AuthContext] No session returned after login');
      throw new Error('No session');
    }

    console.log('[AuthContext] Login successful');
    // Session change will be handled by onAuthStateChange listener
    // No need to manually call handleSession here
  }, []);

  const logout = useCallback(async () => {
    if (bootstrapRetryRef.current) {
      clearTimeout(bootstrapRetryRef.current);
    }
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      session,
      loading,
      bootstrapping,
      error,
      login,
      logout,
      refreshBootstrap
    }}>
      {children}
    </AuthContext.Provider>
  );
}
