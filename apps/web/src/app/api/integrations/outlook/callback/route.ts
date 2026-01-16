/**
 * Microsoft OAuth - Callback Handler (READ App)
 *
 * Receives OAuth callback from Microsoft and forwards to Render backend
 * for token exchange and storage. This keeps all secrets in Render.
 *
 * Flow:
 * 1. Microsoft redirects here with code + state
 * 2. We call Render /auth/outlook/exchange with the code
 * 3. Render exchanges code for tokens and stores them
 * 4. We redirect user to /settings with result
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

// Render backend URL
const RENDER_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// App URL for redirects
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai';

// Redirect URI for OAuth (must match Azure app registration)
const REDIRECT_URI = `${APP_URL}/api/integrations/outlook/callback`;

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    // Handle OAuth errors from Microsoft
    if (error) {
      console.error('[Outlook Callback READ] OAuth error from Microsoft:', error, errorDescription);
      const redirectUrl = new URL('/settings', APP_URL);
      redirectUrl.searchParams.set('error', error);
      redirectUrl.searchParams.set('provider', 'outlook');
      if (errorDescription) {
        redirectUrl.searchParams.set('error_description', errorDescription);
      }
      return NextResponse.redirect(redirectUrl.toString());
    }

    if (!code) {
      console.error('[Outlook Callback READ] No authorization code provided');
      const redirectUrl = new URL('/settings', APP_URL);
      redirectUrl.searchParams.set('error', 'no_code');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    if (!state) {
      console.error('[Outlook Callback READ] No state parameter');
      const redirectUrl = new URL('/settings', APP_URL);
      redirectUrl.searchParams.set('error', 'no_state');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    console.log('[Outlook Callback READ] Forwarding to Render for token exchange');

    // Call Render backend to exchange code and store tokens
    const renderResponse = await fetch(`${RENDER_API_URL}/auth/outlook/exchange`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code,
        state,
        redirect_uri: REDIRECT_URI,
      }),
    });

    const result = await renderResponse.json();

    console.log('[Outlook Callback READ] Render response:', {
      success: result.success,
      error: result.error,
      error_code: result.error_code,
    });

    // Build redirect URL based on result
    const redirectUrl = new URL('/settings', APP_URL);
    redirectUrl.searchParams.set('provider', 'outlook');
    redirectUrl.searchParams.set('purpose', 'read');

    if (result.success) {
      redirectUrl.searchParams.set('success', 'true');
      if (result.warning) {
        redirectUrl.searchParams.set('warning', result.warning);
      }
      if (result.email) {
        redirectUrl.searchParams.set('email', result.email);
      }
    } else {
      redirectUrl.searchParams.set('error', result.error_code || 'exchange_failed');
      if (result.error) {
        // Don't expose full error to URL, just log it
        console.error('[Outlook Callback READ] Exchange error:', result.error);
      }
    }

    return NextResponse.redirect(redirectUrl.toString());

  } catch (error) {
    console.error('[Outlook Callback READ] Unexpected error:', error);
    const redirectUrl = new URL('/settings', APP_URL);
    redirectUrl.searchParams.set('error', 'unexpected');
    redirectUrl.searchParams.set('provider', 'outlook');
    return NextResponse.redirect(redirectUrl.toString());
  }
}
