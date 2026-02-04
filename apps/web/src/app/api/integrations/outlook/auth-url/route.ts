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

// Build version marker for cache verification
console.log('[Outlook Auth URL] Module loaded - build 2026-01-27-v2');

const CACHE_HEADERS = { 'Cache-Control': 'no-store, no-cache, must-revalidate' };

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
        { error: 'Server configuration error', code: 'config_error', requestId },
        { status: 500, headers: CACHE_HEADERS }
      );
    }

    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    console.log(`[Outlook Auth READ][${requestId}] Auth header present: ${!!authHeader}, length: ${authHeader?.length || 0}`);

    if (!authHeader) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: No Authorization header`);
      return NextResponse.json(
        { error: 'No authorization header', code: 'missing_bearer', requestId },
        { status: 401, headers: CACHE_HEADERS }
      );
    }

    if (!authHeader.startsWith('Bearer ')) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: Invalid format`);
      return NextResponse.json(
        { error: 'Invalid authorization format', code: 'invalid_bearer', requestId },
        { status: 401, headers: CACHE_HEADERS }
      );
    }

    const token = authHeader.split(' ')[1];
    console.log(`[Outlook Auth READ][${requestId}] Token extracted, length: ${token?.length || 0}`);
    console.log(`[Outlook Auth READ][${requestId}] Token prefix: ${token?.substring(0, 20)}...`);
    console.log(`[Outlook Auth READ][${requestId}] Supabase URL: ${supabaseUrl?.substring(0, 40)}...`);

    if (!token || token.length < 10) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: Token empty or too short`);
      return NextResponse.json(
        { error: 'Empty or invalid token', code: 'empty_token', requestId },
        { status: 401, headers: CACHE_HEADERS }
      );
    }

    // Create Supabase client with the user's JWT to verify it
    const supabase = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: `Bearer ${token}` } }
    });

    // Verify JWT by calling getUser
    console.log(`[Outlook Auth READ][${requestId}] Validating token against Supabase`);
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      console.error(`[Outlook Auth READ][${requestId}] FAIL: Token validation - ${error?.message || 'no user'}`);
      console.error(`[Outlook Auth READ][${requestId}] Supabase URL used: ${supabaseUrl}`);
      return NextResponse.json(
        {
          error: 'Token validation failed',
          code: 'token_invalid',
          detail: error?.message || 'no user returned',
          supabaseUrlPrefix: supabaseUrl?.substring(0, 30),
          requestId
        },
        { status: 401, headers: CACHE_HEADERS }
      );
    }

    console.log(`[Outlook Auth READ][${requestId}] Token valid for user: ${user.id}`);

    // Generate state with user_id and purpose for CSRF protection
    const state = generateOAuthState(user.id, 'read');

    // Build Microsoft OAuth URL for READ app
    const authUrl = buildAuthUrl('read', state);

    console.log(`[Outlook Auth READ][${requestId}] Generated auth URL for user:`, user.id);
    console.log(`[Outlook Auth READ][${requestId}] Using app:`, READ_APP.appId);

    return NextResponse.json({
      url: authUrl,
      state: state,
      purpose: 'read',
      scopes: READ_APP.scopes,
    }, { headers: CACHE_HEADERS });

  } catch (error) {
    console.error(`[Outlook Auth READ][${requestId}] Error:`, error);
    return NextResponse.json(
      { error: 'Failed to generate auth URL', code: 'internal_error', requestId },
      { status: 500, headers: CACHE_HEADERS }
    );
  }
}
