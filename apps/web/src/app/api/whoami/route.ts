import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

/**
 * GET /api/whoami
 *
 * Returns the authenticated user's identity and yacht context.
 * This endpoint queries the master DB to get:
 * - user_id
 * - yacht_id
 * - role
 * - status
 * - yacht_name
 *
 * Authentication: Requires valid Supabase JWT in Authorization header
 *
 * This is the server-side equivalent of get_my_bootstrap RPC.
 * Use this when you need server-side auth validation.
 */

// Master DB client (using env vars)
function getMasterClient(accessToken: string) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('Supabase environment variables not configured');
  }

  return createClient(supabaseUrl, supabaseAnonKey, {
    global: {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  });
}

export async function GET(request: NextRequest) {
  try {
    // Extract JWT from Authorization header
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid Authorization header' },
        { status: 401 }
      );
    }

    const accessToken = authHeader.replace('Bearer ', '');

    // Create client with user's token
    const supabase = getMasterClient(accessToken);

    // Verify the token and get user
    const { data: { user }, error: userError } = await supabase.auth.getUser();

    if (userError || !user) {
      return NextResponse.json(
        { error: 'Invalid or expired token' },
        { status: 401 }
      );
    }

    // Call get_my_bootstrap RPC to get yacht context
    const { data: bootstrap, error: rpcError } = await supabase.rpc('get_my_bootstrap');

    if (rpcError) {
      console.error('[/api/whoami] RPC error:', rpcError.message);

      // Return minimal user info even if bootstrap fails
      return NextResponse.json({
        user_id: user.id,
        email: user.email,
        yacht_id: null,
        role: 'pending',
        status: 'BOOTSTRAP_ERROR',
        yacht_name: null,
        yacht_active: false,
        error: rpcError.message,
      }, { status: 200 }); // 200 because user IS authenticated
    }

    // Return bootstrap data
    return NextResponse.json({
      user_id: user.id,
      email: user.email,
      yacht_id: bootstrap?.yacht_id || null,
      role: bootstrap?.role || 'pending',
      status: bootstrap?.status || 'PENDING',
      yacht_name: bootstrap?.yacht_name || null,
      yacht_active: bootstrap?.yacht_active ?? false,
    });

  } catch (error) {
    console.error('[/api/whoami] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * OPTIONS /api/whoami
 * CORS preflight handler
 */
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': 'https://app.celeste7.ai',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Authorization, Content-Type',
      'Access-Control-Max-Age': '86400',
    },
  });
}
