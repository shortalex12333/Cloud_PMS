/**
 * Supabase client utilities
 */

import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

/**
 * Get current user session
 */
export async function getSession() {
  const { data: { session }, error } = await supabase.auth.getSession()

  if (error) {
    console.error('Error getting session:', error)
    return null
  }

  return session
}

/**
 * Get user role from database
 */
export async function getUserRole(userId: string): Promise<string | null> {
  const { data, error } = await supabase
    .from('users')
    .select('role')
    .eq('id', userId)
    .single()

  if (error) {
    console.error('Error getting user role:', error)
    return null
  }

  return data?.role || null
}

/**
 * Check if user has required role
 */
export async function hasRole(userId: string, requiredRoles: string[]): Promise<boolean> {
  const role = await getUserRole(userId)

  if (!role) return false

  // Allow wildcard
  if (requiredRoles.includes('*')) return true

  return requiredRoles.includes(role)
}

/**
 * Get yacht ID for current user
 */
export async function getUserYachtId(userId: string): Promise<string | null> {
  const { data, error } = await supabase
    .from('users')
    .select('yacht_id')
    .eq('id', userId)
    .single()

  if (error) {
    console.error('Error getting yacht ID:', error)
    return null
  }

  return data?.yacht_id || null
}
