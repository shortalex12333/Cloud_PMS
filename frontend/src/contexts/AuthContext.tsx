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
export function isHOD(user: CelesteUser | null): boolean {
  if (!user) return false;
  return ['chief_engineer', 'captain', 'manager'].includes(user.role);
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CelesteUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch user profile from user_profiles and user_roles tables
  const fetchUserProfile = useCallback(async (authUser: User) => {
    try {
      // Query user profile
      const { data: profileData, error: profileError } = await supabase
        .from('user_profiles')
        .select('id, email, yacht_id, name')
        .eq('id', authUser.id)
        .single();

      if (profileError) {
        console.error('[AuthContext] Error fetching user profile:', profileError);
        return null;
      }

      if (!profileData) {
        console.warn('[AuthContext] No user profile found for:', authUser.id);
        return null;
      }

      // Query active role for this user
      const { data: roleData, error: roleError } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', authUser.id)
        .eq('yacht_id', profileData.yacht_id)
        .eq('is_active', true)
        .lte('valid_from', new Date().toISOString())
        .or('valid_until.is.null,valid_until.gt.' + new Date().toISOString())
        .order('assigned_at', { ascending: false })
        .limit(1)
        .single();

      if (roleError) {
        console.error('[AuthContext] Error fetching user role:', roleError);
        // Default to 'crew' if no role found
        console.warn('[AuthContext] No active role found, defaulting to crew');
      }

      const celesteUser: CelesteUser = {
        id: profileData.id,
        email: profileData.email,
        role: (roleData?.role as CelesteUser['role']) || 'crew',
        yachtId: profileData.yacht_id,
        displayName: profileData.name,
      };

      console.log('[AuthContext] User profile loaded:', {
        id: celesteUser.id,
        role: celesteUser.role,
        yachtId: celesteUser.yachtId,
      });

      return celesteUser;
    } catch (err) {
      console.error('[AuthContext] Exception fetching user profile:', err);
      return null;
    }
  }, []);

  // Initialize auth state
  useEffect(() => {
    console.log('[AuthContext] Initializing auth state...');

    // Check current session
    supabase.auth.getSession().then(({ data: { session } }) => {
      console.log('[AuthContext] Current session:', session ? 'exists' : 'none');
      if (session?.user) {
        fetchUserProfile(session.user).then((profile) => {
          setUser(profile);
          setLoading(false);
        });
      } else {
        setLoading(false);
      }
    });

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[AuthContext] Auth state changed:', event);

      if (event === 'SIGNED_IN' && session?.user) {
        const profile = await fetchUserProfile(session.user);
        setUser(profile);
      } else if (event === 'SIGNED_OUT') {
        setUser(null);
      } else if (event === 'TOKEN_REFRESHED' && session?.user) {
        // Optionally refresh user profile on token refresh
        const profile = await fetchUserProfile(session.user);
        setUser(profile);
      }
    });

    return () => {
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
