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
 * Fetch bootstrap data from master DB (background, non-blocking)
 * Returns enriched user with yacht context
 */
async function fetchBootstrap(baseUser: CelesteUser): Promise<CelesteUser> {
  try {
    console.log('[AuthContext] Fetching bootstrap for user:', baseUser.id);

    // Call get_my_bootstrap RPC with 5s timeout (fast RPC on master DB)
    const rpcPromise = supabase.rpc('get_my_bootstrap');

    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Bootstrap timeout after 5s')), 5000);
    });

    const result = await Promise.race([rpcPromise, timeoutPromise]);
    const { data, error } = result;

    if (error) {
      console.error('[AuthContext] Bootstrap RPC error:', error.message);
      return { ...baseUser, bootstrapStatus: 'error' };
    }

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

  } catch (err) {
    console.error('[AuthContext] Bootstrap error:', err);
    return { ...baseUser, bootstrapStatus: 'error' };
  }
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
    if (!user) return;

    setBootstrapping(true);
    const enrichedUser = await fetchBootstrap(user);
    setUser(enrichedUser);
    setBootstrapping(false);

    // If error, schedule retry
    if (enrichedUser.bootstrapStatus === 'error') {
      bootstrapRetryRef.current = setTimeout(() => {
        console.log('[AuthContext] Retrying bootstrap...');
        refreshBootstrap();
      }, 10000); // Retry in 10s
    }
  }, [user]);

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

    // BACKGROUND: Fetch bootstrap data (yacht context)
    setBootstrapping(true);
    const enrichedUser = await fetchBootstrap(baseUser);
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
