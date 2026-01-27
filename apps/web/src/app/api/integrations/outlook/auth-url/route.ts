/**
 * Microsoft OAuth - Generate Authorization URL (READ App)
 *
 * Generates the Microsoft OAuth URL for READ permissions.
 * Uses READ app with Mail.Read, User.Read, MailboxSettings.Read, offline_access.
 *
 * Per doctrine: READ app NEVER has write permissions.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import {
  generateOAuthState,
  buildAuthUrl,
  READ_APP,
} from '@/lib/email/oauth-utils';

export async function GET(request: NextRequest) {
  try {
    // Check required env vars
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !anonKey) {
      console.error('[Outlook Auth READ] Missing env vars:', {
        hasUrl: !!supabaseUrl,
        hasAnonKey: !!anonKey,
      });
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      console.error('[Outlook Auth READ] No Authorization header provided');
      return NextResponse.json(
        { error: 'No authorization header', code: 'missing_auth_header' },
        { status: 401 }
      );
    }
    if (!authHeader.startsWith('Bearer ')) {
      console.error('[Outlook Auth READ] Invalid Authorization header format:', authHeader.substring(0, 20));
      return NextResponse.json(
        { error: 'Invalid authorization header format', code: 'invalid_auth_format' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];
    if (!token || token.length < 10) {
      console.error('[Outlook Auth READ] Token is empty or too short');
      return NextResponse.json(
        { error: 'Empty or invalid token', code: 'empty_token' },
        { status: 401 }
      );
    }

    // Create Supabase client with the user's JWT to verify it
    // This uses the anon key but will only succeed if the JWT is valid
    const supabase = createClient(supabaseUrl, anonKey, {
      global: {
        headers: { Authorization: `Bearer ${token}` }
      }
    });

    // Verify JWT by calling getUser - this validates the token
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      console.error('[Outlook Auth READ] Auth validation failed:', error?.message);
      return NextResponse.json(
        { error: 'Token validation failed', code: 'token_invalid', details: error?.message },
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
