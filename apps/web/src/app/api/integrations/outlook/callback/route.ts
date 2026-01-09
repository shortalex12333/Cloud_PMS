/**
 * Microsoft OAuth - Token Exchange Callback
 *
 * Exchanges the authorization code for access/refresh tokens.
 * Stores tokens in Supabase auth_microsoft_tokens table.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

// Azure App credentials from environment
const AZURE_APP_ID = process.env.AZURE_APP_ID || '41f6dc82-8127-4330-97e0-c6b26e6aa967';
const AZURE_CLIENT_SECRET = process.env.AZURE_CLIENT_SECRET || '';
const AZURE_TENANT = 'common';

// Log config status on startup (without exposing secrets)
if (!AZURE_CLIENT_SECRET) {
  console.error('[Outlook Callback] CRITICAL: AZURE_CLIENT_SECRET not configured!');
}

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
    console.log('[Outlook Callback] Using redirect_uri:', REDIRECT_URI);

    // Validate credentials are present
    if (!AZURE_CLIENT_SECRET) {
      console.error('[Outlook Callback] Missing AZURE_CLIENT_SECRET environment variable');
      return NextResponse.json(
        { error: 'Server misconfiguration: missing Azure credentials' },
        { status: 500 }
      );
    }

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
      console.error('[Outlook Callback] Token exchange failed:', JSON.stringify(errorData, null, 2));

      // Provide helpful error messages
      let errorMessage = 'Token exchange failed';
      if (errorData.error === 'invalid_grant') {
        errorMessage = 'Authorization code expired or already used. Please try again.';
      } else if (errorData.error_description?.includes('redirect_uri')) {
        errorMessage = `Redirect URI mismatch. Expected: ${REDIRECT_URI}. Please check Azure App Registration.`;
      }

      return NextResponse.json(
        { error: errorMessage, detail: errorData },
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

    // Get user's yacht_id from auth_users table
    const { data: userRecord, error: userError } = await supabase
      .from('auth_users')
      .select('yacht_id')
      .eq('auth_user_id', userId)
      .single();

    if (userError || !userRecord?.yacht_id) {
      console.error('[Outlook Callback] Failed to get user yacht_id:', userError);
      return NextResponse.json(
        { error: 'User profile not found' },
        { status: 400 }
      );
    }

    // Check for existing OAuth token for this user
    const { data: existingToken } = await supabase
      .from('auth_microsoft_tokens')
      .select('id')
      .eq('user_id', userId)
      .eq('token_type', 'oauth')
      .eq('token_name', 'microsoft_outlook')
      .single();

    // Build token record matching auth_microsoft_tokens schema
    const tokenRecord = {
      id: existingToken?.id || crypto.randomUUID(),
      user_id: userId,
      yacht_id: userRecord.yacht_id,
      token_hash: hashToken(tokenData.access_token),
      token_type: 'oauth',
      token_name: 'microsoft_outlook',
      scopes: ['Mail.Read', 'User.Read', 'MailboxSettings.Read', 'offline_access'],
      issued_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + tokenData.expires_in * 1000).toISOString(),
      is_revoked: false,
      metadata: {
        provider: 'microsoft',
        email: userEmail,
        display_name: displayName,
        refresh_token: tokenData.refresh_token, // TODO: encrypt in production
        access_token: tokenData.access_token, // Needed for API calls
      },
    };

    // Upsert to handle reconnections
    const { error: upsertError } = await supabase
      .from('auth_microsoft_tokens')
      .upsert(tokenRecord, {
        onConflict: 'id',
        ignoreDuplicates: false
      });

    if (upsertError) {
      console.error('[Outlook Callback] Failed to store tokens:', upsertError);
      return NextResponse.json(
        { error: 'Failed to store tokens', detail: upsertError.message },
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
