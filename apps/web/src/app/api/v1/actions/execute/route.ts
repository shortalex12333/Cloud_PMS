/**
 * Action Router - Proxy to Render Backend
 *
 * Endpoint: POST /v1/actions/execute
 *
 * This route proxies action requests to the Render backend (pipeline-core)
 * which handles all tenant database operations.
 *
 * Architecture:
 * - Vercel: UI, Master DB auth
 * - Render: Tenant DB operations, action execution
 */

import { NextRequest, NextResponse } from 'next/server';

const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

interface ActionResponse {
  success: boolean;
  data?: any;
  message?: string;
  error?: string;
  code?: string;
}

export async function POST(request: NextRequest): Promise<NextResponse<ActionResponse>> {
  try {
    // Get the request body
    const body = await request.json();

    // Extract JWT from Authorization header
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { success: false, error: 'Missing or invalid Authorization header', code: 'UNAUTHORIZED' },
        { status: 401 }
      );
    }

    // Log the proxy request
    console.log('[Action Router] Proxying to Render:', {
      action: body.action,
      renderUrl: `${RENDER_API_URL}/v1/actions/execute`,
    });

    // Proxy to Render backend
    const renderResponse = await fetch(`${RENDER_API_URL}/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
      body: JSON.stringify(body),
    });

    // Get response from Render
    const responseData = await renderResponse.json();

    // Log the response
    console.log('[Action Router] Render response:', {
      status: renderResponse.status,
      success: responseData.success,
      error: responseData.error,
    });

    // Return the response with the same status code
    return NextResponse.json(responseData, { status: renderResponse.status });

  } catch (error) {
    console.error('[Action Router] Proxy error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to proxy request to backend',
        code: 'PROXY_ERROR'
      },
      { status: 500 }
    );
  }
}
