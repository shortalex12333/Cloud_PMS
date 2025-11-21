/**
 * Microsoft OAuth - Disconnect Account
 *
 * Removes stored Microsoft tokens for the user.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY || '';

export async function POST(request: NextRequest) {
  try {
    // Get JWT from Authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];

    // Verify JWT and get user_id
    const supabase = createClient(supabaseUrl, supabaseServiceKey);
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      return NextResponse.json(
        { success: false, error: 'Invalid token' },
        { status: 401 }
      );
    }

    console.log('[Outlook Disconnect] Removing tokens for user:', user.id);

    // Delete Microsoft tokens
    const { error: deleteError } = await supabase
      .from('api_tokens')
      .delete()
      .eq('user_id', user.id)
      .eq('provider', 'microsoft');

    if (deleteError) {
      console.error('[Outlook Disconnect] Failed to delete tokens:', deleteError);
      return NextResponse.json(
        { success: false, error: 'Failed to disconnect' },
        { status: 500 }
      );
    }

    console.log('[Outlook Disconnect] Successfully disconnected');

    return NextResponse.json({
      success: true,
    });

  } catch (error) {
    console.error('[Outlook Disconnect] Error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
