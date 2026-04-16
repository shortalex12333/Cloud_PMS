/**
 * Notifications proxy — GET /api/v1/notifications + PATCH /api/v1/notifications/mark-all-read
 *
 * Forwards to the pipeline-core backend.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function GET(request: NextRequest): Promise<NextResponse> {
  const auth = request.headers.get('Authorization');
  if (!auth) return NextResponse.json({ status: 'error', message: 'Unauthorized' }, { status: 401 });

  const params = request.nextUrl.searchParams.toString();
  const res = await fetch(`${API_BASE}/v1/notifications?${params}`, {
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function PATCH(request: NextRequest): Promise<NextResponse> {
  const auth = request.headers.get('Authorization');
  if (!auth) return NextResponse.json({ status: 'error', message: 'Unauthorized' }, { status: 401 });

  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${API_BASE}/v1/notifications/mark-all-read`, {
    method: 'PATCH',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
