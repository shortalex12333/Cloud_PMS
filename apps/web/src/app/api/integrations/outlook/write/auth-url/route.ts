/**
 * Microsoft OAuth - Generate Authorization URL (WRITE App)
 *
 * Generates the Microsoft OAuth URL for WRITE permissions.
 * Uses WRITE app with Mail.Send, User.Read, offline_access.
 *
 * Per doctrine:
 * - WRITE app NEVER has Mail.ReadWrite
 * - WRITE app only has Mail.Send
 * - Completely separate from READ app
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  getServiceClient,
  generateOAuthState,
  buildAuthUrl,
  WRITE_APP,
} from '@/lib/email/oauth-utils';

// Force dynamic rendering - this route requires auth headers
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];

    // Verify JWT and get user_id
    const supabase = getServiceClient();
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    // Check if WRITE app is configured
    if (!WRITE_APP.clientSecret) {
      console.error('[Outlook Auth WRITE] AZURE_WRITE_CLIENT_SECRET not configured');
      return NextResponse.json(
        { error: 'Write integration not configured' },
        { status: 503 }
      );
    }

    // Generate state with user_id and purpose for CSRF protection
    const state = generateOAuthState(user.id, 'write');

    // Build Microsoft OAuth URL for WRITE app
    const authUrl = buildAuthUrl('write', state);

    console.log('[Outlook Auth WRITE] Generated auth URL for user:', user.id);
    console.log('[Outlook Auth WRITE] Using app:', WRITE_APP.appId);
    console.log('[Outlook Auth WRITE] Scopes:', WRITE_APP.scopes.join(', '));

    return NextResponse.json({
      url: authUrl,
      state: state,
      purpose: 'write',
      scopes: WRITE_APP.scopes,
    });

  } catch (error) {
    console.error('[Outlook Auth WRITE] Error generating auth URL:', error);
    return NextResponse.json(
      { error: 'Failed to generate auth URL' },
      { status: 500 }
    );
  }
}
