'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [loading, setLoading] = useState(true);
  const fetchingRef = React.useRef(false);

  // Fetch user profile from users table (production schema)
  const fetchUserProfile = useCallback(async (authUser: User) => {
    // Prevent concurrent fetches
    if (fetchingRef.current) {
      console.log('[AuthContext] ⏸️ Already fetching, skipping...');
      return null;
    }

    fetchingRef.current = true;
    console.log('[AuthContext] ▶ fetchUserProfile START for:', authUser.email);

    try {
      console.log('[AuthContext] Fetching user profile...');

      // Fast timeout - if RLS blocks, fail fast and use fallback (2 seconds max)
      const timeoutMs = 2000;
      const timeoutPromise = new Promise<{ data: null; error: { message: string } }>((resolve) =>
        setTimeout(() => resolve({
          data: null,
          error: { message: 'Query timeout - using fallback profile' }
        }), timeoutMs)
      );

      const queryPromise = supabase
        .from('users')
        .select('id, auth_user_id, email, yacht_id, name, metadata')
        .eq('email', authUser.email)
        .maybeSingle();

      const { data: userData, error: userError } = await Promise.race([
        queryPromise,
        timeoutPromise
      ]);

      // Fallback profile using auth.users data when public.users query fails
      const fallbackProfile: CelesteUser = {
        id: authUser.id,
        email: authUser.email || null,
        role: 'crew', // Default role
        yachtId: null,
        displayName: authUser.email || null,
      };

      if (userError) {
        console.error('[AuthContext] ❌ Query returned error:', {
          message: userError.message,
          details: (userError as any).details,
          hint: (userError as any).hint,
          code: (userError as any).code,
        });
        console.warn('[AuthContext] ⚠️ Using fallback profile from auth.users');
        return fallbackProfile;
      }

      if (!userData) {
        console.warn('[AuthContext] ⚠️ No user profile found for:', authUser.email);
        console.warn('[AuthContext] Using fallback profile - user can still access system');
        return fallbackProfile;
      }

      console.log('[AuthContext] ✅ User data received:', userData);

      // Role may be in metadata.role or default to 'crew'
      const metadata = userData.metadata as { role?: string } | null;
      const userRole = metadata?.role || 'crew';

      const celesteUser: CelesteUser = {
        id: userData.auth_user_id || userData.id,
        email: userData.email,
        role: userRole as CelesteUser['role'],
        yachtId: userData.yacht_id,
        displayName: userData.name,
      };

      console.log('[AuthContext] ✅ User profile loaded:', celesteUser.email);

      return celesteUser;
    } catch (err) {
      console.error('[AuthContext] ❌ Exception in fetchUserProfile:', err);
      // Return fallback profile so user can still access the system
      console.warn('[AuthContext] ⚠️ Using fallback profile due to exception');
      return {
        id: authUser.id,
        email: authUser.email || null,
        role: 'crew' as const,
        yachtId: null,
        displayName: authUser.email || null,
      };
    } finally {
      fetchingRef.current = false;
      console.log('[AuthContext] ◀ fetchUserProfile END');
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    console.log('[AuthContext] Initializing auth state...');

    // Fast timeout - don't wait if Supabase is slow/unreachable
    const sessionTimeout = 2000;
    let didTimeout = false;

    const timeoutId = setTimeout(() => {
      didTimeout = true;
      console.warn('[AuthContext] ⚠️ getSession timeout - Supabase may be unreachable');
      setLoading(false); // Allow UI to render regardless
    }, sessionTimeout);

    // Check current session with error handling
    supabase.auth.getSession()
      .then(({ data: { session }, error }) => {
        if (didTimeout) {
          console.log('[AuthContext] Session response received after timeout, ignoring');
          return;
        }
        clearTimeout(timeoutId);

        if (error) {
          console.error('[AuthContext] getSession error:', error);
          setLoading(false);
          return;
        }

        console.log('[AuthContext] Current session:', session ? 'exists' : 'none');
        if (session?.user) {
          fetchUserProfile(session.user)
            .then((profile) => {
              setUser(profile);
            })
            .catch((err) => {
              console.error('[AuthContext] Failed to fetch profile on init:', err);
              setUser(null);
            })
            .finally(() => {
              setLoading(false);
            });
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        if (didTimeout) return;
        clearTimeout(timeoutId);
        console.error('[AuthContext] ❌ getSession exception:', err);
        setLoading(false); // Always allow UI to render
      });

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthContext] Auth state changed:', event);

      if (event === 'SIGNED_IN' && session?.user) {
        const profile = await fetchUserProfile(session.user);
        setUser(profile);
        setLoading(false); // ← FIX: End loading state
      } else if (event === 'SIGNED_OUT') {
        setUser(null);
        setLoading(false); // ← FIX: End loading state
      } else if (event === 'TOKEN_REFRESHED' && session?.user) {
        // Optionally refresh user profile on token refresh
        const profile = await fetchUserProfile(session.user);
        setUser(profile);
        // Don't change loading state on token refresh
      }
    });

    return () => {
      clearTimeout(timeoutId);
      subscription.unsubscribe();
    };
  }, [fetchUserProfile]);

  // Login function
  const login = useCallback(
    async (email: string, password: string) => {
      console.log('[AuthContext] Login attempt for:', email);

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

      // Fetch user profile
      const profile = await fetchUserProfile(data.user);
      if (!profile) {
        throw new Error('User profile not found. Please contact support.');
      }

      setUser(profile);
      console.log('[AuthContext] Login successful:', profile.id);
    },
    [fetchUserProfile]
  );

  // Logout function
  const logout = useCallback(async () => {
    console.log('[AuthContext] Logout initiated');

    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('[AuthContext] Logout error:', error);
      throw error;
    }

    setUser(null);
    console.log('[AuthContext] Logout successful');
  }, []);

  const value: AuthContextValue = {
    user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook to use auth context
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
