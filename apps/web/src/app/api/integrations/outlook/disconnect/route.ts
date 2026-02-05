/**
 * Microsoft OAuth - Disconnect Account
 *
 * Forwards disconnect request to Render backend.
 * This keeps all secrets (Supabase service keys) in Render only.
 *
 * Per doctrine:
 * - Soft delete only - set is_revoked=true
 * - Historical email data preserved
 * - All DB operations handled by Render backend
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

// Render backend URL
const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function POST(request: NextRequest) {
  try {
    // Get JWT from Authorization header - pass through to Render
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
        { status: 401 }
      );
    }

    console.log('[Outlook Disconnect] Forwarding to Render backend');

    // Forward request to Render backend
    let renderResponse: Response;
    try {
      renderResponse = await fetch(`${RENDER_API_URL}/auth/outlook/disconnect`, {
        method: 'POST',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
        },
      });
    } catch (fetchError) {
      console.error('[Outlook Disconnect] Network error calling Render:', fetchError);
      return NextResponse.json(
        { success: false, error: 'Backend unreachable' },
        { status: 503 }
      );
    }

    // Parse response
    let result: { success: boolean; message?: string; error?: string; error_code?: string };
    try {
      result = await renderResponse.json();
    } catch {
      console.error('[Outlook Disconnect] Invalid response from Render');
      return NextResponse.json(
        { success: false, error: 'Invalid backend response' },
        { status: 502 }
      );
    }

    console.log('[Outlook Disconnect] Render response:', {
      status: renderResponse.status,
      success: result.success,
      error: result.error,
    });

    // Return Render's response
    if (result.success) {
      return NextResponse.json({
        success: true,
        message: result.message || 'Disconnected successfully. Email history preserved.',
      });
    } else {
      return NextResponse.json(
        {
          success: false,
          error: result.error || 'Disconnect failed',
          error_code: result.error_code,
        },
        { status: renderResponse.status >= 400 ? renderResponse.status : 500 }
      );
    }

  } catch (error) {
    console.error('[Outlook Disconnect] Unexpected error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
