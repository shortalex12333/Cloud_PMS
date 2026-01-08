/**
 * Microsoft OAuth - Connection Status
 *
 * Returns whether user has connected their Outlook account.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

export async function GET(request: NextRequest) {
  try {
    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json(
        { connected: false, error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];

    // Verify JWT and get user_id
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      return NextResponse.json(
        { connected: false, error: 'Invalid token' },
        { status: 401 }
      );
    }

    // Check for existing Microsoft OAuth token
    const { data: tokenData, error: tokenError } = await supabase
      .from('auth_microsoft_tokens')
      .select('metadata, issued_at, expires_at, is_revoked')
      .eq('user_id', user.id)
      .eq('token_type', 'oauth')
      .eq('token_name', 'microsoft_outlook')
      .single();

    if (tokenError || !tokenData) {
      return NextResponse.json({
        connected: false,
      });
    }

    // Check if token is expired or revoked
    const isExpired = new Date(tokenData.expires_at) < new Date();
    const isRevoked = tokenData.is_revoked;

    // Extract email from metadata
    const metadata = tokenData.metadata as { email?: string; display_name?: string } || {};

    return NextResponse.json({
      connected: !isExpired && !isRevoked,
      email: metadata.email || '',
      displayName: metadata.display_name || '',
      connectedAt: tokenData.issued_at,
      expiresAt: tokenData.expires_at,
    });

  } catch (error) {
    console.error('[Outlook Status] Error:', error);
    return NextResponse.json(
      { connected: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
