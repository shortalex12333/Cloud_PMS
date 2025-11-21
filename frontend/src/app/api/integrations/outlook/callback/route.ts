/**
 * Microsoft OAuth - Token Exchange Callback
 *
 * Exchanges the authorization code for access/refresh tokens.
 * Stores tokens in Supabase api_tokens table.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Azure App credentials from environment
const AZURE_APP_ID = process.env.AZURE_APP_ID || '';
const AZURE_CLIENT_SECRET = process.env.AZURE_CLIENT_SECRET || '';
const AZURE_TENANT = 'common';

// Token endpoint
const TOKEN_URL = `https://login.microsoftonline.com/${AZURE_TENANT}/oauth2/v2.0/token`;
const GRAPH_URL = 'https://graph.microsoft.com/v1.0/me';

// Redirect URI - must match auth-url route
const REDIRECT_URI = process.env.NEXT_PUBLIC_APP_URL
  ? `${process.env.NEXT_PUBLIC_APP_URL}/integrations/outlook/callback`
  : 'https://celeste7.ai/integrations/outlook/callback';

// Supabase
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    // Handle OAuth errors
    if (error) {
      console.error('[Outlook Callback] OAuth error:', error);
      return NextResponse.json(
        { error: 'OAuth authentication failed', detail: error },
        { status: 400 }
      );
    }

    if (!code) {
      return NextResponse.json(
        { error: 'No authorization code provided' },
        { status: 400 }
      );
    }

    // Extract user_id from state
    const userId = state?.split(':')[0];
    if (!userId) {
      return NextResponse.json(
        { error: 'Invalid state parameter' },
        { status: 400 }
      );
    }

    console.log('[Outlook Callback] Exchanging code for tokens, user:', userId);

    // Exchange code for tokens
    const tokenResponse = await fetch(TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: AZURE_APP_ID,
        client_secret: AZURE_CLIENT_SECRET,
        code: code,
        grant_type: 'authorization_code',
        redirect_uri: REDIRECT_URI,
      }),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('[Outlook Callback] Token exchange failed:', errorData);
      return NextResponse.json(
        { error: 'Token exchange failed', detail: errorData },
        { status: 400 }
      );
    }

    const tokenData = await tokenResponse.json();
    console.log('[Outlook Callback] Token exchange successful');

    // Fetch user profile from Microsoft Graph
    const userResponse = await fetch(GRAPH_URL, {
      headers: {
        'Authorization': `Bearer ${tokenData.access_token}`,
      },
    });

    let userEmail = '';
    let displayName = '';

    if (userResponse.ok) {
      const userData = await userResponse.json();
      userEmail = userData.mail || userData.userPrincipalName || '';
      displayName = userData.displayName || '';
      console.log('[Outlook Callback] Got user profile:', userEmail);
    }

    // Store tokens in Supabase
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const tokenRecord = {
      user_id: userId,
      provider: 'microsoft',
      token_type: 'device',
      access_token_hash: hashToken(tokenData.access_token),
      refresh_token_encrypted: tokenData.refresh_token, // TODO: encrypt properly
      expires_at: new Date(Date.now() + tokenData.expires_in * 1000).toISOString(),
      scopes: ['mail:read', 'user:read'],
      email: userEmail,
      display_name: displayName,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Upsert to handle reconnections
    const { error: upsertError } = await supabase
      .from('api_tokens')
      .upsert(tokenRecord, {
        onConflict: 'user_id,provider',
        ignoreDuplicates: false
      });

    if (upsertError) {
      console.error('[Outlook Callback] Failed to store tokens:', upsertError);
      return NextResponse.json(
        { error: 'Failed to store tokens' },
        { status: 500 }
      );
    }

    console.log('[Outlook Callback] Tokens stored successfully');

    return NextResponse.json({
      success: true,
      email: userEmail,
    });

  } catch (error) {
    console.error('[Outlook Callback] Unexpected error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

// Simple hash for access token (for lookup, not storage)
function hashToken(token: string): string {
  // In production, use proper crypto
  let hash = 0;
  for (let i = 0; i < token.length; i++) {
    const char = token.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16);
}
