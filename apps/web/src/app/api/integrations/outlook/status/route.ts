/**
 * Microsoft OAuth - Connection Status
 *
 * Proxies to Render backend which has access to both MASTER and TENANT databases.
 * Returns simplified status for frontend consumption.
 *
 * Response shape:
 * {
 *   connected: boolean,
 *   email?: string,
 *   connectedAt?: string
 * }
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Force dynamic rendering - this route requires auth headers
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  const requestId = Math.random().toString(36).substring(7);
  console.log(`[Outlook Status][${requestId}] Request received`);

  try {
    // Check required env vars
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    const renderBackendUrl = process.env.NEXT_PUBLIC_RENDER_BACKEND_URL || 'https://pipeline-core.int.celeste7.ai';

    if (!supabaseUrl || !anonKey) {
      console.error(`[Outlook Status][${requestId}] Missing Supabase env vars`);
      return NextResponse.json(
        { error: 'Server configuration error', code: 'config_error' },
        {
          status: 500,
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
        }
      );
    }

    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    console.log(`[Outlook Status][${requestId}] Auth header present: ${!!authHeader}, length: ${authHeader?.length || 0}`);

    if (!authHeader) {
      return NextResponse.json(
        { error: 'No authorization header', code: 'missing_bearer' },
        {
          status: 401,
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
        }
      );
    }

    if (!authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Invalid authorization format', code: 'invalid_bearer' },
        {
          status: 401,
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
        }
      );
    }

    const token = authHeader.split(' ')[1];
    if (!token || token.length < 10) {
      return NextResponse.json(
        { error: 'Empty or invalid token', code: 'empty_token' },
        {
          status: 401,
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
        }
      );
    }

    // Verify JWT using anon client
    const authClient = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: `Bearer ${token}` } }
    });
    const { data: { user }, error } = await authClient.auth.getUser(token);

    if (error || !user) {
      console.error(`[Outlook Status][${requestId}] Token validation failed:`, error?.message);
      return NextResponse.json(
        { error: 'Token validation failed', code: 'token_invalid' },
        {
          status: 401,
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
        }
      );
    }

    console.log(`[Outlook Status][${requestId}] Token valid for user: ${user.id}`);

    // Proxy to Render backend which has access to both MASTER and TENANT DBs
    const backendResponse = await fetch(`${renderBackendUrl}/auth/outlook/status`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!backendResponse.ok) {
      console.error(`[Outlook Status][${requestId}] Backend error: ${backendResponse.status}`);

      // If backend returns 404, user has no connection
      if (backendResponse.status === 404) {
        return NextResponse.json(
          { connected: false },
          { headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' } }
        );
      }

      return NextResponse.json(
        { error: 'Backend request failed', code: 'backend_error' },
        {
          status: backendResponse.status,
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
        }
      );
    }

    const backendData = await backendResponse.json();
    console.log(`[Outlook Status][${requestId}] Backend response:`, {
      connected: backendData.connected,
      email: backendData.email,
      purpose: backendData.token_purpose
    });

    // Transform to simplified frontend format
    const status = {
      connected: backendData.connected || false,
      email: backendData.email || undefined,
      connectedAt: backendData.connected_at || backendData.expires_at || undefined,
    };

    return NextResponse.json(status, {
      headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
    });

  } catch (error) {
    console.error(`[Outlook Status][${requestId}] Error:`, error);
    return NextResponse.json(
      { error: 'Internal server error', code: 'internal_error' },
      {
        status: 500,
        headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' }
      }
    );
  }
}
