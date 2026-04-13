/**
 * Notifications stub — GET /api/v1/notifications
 *
 * Returns an empty list for all notification types until the backend
 * notifications endpoint is implemented (deferred HoR phase).
 *
 * Supported query params (forwarded to backend when implemented):
 *   ?type=hor_unsigned | hor_days_missing | hor_hod_pending | hor_captain_pending
 */

import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest): Promise<NextResponse> {
  return NextResponse.json({ status: 'success', data: [] });
}
