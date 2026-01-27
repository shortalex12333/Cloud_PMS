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

// Force dynamic rendering - this route requires auth headers
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  const requestId = Math.random().toString(36).substring(7);
  console.log(`[Outlook Auth READ][${requestId}] Request received`);
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
    console.log(`[Outlook Auth READ][${requestId}] Auth header present: ${!!authHeader}, length: ${authHeader?.length || 0}`);

    if (!authHeader) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: No Authorization header`);
      return NextResponse.json(
        { error: 'No authorization header', code: 'missing_auth_header', requestId, hint: 'Ensure frontend sends Authorization: Bearer <token>' },
        { status: 401 }
      );
    }
    if (!authHeader.startsWith('Bearer ')) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: Invalid format - starts with: ${authHeader.substring(0, 10)}`);
      return NextResponse.json(
        { error: 'Invalid authorization header format', code: 'invalid_auth_format', requestId, hint: 'Header must start with "Bearer "' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];
    console.log(`[Outlook Auth READ][${requestId}] Token extracted, length: ${token?.length || 0}`);

    if (!token || token.length < 10) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: Token empty or too short`);
      return NextResponse.json(
        { error: 'Empty or invalid token', code: 'empty_token', requestId, hint: 'Token is missing or malformed' },
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
    console.log(`[Outlook Auth READ][${requestId}] Validating token against Supabase: ${supabaseUrl.substring(0, 30)}...`);
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: Token validation - ${error?.message || 'no user returned'}`);
      return NextResponse.json(
        { error: 'Token validation failed', code: 'token_invalid', requestId, details: error?.message, hint: 'JWT may be expired or signed by different Supabase project' },
        { status: 401 }
      );
    }
    console.log(`[Outlook Auth READ][${requestId}] Token valid for user: ${user.id}`);

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
