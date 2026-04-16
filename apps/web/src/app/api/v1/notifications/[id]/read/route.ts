/**
 * Mark single notification as read — PATCH /api/v1/notifications/[id]/read
 *
 * Forwards to the pipeline-core backend.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const auth = request.headers.get('Authorization');
  if (!auth) return NextResponse.json({ status: 'error', message: 'Unauthorized' }, { status: 401 });

  const { id } = await params;

  const res = await fetch(`${API_BASE}/v1/notifications/${id}/read`, {
    method: 'PATCH',
    headers: { Authorization: auth },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
