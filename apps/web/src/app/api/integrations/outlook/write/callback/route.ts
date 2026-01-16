/**
 * Microsoft OAuth - Token Exchange Callback (WRITE App)
 *
 * Exchanges authorization code for tokens and stores with token_purpose='write'.
 * Updates email_watchers record.
 *
 * Per doctrine:
 * - WRITE tokens stored separately from READ tokens
 * - WRITE app only has Mail.Send (NO Mail.ReadWrite!)
 * - Forbidden scopes result in degraded status
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
      console.error('[Outlook Callback WRITE] OAuth error:', error, errorDescription);
      // Redirect to settings with error
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', error);
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'write');
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
    if (!stateData || stateData.purpose !== 'write') {
      console.error('[Outlook Callback WRITE] Invalid state or wrong purpose:', state);
      return NextResponse.json(
        { error: 'Invalid state parameter' },
        { status: 400 }
      );
    }

    const { userId } = stateData;
    console.log('[Outlook Callback WRITE] Processing callback for user:', userId);

    // Exchange code for tokens
    const tokenResult = await exchangeCodeForTokens(code, 'write');
    if (!tokenResult.success || !tokenResult.data) {
      console.error('[Outlook Callback WRITE] Token exchange failed:', tokenResult.error);
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', 'token_exchange_failed');
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'write');
      return NextResponse.redirect(redirectUrl.toString());
    }

    const { access_token, refresh_token, expires_in, scope } = tokenResult.data;
    const grantedScopes = scope.split(' ');

    // Check for forbidden scopes (doctrine enforcement)
    // CRITICAL: Mail.ReadWrite is forbidden for WRITE app
    const scopeCheck = checkScopes(grantedScopes);
    if (!scopeCheck.valid) {
      console.warn('[Outlook Callback WRITE] Forbidden scopes detected:', scopeCheck.forbidden);
    }

    // Fetch user profile from Graph
    const profile = await fetchGraphProfile(access_token);
    const email = profile?.email || '';
    const displayName = profile?.displayName || '';
    const emailHash = email ? hashEmail(email) : '';

    console.log('[Outlook Callback WRITE] Got profile:', email);

    // Get Supabase client and user's yacht_id
    const supabase = getServiceClient();
    const yachtId = await getUserYachtId(supabase, userId);

    if (!yachtId) {
      console.error('[Outlook Callback WRITE] No yacht_id found for user:', userId);
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', 'no_yacht');
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'write');
      return NextResponse.redirect(redirectUrl.toString());
    }

    // Build token record
    const tokenRecord: TokenRecord = {
      user_id: userId,
      yacht_id: yachtId,
      provider: 'microsoft_graph',
      token_purpose: 'write',
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
      console.error('[Outlook Callback WRITE] Failed to store token:', upsertResult.error);
      const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
      redirectUrl.searchParams.set('error', 'storage_failed');
      redirectUrl.searchParams.set('provider', 'outlook');
      redirectUrl.searchParams.set('purpose', 'write');
      return NextResponse.redirect(redirectUrl.toString());
    }

    console.log('[Outlook Callback WRITE] Token stored successfully');

    // Check if read token exists to determine watcher status
    const readToken = await getToken(supabase, userId, yachtId, 'read');
    const watcherStatus = determineWatcherStatus(
      readToken,
      tokenRecord,
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
      console.warn('[Outlook Callback WRITE] Failed to update watcher:', watcherResult.error);
      // Non-fatal - token is stored, continue
    }

    console.log('[Outlook Callback WRITE] Watcher status:', watcherStatus);

    // Redirect to settings with success
    const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
    redirectUrl.searchParams.set('success', 'true');
    redirectUrl.searchParams.set('provider', 'outlook');
    redirectUrl.searchParams.set('purpose', 'write');
    if (scopeCheck.warning) {
      redirectUrl.searchParams.set('warning', 'forbidden_scopes');
    }

    return NextResponse.redirect(redirectUrl.toString());

  } catch (error) {
    console.error('[Outlook Callback WRITE] Unexpected error:', error);
    const redirectUrl = new URL('/settings', process.env.NEXT_PUBLIC_APP_URL || 'https://app.celeste7.ai');
    redirectUrl.searchParams.set('error', 'unexpected');
    redirectUrl.searchParams.set('provider', 'outlook');
    redirectUrl.searchParams.set('purpose', 'write');
    return NextResponse.redirect(redirectUrl.toString());
  }
}
