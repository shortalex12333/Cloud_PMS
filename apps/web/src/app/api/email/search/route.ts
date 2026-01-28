import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Force dynamic rendering - no static generation
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * POST /api/email/search
 *
 * Proxies search requests to Python backend /email/search endpoint.
 * The Python backend handles:
 * - Query parsing with operator support (from:, to:, has:attachment, etc.)
 * - Embedding generation with caching
 * - Hybrid vector + entity search
 * - Telemetry and logging
 *
 * Frontend sends: { query, limit?, yacht_id? }
 * Backend expects: GET /email/search?q=query&limit=20
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query, limit = 20 } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      );
    }

    // Get auth token from request or session
    const authHeader = request.headers.get('Authorization');

    // If no auth header provided, try to get from Supabase session cookie
    let token = authHeader?.replace('Bearer ', '');

    if (!token) {
      // Fall back to service role for server-side calls (e.g., from SpotlightSearch)
      // The Python backend will use the JWT to get yacht_id
      const supabase = createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
          auth: {
            autoRefreshToken: false,
            persistSession: false,
          },
        }
      );

      // Try to get session from cookie
      const cookieHeader = request.headers.get('cookie') || '';
      const sessionCookie = cookieHeader.split(';').find(c =>
        c.trim().startsWith('sb-') && c.includes('auth-token')
      );

      if (sessionCookie) {
        // Extract token from cookie
        const tokenMatch = sessionCookie.match(/base64-([^,]+)/);
        if (tokenMatch) {
          try {
            const decoded = Buffer.from(tokenMatch[1], 'base64').toString('utf-8');
            const parsed = JSON.parse(decoded);
            token = parsed.access_token;
          } catch {
            // Ignore parse errors
          }
        }
      }
    }

    if (!token) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Build query params for Python backend
    const params = new URLSearchParams({
      q: query,
      limit: String(limit),
    });

    // Call Python backend
    const response = await fetch(`${RENDER_API_URL}/email/search?${params}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      console.error('[api/email/search] Backend error:', response.status, error);
      return NextResponse.json(
        { error: error.detail || error.message || 'Search failed' },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Transform response to match frontend expectations
    // Python returns { results: [...], telemetry: {...} }
    return NextResponse.json({
      results: data.results || [],
      query,
      telemetry: data.telemetry,
    });
  } catch (error) {
    console.error('[api/email/search] Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
