/**
 * Microsoft OAuth - Connection Status
 *
 * Proxies to Render backend which has access to both MASTER and TENANT databases.
 * This fixes the issue where frontend can't directly query TENANT DB for tokens.
 *
 * Response shape:
 * {
 *   read: { connected, expires_at, scopes, email },
 *   write: { connected, expires_at, scopes, email },
 *   watcher: { sync_status, last_sync_at, subscription_expires_at, last_sync_error }
 * }
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET(request: NextRequest) {
  try {
    // Check required env vars
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    const renderBackendUrl = process.env.NEXT_PUBLIC_RENDER_BACKEND_URL || 'https://pipeline-core.int.celeste7.ai';

    if (!supabaseUrl || !anonKey) {
      console.error('[Outlook Status] Missing Supabase env vars');
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];

    // Verify JWT using anon client
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error } = await authClient.auth.getUser(token);

    if (error || !user) {
      console.error('[Outlook Status] Auth error:', error?.message);
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    // Proxy to Render backend which has access to both MASTER and TENANT DBs
    const backendResponse = await fetch(`${renderBackendUrl}/auth/outlook/status`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!backendResponse.ok) {
      console.error('[Outlook Status] Backend error:', backendResponse.status);
      return NextResponse.json(
        { error: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const backendData = await backendResponse.json();

    // Transform backend response to match expected frontend format
    // Backend returns: { connected, email, token_purpose, scopes, expires_at }
    // Frontend expects: { read: {...}, write: {...}, watcher: {...} }

    const status = {
      read: {
        connected: backendData.connected && backendData.token_purpose === 'read',
        expires_at: backendData.expires_at || null,
        scopes: backendData.scopes || [],
        email: backendData.email || undefined,
      },
      write: {
        connected: backendData.connected && backendData.token_purpose === 'write',
        expires_at: backendData.expires_at || null,
        scopes: backendData.scopes || [],
        email: backendData.email || undefined,
      },
      watcher: null, // TODO: Add watcher status to backend endpoint
    };

    return NextResponse.json(status);

  } catch (error) {
    console.error('[Outlook Status] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
