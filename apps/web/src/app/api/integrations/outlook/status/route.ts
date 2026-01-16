/**
 * Microsoft OAuth - Connection Status
 *
 * Returns detailed status for both READ and WRITE connections,
 * plus email_watchers sync state.
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
import {
  getServiceClient,
  getUserYachtId,
  getToken,
  getWatcher,
  ConnectionStatus,
} from '@/lib/email/oauth-utils';

export async function GET(request: NextRequest) {
  try {
    // Check required env vars
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !anonKey) {
      console.error('[Outlook Status] Missing env vars');
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

    // Verify JWT using anon client (doesn't need service key)
    const authClient = createClient(supabaseUrl, anonKey);
    const { data: { user }, error } = await authClient.auth.getUser(token);

    if (error || !user) {
      console.error('[Outlook Status] Auth error:', error?.message);
      return NextResponse.json(
        { error: 'Invalid token' },
        { status: 401 }
      );
    }

    // For DB queries, prefer service client if available (bypasses RLS)
    // Fall back to auth client with user's JWT if no service key
    let dbClient;
    if (serviceKey) {
      dbClient = getServiceClient();
    } else {
      dbClient = createClient(supabaseUrl, anonKey, {
        global: { headers: { Authorization: `Bearer ${token}` } }
      });
    }

    // Get user's yacht_id
    const yachtId = await getUserYachtId(dbClient, user.id);
    if (!yachtId) {
      return NextResponse.json<ConnectionStatus>({
        read: { connected: false, expires_at: null, scopes: [] },
        write: { connected: false, expires_at: null, scopes: [] },
        watcher: null,
      });
    }

    // Get read token
    const readToken = await getToken(dbClient, user.id, yachtId, 'read');
    const readConnected = readToken !== null &&
      !readToken.is_revoked &&
      new Date(readToken.token_expires_at) > new Date();

    // Get write token
    const writeToken = await getToken(dbClient, user.id, yachtId, 'write');
    const writeConnected = writeToken !== null &&
      !writeToken.is_revoked &&
      new Date(writeToken.token_expires_at) > new Date();

    // Get watcher status
    const watcher = await getWatcher(dbClient, user.id, yachtId);

    // Build response
    const status: ConnectionStatus = {
      read: {
        connected: readConnected,
        expires_at: readToken?.token_expires_at || null,
        scopes: readToken?.scopes || [],
        email: readToken?.provider_display_name || undefined,
      },
      write: {
        connected: writeConnected,
        expires_at: writeToken?.token_expires_at || null,
        scopes: writeToken?.scopes || [],
        email: writeToken?.provider_display_name || undefined,
      },
      watcher: watcher,
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
