/**
 * Hours of Rest — catch-all API proxy
 *
 * Proxies all GET/POST requests to:
 *   /api/v1/hours-of-rest/my-week
 *   /api/v1/hours-of-rest/department-status
 *   /api/v1/hours-of-rest/vessel-compliance
 *   /api/v1/hours-of-rest/upsert
 *   /api/v1/hours-of-rest/signoffs/sign
 *   /api/v1/hours-of-rest/templates
 *   /api/v1/hours-of-rest/templates/apply
 *
 * → ${RENDER_API_URL}/v1/hours-of-rest/...
 */

import { NextRequest, NextResponse } from 'next/server';

const RENDER_API_URL = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

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
  };

  if (method === 'POST') {
    try {
      options.body = JSON.stringify(await request.json());
    } catch {
      options.body = '{}';
    }
  }

  try {
    const resp = await fetch(upstreamUrl, options);
    const data = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch (err) {
    console.error('[HoR Proxy]', err);
    return NextResponse.json({ success: false, error: 'Proxy error' }, { status: 502 });
  }
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, 'GET', params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, 'POST', params.path);
}
