/**
 * Notifications proxy — GET /api/v1/notifications
 *
 * Forwards to the pipeline-core backend.
 * Non-critical path: returns empty list on any upstream error rather than 500.
 *
 * PATCH /api/v1/notifications/mark-all-read is handled by mark-all-read/route.ts.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
const EMPTY_RESPONSE = { status: 'success', unread_count: 0, notifications: [] };

export async function GET(request: NextRequest): Promise<NextResponse> {
  const auth = request.headers.get('Authorization');
  if (!auth) return NextResponse.json({ status: 'error', message: 'Unauthorized' }, { status: 401 });

  const params = request.nextUrl.searchParams.toString();
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/v1/notifications?${params}`, {
      headers: { Authorization: auth, 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return NextResponse.json(EMPTY_RESPONSE, { status: 200 });
  }
  const data = await res.json().catch(() => EMPTY_RESPONSE);
  return NextResponse.json(data, { status: res.status });
}
