/**
 * Microsoft OAuth - Disconnect Account
 *
 * Revokes BOTH read and write tokens (soft delete).
 * Marks email_watchers as disconnected.
 * Does NOT delete email_threads/messages/links (preserves history).
 *
 * Per doctrine:
 * - Soft delete only - set is_revoked=true
 * - Historical email data preserved
 * - Separate "Delete all email data" endpoint for hard delete (future)
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  getServiceClient,
  getUserYachtId,
  revokeAllTokens,
  disconnectWatcher,
} from '@/lib/email/oauth-utils';

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
    const supabase = getServiceClient();
    const { data: { user }, error } = await supabase.auth.getUser(token);

    if (error || !user) {
      return NextResponse.json(
        { success: false, error: 'Invalid token' },
        { status: 401 }
      );
    }

    console.log('[Outlook Disconnect] Revoking tokens for user:', user.id);

    // Get user's yacht_id
    const yachtId = await getUserYachtId(supabase, user.id);
    if (!yachtId) {
      return NextResponse.json(
        { success: false, error: 'No yacht found for user' },
        { status: 400 }
      );
    }

    // Revoke all Microsoft tokens (both read and write)
    const revokeResult = await revokeAllTokens(supabase, user.id, yachtId, user.id);
    if (!revokeResult.success) {
      console.error('[Outlook Disconnect] Failed to revoke tokens:', revokeResult.error);
      return NextResponse.json(
        { success: false, error: 'Failed to revoke tokens' },
        { status: 500 }
      );
    }

    // Mark watcher as disconnected
    const watcherResult = await disconnectWatcher(supabase, user.id, yachtId);
    if (!watcherResult.success) {
      console.warn('[Outlook Disconnect] Failed to update watcher:', watcherResult.error);
      // Non-fatal - tokens are revoked
    }

    console.log('[Outlook Disconnect] Successfully disconnected');

    return NextResponse.json({
      success: true,
      message: 'Disconnected successfully. Email history preserved.',
    });

  } catch (error) {
    console.error('[Outlook Disconnect] Error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
