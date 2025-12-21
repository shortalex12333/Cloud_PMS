'use client';

import React, { createContext, useEffect, useState, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import type { User } from '@supabase/supabase-js';

// CelesteOS user type - GDPR-minimized
// Role mapping: chief_engineer, captain, manager = HOD (Head of Department)
export type CelesteUser = {
  id: string; // user_id
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
// HOD roles: chief_engineer, eto, captain, manager
export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'eto', 'captain', 'manager'].includes(user.role);
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

/**
 * Build CelesteUser from Supabase auth user
 * Uses user_metadata from auth.users - no separate profile table needed
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

  // Initialize auth state
  useEffect(() => {
    console.log('[AuthContext] Initializing...');
    let resolved = false;

    // Timeout to prevent hanging forever
    const timeout = setTimeout(() => {
      if (!resolved) {
        console.warn('[AuthContext] getSession timeout after 3s');
        resolved = true;
        setLoading(false);
      }
    }, 3000);

    // Check current session
    supabase.auth.getSession()
      .then(({ data: { session }, error }) => {
        if (resolved) return; // Already timed out
        resolved = true;
        clearTimeout(timeout);

        if (error) {
          console.error('[AuthContext] getSession error:', error.message);
          setLoading(false);
          return;
        }

        if (session?.user) {
          const celesteUser = buildUserFromAuth(session.user);
          console.log('[AuthContext] Session found:', celesteUser.email);
          setUser(celesteUser);
        } else {
          console.log('[AuthContext] No session');
        }
        setLoading(false);
      })
      .catch((err) => {
        if (resolved) return;
        resolved = true;
        clearTimeout(timeout);
        console.error('[AuthContext] getSession exception:', err);
        setLoading(false);
      });

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      console.log('[AuthContext] Auth state:', event);

      if (event === 'SIGNED_IN' && session?.user) {
        const celesteUser = buildUserFromAuth(session.user);
        setUser(celesteUser);
        setLoading(false);
      } else if (event === 'SIGNED_OUT') {
        setUser(null);
        setLoading(false);
      } else if (event === 'TOKEN_REFRESHED' && session?.user) {
        // Refresh user data on token refresh (metadata may have changed)
        const celesteUser = buildUserFromAuth(session.user);
        setUser(celesteUser);
      }
    });

    return () => {
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, []);

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

    const celesteUser = buildUserFromAuth(data.user);
    setUser(celesteUser);
    console.log('[AuthContext] Login success:', celesteUser.id);
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    console.log('[AuthContext] Logout');

    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('[AuthContext] Logout error:', error);
      throw error;
    }

    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
