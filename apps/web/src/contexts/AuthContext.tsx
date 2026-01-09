'use client';

/**
 * AuthContext - Secure Authentication Provider
 *
 * Security Requirements:
 * - Always validate session with Supabase on mount (don't trust cache)
 * - Verify user exists in auth_users table with valid yacht assignment
 * - Force re-authentication if session is invalid or expired
 * - Never allow access without confirmed valid session
 */

import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { Session } from '@supabase/supabase-js';

// CelesteOS user type - includes validated yacht_id from database
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

// Helper function to check if user is HOD (Head of Department)
export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'eto', 'captain', 'manager'].includes(user.role);
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Validate session and fetch user data from auth_users table
 * Returns null if session is invalid or user not found in database
 */
async function validateAndBuildUser(session: Session | null): Promise<CelesteUser | null> {
  if (!session?.user) {
    console.log('[AuthContext] No session to validate');
    return null;
  }

  const authUser = session.user;
  console.log('[AuthContext] Validating user:', authUser.email, 'id:', authUser.id);

  try {
    // Small delay to ensure Supabase client has JWT ready after auth state change
    await new Promise(resolve => setTimeout(resolve, 100));

    // Query auth_users table - use maybeSingle() to avoid throwing on 0 rows
    console.log('[AuthContext] Querying auth_users table...');
    const { data: dbUser, error } = await supabase
      .from('auth_users')
      .select('yacht_id, email, name, is_active')
      .eq('auth_user_id', authUser.id)
      .maybeSingle();

    console.log('[AuthContext] Query result:', { dbUser, error: error?.message });

    if (error) {
      console.error('[AuthContext] Database error:', error.message, error.code);
      return null;
    }

    if (!dbUser) {
      console.error('[AuthContext] User not found in auth_users table for id:', authUser.id);
      return null;
    }

    if (!dbUser.is_active) {
      console.error('[AuthContext] User account is deactivated');
      return null;
    }

    if (!dbUser.yacht_id) {
      console.error('[AuthContext] User has no yacht assignment');
      return null;
    }

    console.log('[AuthContext] User validated successfully:', {
      email: authUser.email,
      yacht_id: dbUser.yacht_id,
    });

    const meta = authUser.user_metadata || {};

    return {
      id: authUser.id,
      email: authUser.email || null,
      role: (meta.role as CelesteUser['role']) || 'crew',
      yachtId: dbUser.yacht_id,
      displayName: dbUser.name || meta.name || authUser.email || null,
      validatedAt: Date.now(),
    };
  } catch (err) {
    console.error('[AuthContext] Validation error:', err);
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const initialized = useRef(false);

  /**
   * Validate current session - can be called anytime to re-verify
   */
  const validateSession = useCallback(async (): Promise<boolean> => {
    console.log('[AuthContext] validateSession called');

    try {
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError) {
        console.error('[AuthContext] Session error:', sessionError.message);
        setUser(null);
        setError('Session error');
        return false;
      }

      if (!session) {
        console.log('[AuthContext] No active session');
        setUser(null);
        return false;
      }

      console.log('[AuthContext] Session found, validating user...');

      // Check if token is expired
      const expiresAt = session.expires_at || 0;
      const now = Math.floor(Date.now() / 1000);

      if (expiresAt < now) {
        console.log('[AuthContext] Session expired, refreshing...');
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();

        if (refreshError || !refreshData.session) {
          console.error('[AuthContext] Refresh failed:', refreshError?.message);
          setUser(null);
          return false;
        }

        const validatedUser = await validateAndBuildUser(refreshData.session);
        setUser(validatedUser);
        return !!validatedUser;
      }

      const validatedUser = await validateAndBuildUser(session);
      setUser(validatedUser);
      setError(validatedUser ? null : 'User not found in database');
      return !!validatedUser;

    } catch (err) {
      console.error('[AuthContext] validateSession error:', err);
      setUser(null);
      setError('Validation failed');
      return false;
    }
  }, []);

  // Initialize auth on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    console.log('[AuthContext] Initializing...');

    // Subscribe to auth state changes FIRST
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthContext] Auth event:', event);

      if (event === 'SIGNED_OUT') {
        setUser(null);
        setError(null);
        setLoading(false);
      } else if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'INITIAL_SESSION') {
        if (session) {
          const validatedUser = await validateAndBuildUser(session);
          setUser(validatedUser);
          if (!validatedUser) {
            setError('User not found in database');
          }
        }
        setLoading(false);
      }
    });

    // Timeout fallback - end loading after 5 seconds no matter what
    const timeout = setTimeout(() => {
      if (loading) {
        console.warn('[AuthContext] Timeout - ending loading state');
        setLoading(false);
      }
    }, 5000);

    return () => {
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, []);

  // Login function
  const login = useCallback(async (email: string, password: string) => {
    console.log('[AuthContext] Login attempt:', email);
    setError(null);

    const { data, error: loginError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (loginError) {
      console.error('[AuthContext] Login error:', loginError.message);
      throw new Error(loginError.message);
    }

    if (!data.session) {
      throw new Error('No session returned from login');
    }

    console.log('[AuthContext] Login successful, validating user...');

    // Validate user exists in database with yacht assignment
    const validatedUser = await validateAndBuildUser(data.session);

    if (!validatedUser) {
      await supabase.auth.signOut();
      throw new Error('Account not properly configured. Contact administrator.');
    }

    setUser(validatedUser);
    console.log('[AuthContext] Login complete:', validatedUser.email);
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    console.log('[AuthContext] Logout');
    setError(null);

    const { error: logoutError } = await supabase.auth.signOut();
    if (logoutError) {
      console.error('[AuthContext] Logout error:', logoutError);
      throw logoutError;
    }

    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    error,
    login,
    logout,
    validateSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
