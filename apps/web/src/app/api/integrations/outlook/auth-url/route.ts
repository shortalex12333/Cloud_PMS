/**
 * Microsoft OAuth - Generate Authorization URL (READ App)
 *
 * Generates the Microsoft OAuth URL for READ permissions.
 * Uses READ app with Mail.Read, User.Read, MailboxSettings.Read, offline_access.
 *
 * Per doctrine: READ app NEVER has write permissions.
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  getServiceClient,
  generateOAuthState,
  buildAuthUrl,
  READ_APP,
} from '@/lib/email/oauth-utils';

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

    // Generate state with user_id and purpose for CSRF protection
    const state = generateOAuthState(user.id, 'read');

    // Build Microsoft OAuth URL for READ app
    const authUrl = buildAuthUrl('read', state);

    console.log('[Outlook Auth READ] Generated auth URL for user:', user.id);
    console.log('[Outlook Auth READ] Using app:', READ_APP.appId);
    console.log('[Outlook Auth READ] Scopes:', READ_APP.scopes.join(', '));

    return NextResponse.json({
      url: authUrl,
      state: state,
      purpose: 'read',
      scopes: READ_APP.scopes,
    });

  } catch (error) {
    console.error('[Outlook Auth READ] Error generating auth URL:', error);
    return NextResponse.json(
      { error: 'Failed to generate auth URL' },
      { status: 500 }
    );
  }
}
