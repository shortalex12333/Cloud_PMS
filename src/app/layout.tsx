'use client'

import { useEffect } from 'react'
import { supabase } from '@/lib/supabase-client'

/**
 * Root layout component with Supabase auth state listener.
 *
 * This sets up global auth event handling:
 * - TOKEN_REFRESHED: Logs when Supabase auto-refreshes the token
 * - SIGNED_OUT: Logs when user signs out
 *
 * Note: Supabase's built-in auto-refresh only works for calls made through
 * the Supabase client. For direct fetch() calls to external APIs like
 * https://api.celeste7.ai/search, use ensureFreshToken() from auth-helpers.ts
 */
export default function RootLayout({
  children
}: {
  children: React.ReactNode
}) {
  useEffect(() => {
    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        switch (event) {
          case 'TOKEN_REFRESHED':
            console.log('✅ Token auto-refreshed by Supabase')
            break
          case 'SIGNED_OUT':
            console.log('🚪 User signed out')
            // Optionally redirect to login page
            // window.location.href = '/login'
            break
          case 'SIGNED_IN':
            console.log('🔐 User signed in')
            break
          case 'USER_UPDATED':
            console.log('👤 User profile updated')
            break
          case 'PASSWORD_RECOVERY':
            console.log('🔑 Password recovery initiated')
            break
          default:
            // Other events: INITIAL_SESSION, MFA_CHALLENGE_VERIFIED
            break
        }
      }
    )

    // Cleanup subscription on unmount
    return () => {
      subscription.unsubscribe()
    }
  }, [])

  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
