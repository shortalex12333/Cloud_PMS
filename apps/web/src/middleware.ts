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
 * 4. CORS headers for cross-domain requests
 */

// Allowed origins for CORS
const ALLOWED_ORIGINS = [
  'https://app.celeste7.ai',
  'https://auth.celeste7.ai',
  'http://localhost:3000',
];

function addCorsHeaders(response: NextResponse, origin: string | null) {
  // Only add CORS headers for allowed origins
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    response.headers.set('Access-Control-Allow-Origin', origin);
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, RSC, Next-Router-State-Tree, Next-Router-Prefetch');
    response.headers.set('Access-Control-Allow-Credentials', 'true');
    response.headers.set('Access-Control-Max-Age', '86400');
  }
  return response;
}

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const pathname = request.nextUrl.pathname;
  const origin = request.headers.get('origin');

  console.log('[middleware] Request:', { hostname, pathname, origin });

  // Handle CORS preflight (OPTIONS) requests
  if (request.method === 'OPTIONS') {
    console.log('[middleware] CORS preflight for:', pathname);
    const response = new NextResponse(null, { status: 200 });
    return addCorsHeaders(response, origin);
  }

  // Auth domain (auth.celeste7.ai)
  if (hostname.includes('auth.celeste7.ai')) {
    // Allow auth-related pages
    const authPages = ['/', '/login', '/signup', '/reset-password', '/verify-email'];

    if (authPages.includes(pathname) || pathname.startsWith('/api/')) {
      console.log('[middleware] Auth domain - allowing auth page:', pathname);
      const response = NextResponse.next();
      return addCorsHeaders(response, origin);
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
    const response = NextResponse.next();
    return addCorsHeaders(response, origin);
  }

  // Localhost or other domains - allow everything for development
  console.log('[middleware] Localhost/other - allowing:', pathname);
  const response = NextResponse.next();
  return addCorsHeaders(response, origin);
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
