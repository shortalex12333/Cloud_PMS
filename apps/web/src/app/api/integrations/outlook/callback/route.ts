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
      const redirectUrl = new URL('/', APP_URL);
      redirectUrl.searchParams.set('error', error);
      redirectUrl.searchParams.set('provider', 'outlook');
      if (errorDescription) {
        redirectUrl.searchParams.set('error_description', errorDescription);
      }
      return NextResponse.redirect(redirectUrl.toString());
    }

    if (!code) {
      console.error('[Outlook Callback READ] No authorization code provided');
      const redirectUrl = new URL('/', APP_URL);
      redirectUrl.searchParams.set('error', 'no_code');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    if (!state) {
      console.error('[Outlook Callback READ] No state parameter');
      const redirectUrl = new URL('/', APP_URL);
      redirectUrl.searchParams.set('error', 'no_state');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    console.log('[Outlook Callback READ] OAUTH_CALLBACK_START', {
      hasCode: !!code,
      codeLength: code?.length,
      hasState: !!state,
      stateLength: state?.length,
      redirectUri: REDIRECT_URI,
      renderUrl: `${RENDER_API_URL}/auth/outlook/exchange`,
    });

    // Call Render backend to exchange code and store tokens
    let renderResponse: Response;
    try {
      renderResponse = await fetch(`${RENDER_API_URL}/auth/outlook/exchange`, {
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
    } catch (fetchError) {
      console.error('[Outlook Callback READ] FETCH_FAILED - Network error calling Render:', fetchError);
      const redirectUrl = new URL('/', APP_URL);
      redirectUrl.searchParams.set('error', 'render_unreachable');
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'read');
      return NextResponse.redirect(redirectUrl.toString());
    }

    console.log('[Outlook Callback READ] Render HTTP status:', renderResponse.status);

    // Handle non-200 responses
    if (!renderResponse.ok) {
      const errorText = await renderResponse.text();
      console.error('[Outlook Callback READ] RENDER_HTTP_ERROR:', {
        status: renderResponse.status,
        statusText: renderResponse.statusText,
        body: errorText.substring(0, 500),
      });
      const redirectUrl = new URL('/', APP_URL);
      redirectUrl.searchParams.set('error', `render_${renderResponse.status}`);
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'read');
      return NextResponse.redirect(redirectUrl.toString());
    }

    let result: any;
    try {
      result = await renderResponse.json();
    } catch (jsonError) {
      console.error('[Outlook Callback READ] JSON_PARSE_FAILED:', jsonError);
      const redirectUrl = new URL('/', APP_URL);
      redirectUrl.searchParams.set('error', 'render_invalid_response');
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'read');
      return NextResponse.redirect(redirectUrl.toString());
    }

    console.log('[Outlook Callback READ] OAUTH_CALLBACK_RENDER_RESPONSE:', {
      success: result.success,
      error: result.error,
      error_code: result.error_code,
    });

    // Build redirect URL based on result
    // Redirect to root - Celeste is single-surface, no /settings page
    const redirectUrl = new URL('/', APP_URL);
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
    const errorMessage = error instanceof Error ? error.message : String(error);
    const errorStack = error instanceof Error ? error.stack : '';
    console.error('[Outlook Callback READ] UNEXPECTED_ERROR:', {
      message: errorMessage,
      stack: errorStack,
      type: typeof error,
    });
    const redirectUrl = new URL('/', APP_URL);
    redirectUrl.searchParams.set('error', 'unexpected');
    redirectUrl.searchParams.set('detail', errorMessage.substring(0, 100));
    redirectUrl.searchParams.set('provider', 'outlook');
    redirectUrl.searchParams.set('purpose', 'read');
    return NextResponse.redirect(redirectUrl.toString());
  }
}
