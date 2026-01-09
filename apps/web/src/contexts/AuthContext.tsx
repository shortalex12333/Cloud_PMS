'use client';

import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { Session } from '@supabase/supabase-js';

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

  try {
    // Use RPC function (SECURITY DEFINER - bypasses RLS)
    // Add timeout via Promise.race
    const rpcPromise = supabase.rpc('get_user_auth_info', {
      p_user_id: authUser.id
    });

    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('RPC timeout')), 5000);
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

    console.log('[AuthContext] Init');

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthContext] Event:', event);

      if (event === 'SIGNED_OUT') {
        setUser(null);
        setError(null);
        setLoading(false);
      } else if (session) {
        const validatedUser = await validateAndBuildUser(session);
        setUser(validatedUser);
        setError(validatedUser ? null : 'User not configured');
        setLoading(false);
      } else {
        setLoading(false);
      }
    });

    // Fallback timeout
    const timeout = setTimeout(() => setLoading(false), 6000);

    return () => {
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    console.log('[AuthContext] Login:', email);

    const { data, error: loginError } = await supabase.auth.signInWithPassword({ email, password });

    if (loginError) throw new Error(loginError.message);
    if (!data.session) throw new Error('No session');

    const validatedUser = await validateAndBuildUser(data.session);
    if (!validatedUser) {
      await supabase.auth.signOut();
      throw new Error('Account not configured. Contact admin.');
    }

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
