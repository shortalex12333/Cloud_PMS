'use client';

import React, { createContext, useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { User } from '@supabase/supabase-js';

// CelesteOS user type - GDPR-minimized
export type CelesteUser = {
  id: string;
  email: string | null;
  role: 'chief_engineer' | 'eto' | 'captain' | 'manager' | 'vendor' | 'crew' | 'deck' | 'interior';
  yachtId: string | null;
  displayName: string | null;
};

export type AuthContextValue = {
  user: CelesteUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

// Helper function to check if user is HOD (Head of Department)
export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'eto', 'captain', 'manager'].includes(user.role);
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Build CelesteUser from Supabase auth user
 */
function buildUserFromAuth(authUser: User): CelesteUser {
  const meta = authUser.user_metadata || {};
  return {
    id: authUser.id,
    email: authUser.email || null,
    role: (meta.role as CelesteUser['role']) || 'crew',
    yachtId: meta.yacht_id || meta.yachtId || null,
    displayName: meta.name || meta.display_name || meta.full_name || authUser.email || null,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [loading, setLoading] = useState(true);
  const initialized = useRef(false);

  // Initialize auth using onAuthStateChange (more reliable than getSession)
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    console.log('[AuthContext] Setting up auth listener...');

    // Fallback timeout - if no auth event received in 2s, end loading
    const fallbackTimeout = setTimeout(() => {
      if (loading) {
        console.warn('[AuthContext] No auth event received in 2s, ending loading state');
        setLoading(false);
      }
    }, 2000);

    // Subscribe to auth state changes - this fires immediately with INITIAL_SESSION
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('[AuthContext] Auth event:', event, session?.user?.email || 'no user');

      clearTimeout(fallbackTimeout);

      if (session?.user) {
        const celesteUser = buildUserFromAuth(session.user);
        setUser(celesteUser);
      } else {
        setUser(null);
      }

      // End loading on any auth event
      setLoading(false);
    });

    return () => {
      clearTimeout(fallbackTimeout);
      subscription.unsubscribe();
    };
  }, [loading]);

  // Login function
  const login = useCallback(async (email: string, password: string) => {
    console.log('[AuthContext] Login:', email);

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      console.error('[AuthContext] Login error:', error.message);
      throw new Error(error.message);
    }

    if (!data.user) {
      throw new Error('No user returned from login');
    }

    // User will be set by onAuthStateChange listener
    console.log('[AuthContext] Login success:', data.user.id);
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    console.log('[AuthContext] Logout');

    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('[AuthContext] Logout error:', error);
      throw error;
    }
    // User will be cleared by onAuthStateChange listener
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
