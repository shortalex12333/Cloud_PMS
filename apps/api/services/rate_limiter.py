"""
Email Watcher - Microsoft Graph API Rate Limiter

Respects Microsoft's 10,000 calls/hour limit.
Tracks calls per user/yacht in email_watchers table.
Auto-pauses sync when approaching limit.
"""

from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MicrosoftRateLimiter:
    """
    Rate limiter for Microsoft Graph API calls.

    Microsoft enforces 10,000 API calls per hour per mailbox.
    We use a safety margin to avoid hitting the hard limit.
    """

    HOURLY_LIMIT = 10_000
    SAFETY_MARGIN = 500  # Stop at 9,500 to be safe
    EFFECTIVE_LIMIT = HOURLY_LIMIT - SAFETY_MARGIN

    def __init__(self, supabase_client):
        """
        Initialize rate limiter with Supabase client.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def can_make_call(self, user_id: str, yacht_id: str) -> bool:
        """
        Check if we can make another API call without exceeding rate limit.

        Args:
            user_id: User ID of the mailbox owner
            yacht_id: Yacht ID for isolation

        Returns:
            True if call is allowed, False if rate limited
        """
        try:
            # First, reset counter if hour has elapsed
            await self.reset_if_new_hour(user_id, yacht_id)

            # Get current count
            result = self.supabase.table('email_watchers').select(
                'api_calls_this_hour, hour_window_start'
            ).eq('user_id', user_id).eq('yacht_id', yacht_id).single().execute()

            if not result.data:
                logger.warning(f"[RateLimiter] No watcher found for user={user_id}, yacht={yacht_id}")
                return False

            calls_this_hour = result.data.get('api_calls_this_hour', 0) or 0

            if calls_this_hour >= self.EFFECTIVE_LIMIT:
                logger.warning(
                    f"[RateLimiter] Rate limit reached: {calls_this_hour}/{self.EFFECTIVE_LIMIT} "
                    f"for user={user_id}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"[RateLimiter] Error checking rate limit: {e}")
            # Fail closed - don't make call if we can't verify
            return False

    async def record_call(self, user_id: str, yacht_id: str, count: int = 1) -> int:
        """
        Record API call(s) made.

        Args:
            user_id: User ID of the mailbox owner
            yacht_id: Yacht ID for isolation
            count: Number of calls made (default 1)

        Returns:
            New total call count for this hour
        """
        try:
            # Use RPC function for atomic update
            result = self.supabase.rpc('record_email_api_calls', {
                'p_user_id': user_id,
                'p_yacht_id': yacht_id,
                'p_call_count': count
            }).execute()

            new_count = result.data if result.data else 0

            logger.debug(
                f"[RateLimiter] Recorded {count} call(s), total: {new_count} "
                f"for user={user_id}"
            )

            return new_count

        except Exception as e:
            logger.error(f"[RateLimiter] Error recording call: {e}")
            # Still return 0 but log the error
            return 0

    async def get_remaining_calls(self, user_id: str, yacht_id: str) -> int:
        """
        Get remaining API calls allowed this hour.

        Args:
            user_id: User ID of the mailbox owner
            yacht_id: Yacht ID for isolation

        Returns:
            Number of remaining calls allowed
        """
        try:
            result = self.supabase.table('email_watchers').select(
                'api_calls_this_hour'
            ).eq('user_id', user_id).eq('yacht_id', yacht_id).single().execute()

            if not result.data:
                return 0

            calls_this_hour = result.data.get('api_calls_this_hour', 0) or 0
            remaining = max(0, self.EFFECTIVE_LIMIT - calls_this_hour)

            return remaining

        except Exception as e:
            logger.error(f"[RateLimiter] Error getting remaining calls: {e}")
            return 0

    async def reset_if_new_hour(self, user_id: str, yacht_id: str) -> bool:
        """
        Reset counter if hour window has passed.

        Args:
            user_id: User ID of the mailbox owner
            yacht_id: Yacht ID for isolation

        Returns:
            True if counter was reset, False otherwise
        """
        try:
            # Use RPC function for atomic check-and-reset
            self.supabase.rpc('reset_email_watcher_rate_limit', {
                'p_user_id': user_id,
                'p_yacht_id': yacht_id
            }).execute()

            return True

        except Exception as e:
            logger.error(f"[RateLimiter] Error resetting rate limit: {e}")
            return False

    async def pause_watcher(
        self,
        user_id: str,
        yacht_id: str,
        reason: str = 'rate_limit'
    ) -> None:
        """
        Pause a watcher (e.g., when rate limited or error occurred).

        Args:
            user_id: User ID of the mailbox owner
            yacht_id: Yacht ID for isolation
            reason: Reason for pausing
        """
        try:
            self.supabase.table('email_watchers').update({
                'is_paused': True,
                'pause_reason': reason,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('yacht_id', yacht_id).execute()

            logger.info(f"[RateLimiter] Paused watcher for user={user_id}, reason={reason}")

        except Exception as e:
            logger.error(f"[RateLimiter] Error pausing watcher: {e}")

    async def resume_watcher(self, user_id: str, yacht_id: str) -> None:
        """
        Resume a paused watcher.

        Args:
            user_id: User ID of the mailbox owner
            yacht_id: Yacht ID for isolation
        """
        try:
            self.supabase.table('email_watchers').update({
                'is_paused': False,
                'pause_reason': None,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('user_id', user_id).eq('yacht_id', yacht_id).execute()

            logger.info(f"[RateLimiter] Resumed watcher for user={user_id}")

        except Exception as e:
            logger.error(f"[RateLimiter] Error resuming watcher: {e}")

    def get_stats(self, watcher_data: dict) -> dict:
        """
        Get rate limit statistics for a watcher.

        Args:
            watcher_data: Watcher row data

        Returns:
            Dictionary with rate limit stats
        """
        calls_this_hour = watcher_data.get('api_calls_this_hour', 0) or 0
        hour_window_start = watcher_data.get('hour_window_start')

        # Calculate time until reset
        time_until_reset = None
        if hour_window_start:
            try:
                window_start = datetime.fromisoformat(hour_window_start.replace('Z', '+00:00'))
                window_end = window_start + timedelta(hours=1)
                now = datetime.utcnow().replace(tzinfo=window_start.tzinfo)
                if window_end > now:
                    time_until_reset = (window_end - now).total_seconds()
            except:
                pass

        return {
            'calls_this_hour': calls_this_hour,
            'calls_remaining': max(0, self.EFFECTIVE_LIMIT - calls_this_hour),
            'limit': self.EFFECTIVE_LIMIT,
            'hard_limit': self.HOURLY_LIMIT,
            'time_until_reset_seconds': time_until_reset,
            'is_rate_limited': calls_this_hour >= self.EFFECTIVE_LIMIT
        }


# Export
__all__ = ['MicrosoftRateLimiter']
