import { supabase } from './supabase-client'

/**
 * Ensures we have a fresh JWT token before making API calls.
 * Automatically refreshes if token expires within 5 minutes (300 seconds).
 *
 * @returns Fresh access token
 * @throws Error if not authenticated or refresh fails
 */
export async function ensureFreshToken(): Promise<string> {
  const { data: { session }, error } = await supabase.auth.getSession()

  if (error || !session) {
    throw new Error('Not authenticated')
  }

  const expiresAt = session.expires_at || 0
  const now = Math.floor(Date.now() / 1000)
  const timeUntilExpiry = expiresAt - now

  if (timeUntilExpiry < 300) {
    console.log('Token expiring soon, refreshing...')

    const { data, error: refreshError } = await supabase.auth.refreshSession()

    if (refreshError || !data.session) {
      throw new Error('Failed to refresh token')
    }

    console.log('Token refreshed successfully')
    return data.session.access_token
  }

  return session.access_token
}

/**
 * Session info structure
 */
export interface SessionInfo {
  token: string
  userId: string
  yachtId: string | null
}

/**
 * Auth context for API calls
 */
export interface AuthContext {
  user_id: string
  yacht_id: string
  yacht_signature: string
}

/**
 * Get yacht_id from user session.
 * Checks multiple locations where yacht_id might be stored.
 */
async function getYachtId(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    return null
  }

  // Check user_metadata first (set during signup)
  const userMetaYachtId = session.user.user_metadata?.yacht_id

  // Check app_metadata (set by admin/backend)
  const appMetaYachtId = session.user.app_metadata?.yacht_id

  // Return first available yacht_id
  return userMetaYachtId || appMetaYachtId || null
}

/**
 * Calculate yacht signature using HMAC-SHA256.
 * This provides verification that the request comes from an authorized client.
 *
 * @param userId - User's UUID
 * @param yachtId - Yacht's UUID
 * @param timestamp - Unix timestamp in seconds
 * @returns Base64-encoded HMAC signature
 */
export async function calculateYachtSignature(
  userId: string,
  yachtId: string,
  timestamp: number
): Promise<string> {
  // Signature secret from environment
  const secret = process.env.NEXT_PUBLIC_YACHT_SIGNATURE_SECRET

  if (!secret) {
    // In development or if secret not configured, return empty string
    // Backend should handle this gracefully
    console.warn('NEXT_PUBLIC_YACHT_SIGNATURE_SECRET not configured')
    return ''
  }

  // Create message: userId|yachtId|timestamp
  const message = `${userId}|${yachtId}|${timestamp}`

  // Convert secret and message to ArrayBuffer
  const encoder = new TextEncoder()
  const keyData = encoder.encode(secret)
  const messageData = encoder.encode(message)

  // Import secret as HMAC key
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )

  // Sign the message
  const signature = await crypto.subtle.sign('HMAC', cryptoKey, messageData)

  // Convert to base64
  const signatureArray = new Uint8Array(signature)
  let binaryString = ''
  for (let i = 0; i < signatureArray.length; i++) {
    binaryString += String.fromCharCode(signatureArray[i])
  }
  const signatureBase64 = btoa(binaryString)

  return signatureBase64
}

/**
 * Get full auth context for API calls.
 * Includes user_id, yacht_id, and calculated yacht_signature.
 *
 * @throws Error if not authenticated or yacht_id not available
 */
export async function getAuthContext(): Promise<AuthContext> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('Not authenticated')
  }

  const userId = session.user.id
  const yachtId = await getYachtId()

  if (!yachtId) {
    throw new Error('No yacht_id found. User must be assigned to a yacht.')
  }

  const timestamp = Math.floor(Date.now() / 1000)
  const signature = await calculateYachtSignature(userId, yachtId, timestamp)

  return {
    user_id: userId,
    yacht_id: yachtId,
    yacht_signature: signature
  }
}

/**
 * Get current session info.
 * Use this for basic session data without signature calculation.
 */
export async function getCurrentSession(): Promise<SessionInfo> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('Not authenticated')
  }

  return {
    token: session.access_token,
    userId: session.user.id,
    yachtId: await getYachtId()
  }
}

/**
 * Check if user is currently authenticated
 */
export async function isAuthenticated(): Promise<boolean> {
  const { data: { session } } = await supabase.auth.getSession()
  return !!session
}

/**
 * Check if user has a yacht assigned
 */
export async function hasYachtAssigned(): Promise<boolean> {
  const yachtId = await getYachtId()
  return yachtId !== null
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

/**
 * Update user's yacht_id in metadata.
 * Call this during onboarding or when assigning user to a yacht.
 */
export async function setUserYachtId(yachtId: string): Promise<void> {
  const { error } = await supabase.auth.updateUser({
    data: { yacht_id: yachtId }
  })

  if (error) {
    throw new Error(`Failed to set yacht_id: ${error.message}`)
  }
}
