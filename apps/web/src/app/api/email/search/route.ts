import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering - no static generation
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// Standard cache control headers for auth-required endpoints
const NO_CACHE_HEADERS = {
  'Cache-Control': 'no-store, no-cache, must-revalidate',
};

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
        { status: 400, headers: NO_CACHE_HEADERS }
      );
    }

    // Get auth token from Authorization header (required)
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Authentication required', code: 'missing_bearer' },
        { status: 401, headers: NO_CACHE_HEADERS }
      );
    }

    const token = authHeader.split(' ')[1];
    if (!token || token.length < 10) {
      return NextResponse.json(
        { error: 'Invalid token', code: 'invalid_token' },
        { status: 401, headers: NO_CACHE_HEADERS }
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
        { status: response.status, headers: NO_CACHE_HEADERS }
      );
    }

    const data = await response.json();

    // Transform response to match frontend expectations
    // Python returns { results: [...], telemetry: {...} }
    return NextResponse.json({
      results: data.results || [],
      query,
      telemetry: data.telemetry,
    }, { headers: NO_CACHE_HEADERS });
  } catch (error) {
    console.error('[api/email/search] Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500, headers: NO_CACHE_HEADERS }
    );
  }
}
