import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Domain-based routing middleware - CONSOLIDATED AUTH
 *
 * Architecture (2026-01-13):
 * - app.celeste7.ai: All app functionality INCLUDING auth pages (/login, /signup, etc.)
 * - auth.celeste7.ai: DEPRECATED - 308 redirects to app.celeste7.ai/login
 *
 * This middleware enforces:
 * 1. auth.celeste7.ai redirects to app.celeste7.ai (backwards compatibility)
 * 2. All pages served from app.celeste7.ai (no cross-domain auth)
 * 3. CORS headers for API requests from allowed origins
 */

// Allowed origins for CORS (same-origin is primary now)
const ALLOWED_ORIGINS = [
  'https://app.celeste7.ai',
  'https://auth.celeste7.ai',  // For backwards compatibility during transition
  'http://localhost:3000',
];

function addCorsHeaders(response: NextResponse, origin: string | null) {
  // Only add CORS headers for allowed origins
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    response.headers.set('Access-Control-Allow-Origin', origin);
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, RSC, Next-Router-State-Tree, Next-Router-Prefetch, Next-Url');
    response.headers.set('Access-Control-Allow-Credentials', 'true');
    response.headers.set('Access-Control-Max-Age', '86400');
  }
  return response;
}

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || '';
  const pathname = request.nextUrl.pathname;
  const origin = request.headers.get('origin');

  // Handle CORS preflight (OPTIONS) requests
  if (request.method === 'OPTIONS') {
    const response = new NextResponse(null, { status: 200 });
    return addCorsHeaders(response, origin);
  }

  // DEPRECATED: auth.celeste7.ai → 308 redirect to app.celeste7.ai
  // This provides backwards compatibility for bookmarks/links
  if (hostname.includes('auth.celeste7.ai')) {
    const authPages = ['/', '/login', '/signup', '/reset-password', '/verify-email'];

    // Map auth pages to app domain
    let targetPath = pathname;
    if (pathname === '/') {
      targetPath = '/login';
    }

    const url = new URL(targetPath, 'https://app.celeste7.ai');
    url.search = request.nextUrl.search; // Preserve query params

    // 308 Permanent Redirect (preserves method)
    return NextResponse.redirect(url, 308);
  }

  // App domain (app.celeste7.ai) - serves everything
  if (hostname.includes('app.celeste7.ai')) {
    // DEPRECATED: /app → / (backwards compatibility)
    // Single surface moved from /app to / (root) per cd952ef deployment
    if (pathname === '/app') {
      const url = new URL('/', request.url);
      url.search = request.nextUrl.search; // Preserve query params
      return addCorsHeaders(NextResponse.redirect(url, 308), origin);
    }

    const response = NextResponse.next();
    return addCorsHeaders(response, origin);
  }

  // Localhost or other domains - allow everything for development
  // Apply same /app → / redirect for consistency
  if (pathname === '/app') {
    const url = new URL('/', request.url);
    url.search = request.nextUrl.search;
    return addCorsHeaders(NextResponse.redirect(url, 308), origin);
  }

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
