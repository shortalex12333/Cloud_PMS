/**
 * PATCH /api/v1/notifications/mark-all-read
 *
 * Proxies to backend PATCH /v1/notifications/mark-all-read.
 * Marks all unread notifications as read for the current user+yacht.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function PATCH(request: NextRequest): Promise<NextResponse> {
  const auth = request.headers.get('Authorization');
  if (!auth) return NextResponse.json({ status: 'error', message: 'Unauthorized' }, { status: 401 });

  const params = request.nextUrl.searchParams.toString();
  const url = params
    ? `${API_BASE}/v1/notifications/mark-all-read?${params}`
    : `${API_BASE}/v1/notifications/mark-all-read`;

  const res = await fetch(url, {
    method: 'PATCH',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
  });

  const data = await res.json().catch(() => ({ status: 'success' }));
  return NextResponse.json(data, { status: res.status });
}
