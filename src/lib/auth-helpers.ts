import { supabase } from './supabase-client'

/**
 * Ensures we have a fresh JWT token before making API calls.
 * Automatically refreshes if token expires within 5 minutes (300 seconds).
 *
 * This prevents "JWT token expired" errors caused by:
 * - Clock skew between client and server
 * - Network latency to Render.com backend
 * - Long user sessions without activity
 *
 * @returns Fresh access token
 * @throws Error if not authenticated or refresh fails
 */
export async function ensureFreshToken(): Promise<string> {
  const { data: { session }, error } = await supabase.auth.getSession()

  if (error || !session) {
    throw new Error('Not authenticated')
  }

  // Check if token expires in less than 5 minutes (300 seconds)
  const expiresAt = session.expires_at || 0
  const now = Math.floor(Date.now() / 1000)
  const timeUntilExpiry = expiresAt - now

  if (timeUntilExpiry < 300) {
    console.log('🔄 Token expiring soon, refreshing...')

    const { data, error: refreshError } = await supabase.auth.refreshSession()

    if (refreshError || !data.session) {
      throw new Error('Failed to refresh token')
    }

    console.log('✅ Token refreshed successfully')
    return data.session.access_token
  }

  return session.access_token
}

/**
 * Session info structure returned by getCurrentSession
 */
export interface SessionInfo {
  token: string
  userId: string
  yachtId: string | null
}

/**
 * Get current session with user and yacht info.
 * Use this alongside ensureFreshToken for API calls.
 *
 * @returns Session info including token, userId, and yachtId
 * @throws Error if not authenticated
 */
export async function getCurrentSession(): Promise<SessionInfo> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('Not authenticated')
  }

  return {
    token: session.access_token,
    userId: session.user.id,
    yachtId: session.user.user_metadata?.yacht_id || null
  }
}

/**
 * Check if user is currently authenticated
 * @returns true if user has a valid session
 */
export async function isAuthenticated(): Promise<boolean> {
  const { data: { session } } = await supabase.auth.getSession()
  return !!session
}

/**
 * Sign out the current user
 */
export async function signOut(): Promise<void> {
  const { error } = await supabase.auth.signOut()
  if (error) {
    throw new Error('Failed to sign out')
  }
}
