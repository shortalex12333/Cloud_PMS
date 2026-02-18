import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const apiResponse = await fetch(
    `${RENDER_API_URL}/v1/handover/export/${params.id}/content`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
    }
  );

  if (!apiResponse.ok) {
    const error = await apiResponse.json().catch(() => ({ error: 'Request failed' }));
    return NextResponse.json(error, { status: apiResponse.status });
  }

  return NextResponse.json(await apiResponse.json());
}
