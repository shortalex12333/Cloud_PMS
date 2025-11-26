/**
 * Microsoft OAuth - Generate Authorization URL
 *
 * Generates the Microsoft OAuth URL with proper scopes and state for CSRF protection.
 * Called when user clicks "Connect Outlook" in settings.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Azure App credentials from environment
// Fallback to known app ID from Azure portal
const AZURE_APP_ID = process.env.AZURE_APP_ID || '41f6dc82-8127-4330-97e0-c6b26e6aa967';
const AZURE_TENANT = 'common'; // Multi-tenant

// OAuth configuration
const SCOPES = [
  'Mail.Read',
  'User.Read',
  'MailboxSettings.Read',
  'offline_access'
].join(' ');

// Redirect URI - must match Azure App Registration
const REDIRECT_URI = process.env.NEXT_PUBLIC_APP_URL
  ? `${process.env.NEXT_PUBLIC_APP_URL}/integrations/outlook/callback`
  : 'https://celeste7.ai/integrations/outlook/callback';

// Supabase client for getting user context
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

function generateState(): string {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
}

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
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    // Generate state with user_id for CSRF protection
    const state = `${user.id}:${generateState()}`;

    // Build Microsoft OAuth URL
    const authUrl = new URL(`https://login.microsoftonline.com/${AZURE_TENANT}/oauth2/v2.0/authorize`);
    authUrl.searchParams.set('client_id', AZURE_APP_ID);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
    authUrl.searchParams.set('scope', SCOPES);
    authUrl.searchParams.set('state', state);
    authUrl.searchParams.set('response_mode', 'query');

    console.log('[Outlook Auth] Generated auth URL for user:', user.id);

    return NextResponse.json({
      url: authUrl.toString(),
      state: state
    });

  } catch (error) {
    console.error('[Outlook Auth] Error generating auth URL:', error);
    return NextResponse.json(
      { error: 'Failed to generate auth URL' },
      { status: 500 }
    );
  }
}
