'use client';

import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { Session } from '@supabase/supabase-js';

// Debug function to log auth state
async function debugAuthState(label: string) {
  console.log(`\n========== AUTH DEBUG: ${label} ==========`);

  // Check environment
  console.log('[DEBUG] Supabase URL set:', !!process.env.NEXT_PUBLIC_SUPABASE_URL);
  console.log('[DEBUG] Supabase Anon Key set:', !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

  try {
    // Get current session
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();

    if (sessionError) {
      console.error('[DEBUG] Session error:', sessionError.message);
      return;
    }

    if (!session) {
      console.log('[DEBUG] No active session');
      console.log('[DEBUG] JWT present: false');
      return;
    }

    // Session exists - log details
    console.log('[DEBUG] Session exists: true');
    console.log('[DEBUG] JWT present:', !!session.access_token);
    console.log('[DEBUG] JWT length:', session.access_token?.length || 0);
    console.log('[DEBUG] JWT expires at:', session.expires_at ? new Date(session.expires_at * 1000).toISOString() : 'N/A');
    console.log('[DEBUG] JWT expired:', session.expires_at ? Date.now() > session.expires_at * 1000 : 'unknown');
    console.log('[DEBUG] Refresh token present:', !!session.refresh_token);
    console.log('[DEBUG] User ID:', session.user?.id || 'N/A');
    console.log('[DEBUG] User email:', session.user?.email || 'N/A');
    console.log('[DEBUG] User metadata:', JSON.stringify(session.user?.user_metadata || {}));
    console.log('[DEBUG] Auth provider:', session.user?.app_metadata?.provider || 'N/A');

  } catch (err) {
    console.error('[DEBUG] Error checking auth state:', err);
  }

  console.log('==========================================\n');
}

export type CelesteUser = {
  id: string;
  email: string | null;
  role: 'chief_engineer' | 'eto' | 'captain' | 'manager' | 'vendor' | 'crew' | 'deck' | 'interior';
  yachtId: string | null;
  displayName: string | null;
  validatedAt: number;
};

export type AuthContextValue = {
  user: CelesteUser | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  validateSession: () => Promise<boolean>;
};

export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'eto', 'captain', 'manager'].includes(user.role);
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function validateAndBuildUser(session: Session | null): Promise<CelesteUser | null> {
  if (!session?.user) {
    console.log('[AuthContext] No session');
    return null;
  }

  const authUser = session.user;
  console.log('[AuthContext] Validating:', authUser.email);

  // Debug auth state before RPC
  await debugAuthState('Before RPC call');

  try {
    // Use RPC function (SECURITY DEFINER - bypasses RLS)
    // Add timeout via Promise.race
    console.log('[AuthContext] Calling RPC get_user_auth_info with user_id:', authUser.id);

    const rpcPromise = supabase.rpc('get_user_auth_info', {
      p_user_id: authUser.id
    });

    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('RPC timeout after 5s')), 5000);
    });

    const { data, error } = await Promise.race([rpcPromise, timeoutPromise]);
    console.log('[AuthContext] RPC result:', { data, error: error?.message });

    if (error) {
      console.error('[AuthContext] RPC error:', error.message);
      return null;
    }

    const dbUser = Array.isArray(data) ? data[0] : data;

    if (!dbUser) {
      console.error('[AuthContext] User not in auth_users');
      return null;
    }

    if (!dbUser.is_active) {
      console.error('[AuthContext] User deactivated');
      return null;
    }

    if (!dbUser.yacht_id) {
      console.error('[AuthContext] No yacht assignment');
      return null;
    }

    console.log('[AuthContext] Validated:', dbUser.email, dbUser.yacht_id);

    const meta = authUser.user_metadata || {};
    return {
      id: authUser.id,
      email: authUser.email || null,
      role: (meta.role as CelesteUser['role']) || 'crew',
      yachtId: dbUser.yacht_id,
      displayName: dbUser.name || authUser.email || null,
      validatedAt: Date.now(),
    };
  } catch (err) {
    console.error('[AuthContext] Error:', err);
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);

  const validateSession = useCallback(async (): Promise<boolean> => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setUser(null);
        return false;
      }
      const validatedUser = await validateAndBuildUser(session);
      setUser(validatedUser);
      return !!validatedUser;
    } catch {
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    console.log('[AuthContext] Init - starting auth state listener');

    // First, try to get existing session
    const initSession = async () => {
      console.log('[AuthContext] Checking for existing session...');
      try {
        const { data: { session }, error } = await supabase.auth.getSession();

        if (error) {
          console.error('[AuthContext] getSession error:', error.message);
          setLoading(false);
          return;
        }

        if (session) {
          console.log('[AuthContext] Found existing session for:', session.user.email);
          const validatedUser = await validateAndBuildUser(session);
          setUser(validatedUser);
          setError(validatedUser ? null : 'User not configured');
        } else {
          console.log('[AuthContext] No existing session found');
        }
        setLoading(false);
      } catch (err) {
        console.error('[AuthContext] Init error:', err);
        setLoading(false);
      }
    };

    initSession();

    // Set up listener for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthContext] Auth event:', event, '| Session present:', !!session);

      if (event === 'SIGNED_OUT') {
        setUser(null);
        setError(null);
        setLoading(false);
      } else if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        if (session) {
          const validatedUser = await validateAndBuildUser(session);
          setUser(validatedUser);
          setError(validatedUser ? null : 'User not configured');
        }
        setLoading(false);
      }
      // Ignore INITIAL_SESSION as we handle it above
    });

    // Fallback timeout (reduced to 3s since we're now proactive)
    const timeout = setTimeout(() => {
      if (loading) {
        console.log('[AuthContext] Timeout - forcing loading=false');
        setLoading(false);
      }
    }, 3000);

    return () => {
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, []);

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

    console.log('[AuthContext] Login successful, session obtained');
    await debugAuthState('After successful login');

    const validatedUser = await validateAndBuildUser(data.session);
    if (!validatedUser) {
      console.error('[AuthContext] User validation failed - signing out');
      await supabase.auth.signOut();
      throw new Error('Account not configured. Contact admin.');
    }

    console.log('[AuthContext] User validated successfully:', validatedUser.email);
    setUser(validatedUser);
  }, []);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, validateSession }}>
      {children}
    </AuthContext.Provider>
  );
}
