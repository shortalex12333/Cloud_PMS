import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Domain-based routing middleware for auth/app split
 *
 * Domains:
 * - auth.celeste7.ai: Login, signup, password reset (public)
 * - app.celeste7.ai: Main application (requires authentication)
 *
 * This middleware enforces:
 * 1. Auth domain only serves auth pages
 * 2. App domain redirects auth pages to auth domain
 * 3. App pages require authentication (handled by withAuth HOC)
 */

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const pathname = request.nextUrl.pathname;

  console.log('[middleware] Request:', { hostname, pathname });

  // Auth domain (auth.celeste7.ai)
  if (hostname.includes('auth.celeste7.ai')) {
    // Allow auth-related pages
    const authPages = ['/', '/login', '/signup', '/reset-password', '/verify-email'];

    if (authPages.includes(pathname) || pathname.startsWith('/api/')) {
      console.log('[middleware] Auth domain - allowing auth page:', pathname);
      return NextResponse.next();
    }

    // Redirect app pages to app domain
    console.log('[middleware] Auth domain - redirecting to app domain:', pathname);
    const url = new URL(pathname, 'https://app.celeste7.ai');
    url.search = request.nextUrl.search; // Preserve query params
    return NextResponse.redirect(url);
  }

  // App domain (app.celeste7.ai)
  if (hostname.includes('app.celeste7.ai')) {
    // Auth pages should go to auth domain
    const authPages = ['/login', '/signup', '/reset-password', '/verify-email'];

    if (authPages.includes(pathname)) {
      console.log('[middleware] App domain - redirecting auth page to auth domain:', pathname);
      const url = new URL(pathname, 'https://auth.celeste7.ai');
      url.search = request.nextUrl.search; // Preserve query params
      return NextResponse.redirect(url);
    }

    // Allow app pages and API routes
    console.log('[middleware] App domain - allowing app page:', pathname);
    return NextResponse.next();
  }

  // Localhost or other domains - allow everything for development
  console.log('[middleware] Localhost/other - allowing:', pathname);
  return NextResponse.next();
}

export const config = {
  /*
   * Match all request paths except:
   * - _next/static (static files)
   * - _next/image (image optimization)
   * - favicon.ico (favicon file)
   * - public files (images, etc)
   */
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
