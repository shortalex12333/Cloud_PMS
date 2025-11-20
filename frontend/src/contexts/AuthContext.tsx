'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { User, AuthState } from '@/types/auth'

interface AuthContextType extends AuthState {
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  refreshUser: () => Promise<void>
  isHOD: () => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  })

  // Fetch user profile from database
  const fetchUserProfile = async (authUserId: string): Promise<User | null> => {
    try {
      const { data, error } = await supabase
        .from('users')
        .select(`
          id,
          email,
          name,
          role,
          yacht_id,
          is_active,
          created_at,
          updated_at,
          yachts (
            name
          )
        `)
        .eq('id', authUserId)
        .single()

      if (error) {
        console.error('Error fetching user profile:', error)
        return null
      }

      return {
        ...data,
        yacht_name: data.yachts?.name,
      } as User
    } catch (err) {
      console.error('Error in fetchUserProfile:', err)
      return null
    }
  }

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()

        if (session?.user) {
          const profile = await fetchUserProfile(session.user.id)
          setState({
            user: profile,
            loading: false,
            error: null,
          })
        } else {
          setState({
            user: null,
            loading: false,
            error: null,
          })
        }
      } catch (error) {
        console.error('Error initializing auth:', error)
        setState({
          user: null,
          loading: false,
          error: 'Failed to initialize authentication',
        })
      }
    }

    initAuth()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (session?.user) {
          const profile = await fetchUserProfile(session.user.id)
          setState({
            user: profile,
            loading: false,
            error: null,
          })
        } else {
          setState({
            user: null,
            loading: false,
            error: null,
          })
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const signIn = async (email: string, password: string) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))

      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) throw error

      if (data.user) {
        const profile = await fetchUserProfile(data.user.id)
        setState({
          user: profile,
          loading: false,
          error: null,
        })
      }
    } catch (error: any) {
      setState({
        user: null,
        loading: false,
        error: error.message || 'Failed to sign in',
      })
      throw error
    }
  }

  const signOut = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      await supabase.auth.signOut()
      setState({
        user: null,
        loading: false,
        error: null,
      })
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error.message || 'Failed to sign out',
      }))
      throw error
    }
  }

  const refreshUser = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.user) {
        const profile = await fetchUserProfile(session.user.id)
        setState({
          user: profile,
          loading: false,
          error: null,
        })
      }
    } catch (error: any) {
      console.error('Error refreshing user:', error)
    }
  }

  const isHOD = () => {
    if (!state.user) return false
    return ['chief_engineer', 'hod', 'manager', 'captain'].includes(state.user.role)
  }

  return (
    <AuthContext.Provider
      value={{
        ...state,
        signIn,
        signOut,
        refreshUser,
        isHOD,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Convenience hook for getting user
export function useUser() {
  const { user } = useAuth()
  return user
}
