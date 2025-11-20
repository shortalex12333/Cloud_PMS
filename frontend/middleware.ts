/**
 * CelesteOS Frontend Middleware
 * Handles protected routes based on user role
 */

import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'

// Define role-based access control
const ROLE_ACCESS = {
  '/dashboard': ['HOD', 'Engineer', 'Chief Engineer', 'ETO'],
  '/search': ['*'], // All authenticated users
} as const

export async function middleware(request: NextRequest) {
  const res = NextResponse.next()
  const pathname = request.nextUrl.pathname

  // Create Supabase client
  const supabase = createMiddlewareClient({ req: request, res })

  // Get session
  const {
    data: { session },
  } = await supabase.auth.getSession()

  // If no session, redirect to login
  if (!session) {
    const redirectUrl = request.nextUrl.clone()
    redirectUrl.pathname = '/login'
    redirectUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(redirectUrl)
  }

  // Get user role from database
  const { data: userData, error } = await supabase
    .from('users')
    .select('role')
    .eq('id', session.user.id)
    .single()

  if (error || !userData) {
    // If can't get role, redirect to unauthorized
    const redirectUrl = request.nextUrl.clone()
    redirectUrl.pathname = '/unauthorized'
    return NextResponse.redirect(redirectUrl)
  }

  const userRole = userData.role

  // Check if route requires specific role
  for (const [route, allowedRoles] of Object.entries(ROLE_ACCESS)) {
    if (pathname.startsWith(route)) {
      // If route allows all authenticated users
      if (allowedRoles.includes('*')) {
        return res
      }

      // Check if user's role is allowed
      if (!allowedRoles.includes(userRole)) {
        // Redirect to search page (default allowed page)
        const redirectUrl = request.nextUrl.clone()
        redirectUrl.pathname = '/search'
        redirectUrl.searchParams.set('error', 'insufficient_permissions')
        return NextResponse.redirect(redirectUrl)
      }
    }
  }

  return res
}

// Configure which routes to run middleware on
export const config = {
  matcher: ['/dashboard/:path*', '/search/:path*'],
}
