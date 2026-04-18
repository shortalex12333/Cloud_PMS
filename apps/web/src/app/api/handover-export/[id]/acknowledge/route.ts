import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const RENDER_API_URL =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://pipeline-core.int.celeste7.ai';

/**
 * POST /api/handover-export/[id]/acknowledge
 *
 * Proxies incoming-crew acknowledgement to the Render backend at
 * /v1/actions/handover/{id}/sign/incoming.
 *
 * Backend role gate: any authenticated user on the yacht (enforced by
 * backend `get_authenticated_user` dependency).
 *
 * Body (JSON):
 *   { acknowledge_critical: boolean, note?: string, method?: string }
 *
 * Backend route declares these as scalar FastAPI params — forwarded here as
 * querystring values. Pass-through: Authorization header, x-yacht-id header.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as {
    acknowledge_critical?: boolean;
    note?: string;
    method?: string;
  };

  // Build querystring — FastAPI signature is scalar params, not body model.
  const qs = new URLSearchParams();
  qs.set('acknowledge_critical', String(Boolean(body.acknowledge_critical)));
  if (body.note !== undefined && body.note !== null) {
    qs.set('note', String(body.note));
  }
  if (body.method) {
    qs.set('method', String(body.method));
  }

  const yachtHeader = request.headers.get('x-yacht-id');
  const forwardedHeaders: Record<string, string> = {
    Authorization: authHeader,
    'Content-Type': 'application/json',
  };
  if (yachtHeader) {
    forwardedHeaders['x-yacht-id'] = yachtHeader;
  }

  const apiResponse = await fetch(
    `${RENDER_API_URL}/v1/actions/handover/${params.id}/sign/incoming?${qs.toString()}`,
    {
      method: 'POST',
      headers: forwardedHeaders,
    }
  );

  if (!apiResponse.ok) {
    const error = await apiResponse
      .json()
      .catch(() => ({ error: 'Request failed' }));
    return NextResponse.json(error, { status: apiResponse.status });
  }

  return NextResponse.json(await apiResponse.json());
}
