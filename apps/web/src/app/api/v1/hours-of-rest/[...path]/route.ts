/**
 * Hours of Rest — catch-all API proxy
 *
 * Proxies all GET/POST requests to:
 *   /api/v1/hours-of-rest/my-week
 *   /api/v1/hours-of-rest/department-status
 *   /api/v1/hours-of-rest/vessel-compliance
 *   /api/v1/hours-of-rest/month-status
 *   /api/v1/hours-of-rest/upsert
 *   /api/v1/hours-of-rest/signoffs/sign
 *   /api/v1/hours-of-rest/templates
 *   /api/v1/hours-of-rest/templates/apply
 *   /api/v1/hours-of-rest/notifications/unread
 *   /api/v1/hours-of-rest/warnings/*
 *
 * → ${RENDER_API_URL}/v1/hours-of-rest/...
 *
 * Timeout: 28s — enough for a cold Render service wake-up.
 */

import { NextRequest, NextResponse } from 'next/server';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
const PROXY_TIMEOUT_MS = 28_000;

async function proxy(request: NextRequest, method: 'GET' | 'POST', path: string[]): Promise<NextResponse> {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return NextResponse.json({ success: false, error: 'Unauthorized', code: 'UNAUTHORIZED' }, { status: 401 });
  }

  const segment = path.join('/');
  const searchString = new URL(request.url).search;
  const upstreamUrl = `${RENDER_API_URL}/v1/hours-of-rest/${segment}${searchString}`;

  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': authHeader },
    signal: AbortSignal.timeout(PROXY_TIMEOUT_MS),
  };

  if (method === 'POST') {
    try {
      options.body = JSON.stringify(await request.json());
    } catch {
      options.body = '{}';
    }
  }

  let resp: Response;
  try {
    resp = await fetch(upstreamUrl, options);
  } catch (err: unknown) {
    const isTimeout = err instanceof Error && (err.name === 'TimeoutError' || err.name === 'AbortError');
    console.error(`[HoR Proxy] fetch failed (${segment}):`, err);
    return NextResponse.json(
      { success: false, error: isTimeout ? 'Upstream timeout — service may be cold-starting, retry in a moment' : 'Upstream unreachable', code: isTimeout ? 'TIMEOUT' : 'UPSTREAM_ERROR' },
      { status: 503 },
    );
  }

  // Try JSON parse; if upstream returned HTML/empty on an error status, surface that status.
  let data: unknown;
  try {
    data = await resp.json();
  } catch {
    console.error(`[HoR Proxy] non-JSON upstream response (${segment}) status=${resp.status}`);
    return NextResponse.json(
      { success: false, error: 'Upstream returned a non-JSON response', code: 'BAD_UPSTREAM', status: resp.status },
      { status: resp.status >= 400 ? resp.status : 502 },
    );
  }

  return NextResponse.json(data, { status: resp.status });
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, 'GET', params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, 'POST', params.path);
}
