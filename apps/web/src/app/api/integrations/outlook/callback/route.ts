/**
 * Microsoft OAuth - Token Exchange Callback (READ App)
 *
 * Exchanges authorization code for tokens and stores with token_purpose='read'.
 * Creates/updates email_watchers record.
 *
 * Per doctrine:
 * - READ tokens stored separately from WRITE tokens
 * - Forbidden scopes result in degraded status
 * - No email bodies stored
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  getServiceClient,
  parseOAuthState,
  exchangeCodeForTokens,
  fetchGraphProfile,
  getUserYachtId,
  upsertToken,
  getToken,
  checkScopes,
  determineWatcherStatus,
  upsertWatcher,
  hashEmail,
  TokenRecord,
} from '@/lib/email/oauth-utils';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    // Handle OAuth errors from Microsoft
    if (error) {
      console.error('[Outlook Callback READ] OAuth error:', error, errorDescription);
      // Redirect to settings with error
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', error);
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    if (!code) {
      return NextResponse.json(
        { error: 'No authorization code provided' },
        { status: 400 }
      );
    }

    // Parse state to get user_id and purpose
    const stateData = parseOAuthState(state || '');
    if (!stateData || stateData.purpose !== 'read') {
      console.error('[Outlook Callback READ] Invalid state or wrong purpose:', state);
      return NextResponse.json(
        { error: 'Invalid state parameter' },
        { status: 400 }
      );
    }

    const { userId } = stateData;
    console.log('[Outlook Callback READ] Processing callback for user:', userId);

    // Exchange code for tokens
    const tokenResult = await exchangeCodeForTokens(code, 'read');
    if (!tokenResult.success || !tokenResult.data) {
      console.error('[Outlook Callback READ] Token exchange failed:', tokenResult.error);
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', 'token_exchange_failed');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    const { access_token, refresh_token, expires_in, scope } = tokenResult.data;
    const grantedScopes = scope.split(' ');

    // Check for forbidden scopes (doctrine enforcement)
    const scopeCheck = checkScopes(grantedScopes);
    if (!scopeCheck.valid) {
      console.warn('[Outlook Callback READ] Forbidden scopes detected:', scopeCheck.forbidden);
    }

    // Fetch user profile from Graph
    const profile = await fetchGraphProfile(access_token);
    const email = profile?.email || '';
    const displayName = profile?.displayName || '';
    const emailHash = email ? hashEmail(email) : '';

    console.log('[Outlook Callback READ] Got profile:', email);

    // Get Supabase client and user's yacht_id
    const supabase = getServiceClient();
    const yachtId = await getUserYachtId(supabase, userId);

    if (!yachtId) {
      console.error('[Outlook Callback READ] No yacht_id found for user:', userId);
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', 'no_yacht');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    // Build token record
    const tokenRecord: TokenRecord = {
      user_id: userId,
      yacht_id: yachtId,
      provider: 'microsoft_graph',
      token_purpose: 'read',
      microsoft_access_token: access_token,
      microsoft_refresh_token: refresh_token || '',
      token_expires_at: new Date(Date.now() + expires_in * 1000).toISOString(),
      scopes: grantedScopes,
      provider_email_hash: emailHash,
      provider_display_name: displayName,
      is_revoked: false,
    };

    // Upsert token
    const upsertResult = await upsertToken(supabase, tokenRecord);
    if (!upsertResult.success) {
      console.error('[Outlook Callback READ] Failed to store token:', upsertResult.error);
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', 'storage_failed');
      redirectUrl.searchParams.set('provider', 'outlook');
      return NextResponse.redirect(redirectUrl.toString());
    }

    console.log('[Outlook Callback READ] Token stored successfully');

    // Check if write token exists to determine watcher status
    const writeToken = await getToken(supabase, userId, yachtId, 'write');
    const watcherStatus = determineWatcherStatus(
      tokenRecord,
      writeToken,
      !scopeCheck.valid
    );

    // Upsert watcher
    const watcherResult = await upsertWatcher(
      supabase,
      userId,
      yachtId,
      emailHash,
      watcherStatus
    );

    if (!watcherResult.success) {
      console.warn('[Outlook Callback READ] Failed to update watcher:', watcherResult.error);
      // Non-fatal - token is stored, continue
    }

    console.log('[Outlook Callback READ] Watcher status:', watcherStatus);

    // Redirect to settings with success
    const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
    redirectUrl.searchParams.set('success', 'true');
    redirectUrl.searchParams.set('provider', 'outlook');
    redirectUrl.searchParams.set('purpose', 'read');
    if (scopeCheck.warning) {
      redirectUrl.searchParams.set('warning', 'forbidden_scopes');
    }

    return NextResponse.redirect(redirectUrl.toString());

  } catch (error) {
    console.error('[Outlook Callback READ] Unexpected error:', error);
    const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
    redirectUrl.searchParams.set('error', 'unexpected');
    redirectUrl.searchParams.set('provider', 'outlook');
    return NextResponse.redirect(redirectUrl.toString());
  }
}
