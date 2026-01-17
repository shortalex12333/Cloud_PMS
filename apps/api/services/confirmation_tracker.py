"""
Email Watcher - Confirmation Tracker

Phase 9: Track user confirmations for learning and vendor affinity.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConfirmationTracker:
    """
    Track user decisions on link suggestions for learning.

    Records:
    - Accept: User accepted system suggestion
    - Reject: User rejected suggestion
    - Change: User changed to different object
    - Unlink: User removed a link

    Uses decisions to learn vendor affinity patterns.
    """

    def __init__(self, supabase_client):
        """
        Initialize confirmation tracker.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def record_decision(
        self,
        yacht_id: str,
        thread_id: str,
        action: str,
        chosen_object: Optional[Dict[str, Any]],
        previous_suggestion: Optional[Dict[str, Any]],
        user_id: str
    ) -> str:
        """
        Record user's link decision.

        Args:
            yacht_id: Yacht ID
            thread_id: Email thread ID
            action: Decision type ('accept', 'reject', 'change', 'unlink')
            chosen_object: Object user chose (type, id) or None
            previous_suggestion: What system suggested (for learning)
            user_id: User who made the decision

        Returns:
            Decision record ID
        """
        try:
            decision_data = {
                'yacht_id': yacht_id,
                'thread_id': thread_id,
                'action': action,
                'chosen_object_type': chosen_object.get('object_type') if chosen_object else None,
                'chosen_object_id': chosen_object.get('object_id') if chosen_object else None,
                'previous_suggestion': previous_suggestion,
                'system_score': previous_suggestion.get('score') if previous_suggestion else None,
                'created_by': user_id,
            }

            result = self.supabase.table('email_link_decisions').insert(
                decision_data
            ).execute()

            decision_id = result.data[0]['id'] if result.data else None

            logger.info(
                f"[ConfirmationTracker] Recorded {action} decision for thread {thread_id[:8]}..."
            )

            return decision_id

        except Exception as e:
            logger.error(f"[ConfirmationTracker] Error recording decision: {e}")
            raise

    async def get_vendor_affinity(
        self,
        yacht_id: str,
        vendor_hash: str,
        limit: int = 50
    ) -> Dict[str, int]:
        """
        Get learned vendor → object type affinity.

        Analyzes past decisions for this vendor to predict
        what type of object they usually link to.

        Args:
            yacht_id: Yacht ID
            vendor_hash: SHA256 hash of vendor email
            limit: Maximum decisions to analyze

        Returns:
            Dictionary mapping object_type to affinity score
        """
        try:
            # Get threads from this vendor
            threads = self.supabase.table('email_threads').select(
                'id'
            ).eq('yacht_id', yacht_id).contains(
                'participant_hashes', [vendor_hash]
            ).limit(limit).execute()

            if not threads.data:
                return {}

            thread_ids = [t['id'] for t in threads.data]

            # Get decisions for these threads
            decisions = self.supabase.table('email_link_decisions').select(
                'chosen_object_type, action'
            ).eq('yacht_id', yacht_id).in_(
                'thread_id', thread_ids
            ).execute()

            if not decisions.data:
                return {}

            # Count object types from accepted/changed decisions
            affinity = {}
            for decision in decisions.data:
                obj_type = decision.get('chosen_object_type')
                action = decision.get('action')

                if obj_type and action in ('accept', 'change'):
                    affinity[obj_type] = affinity.get(obj_type, 0) + 1

            # Normalize to scores (max 15 points per vendor affinity rule)
            max_count = max(affinity.values()) if affinity else 1
            for obj_type in affinity:
                affinity[obj_type] = min(15, int(15 * affinity[obj_type] / max_count))

            return affinity

        except Exception as e:
            logger.error(f"[ConfirmationTracker] Error getting vendor affinity: {e}")
            return {}

    async def get_decision_stats(
        self,
        yacht_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get decision statistics for a yacht.

        Args:
            yacht_id: Yacht ID
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        try:
            # Get decisions from last N days
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            result = self.supabase.table('email_link_decisions').select(
                'action, system_score'
            ).eq('yacht_id', yacht_id).gte(
                'created_at', cutoff
            ).execute()

            decisions = result.data or []

            # Calculate stats
            stats = {
                'total': len(decisions),
                'accepts': 0,
                'rejects': 0,
                'changes': 0,
                'unlinks': 0,
                'avg_score_accepted': 0,
                'avg_score_rejected': 0,
            }

            accepted_scores = []
            rejected_scores = []

            for d in decisions:
                action = d.get('action')
                score = d.get('system_score')

                if action == 'accept':
                    stats['accepts'] += 1
                    if score:
                        accepted_scores.append(score)
                elif action == 'reject':
                    stats['rejects'] += 1
                    if score:
                        rejected_scores.append(score)
                elif action == 'change':
                    stats['changes'] += 1
                elif action == 'unlink':
                    stats['unlinks'] += 1

            if accepted_scores:
                stats['avg_score_accepted'] = sum(accepted_scores) / len(accepted_scores)
            if rejected_scores:
                stats['avg_score_rejected'] = sum(rejected_scores) / len(rejected_scores)

            # Calculate acceptance rate
            suggestions = stats['accepts'] + stats['rejects'] + stats['changes']
            if suggestions > 0:
                stats['acceptance_rate'] = stats['accepts'] / suggestions
            else:
                stats['acceptance_rate'] = None

            return stats

        except Exception as e:
            logger.error(f"[ConfirmationTracker] Error getting stats: {e}")
            return {}

    async def update_link_on_decision(
        self,
        yacht_id: str,
        thread_id: str,
        action: str,
        chosen_object: Optional[Dict[str, Any]],
        link_id: Optional[str] = None
    ) -> None:
        """
        Update email_links table based on user decision.

        Args:
            yacht_id: Yacht ID
            thread_id: Thread ID
            action: Decision action
            chosen_object: Chosen object (for accept/change)
            link_id: Specific link ID (for accept/reject)
        """
        try:
            now = datetime.utcnow().isoformat()

            if action == 'accept' and link_id:
                # Accept a suggestion - activate it as primary
                self.supabase.table('email_links').update({
                    'is_active': True,
                    'is_primary': True,
                    'confidence': 'confirmed',
                    'accepted_at': now,
                }).eq('id', link_id).execute()

                # Deactivate other links for this thread
                self.supabase.table('email_links').update({
                    'is_primary': False,
                }).eq('thread_id', thread_id).neq('id', link_id).execute()

            elif action == 'reject' and link_id:
                # Reject a suggestion - mark as blocked
                self.supabase.table('email_links').update({
                    'is_active': False,
                    'user_blocked': True,
                    'removed_at': now,
                }).eq('id', link_id).execute()

            elif action == 'change' and chosen_object:
                # User chose a different object
                # Deactivate all existing links
                self.supabase.table('email_links').update({
                    'is_active': False,
                    'is_primary': False,
                }).eq('thread_id', thread_id).execute()

                # Create new link for chosen object
                self.supabase.table('email_links').insert({
                    'yacht_id': yacht_id,
                    'thread_id': thread_id,
                    'object_type': chosen_object['object_type'],
                    'object_id': chosen_object['object_id'],
                    'confidence': 'confirmed',
                    'is_active': True,
                    'is_primary': True,
                    'accepted_at': now,
                    'suggested_reason': 'user_selected',
                }).execute()

            elif action == 'unlink':
                # Remove all links for thread
                self.supabase.table('email_links').update({
                    'is_active': False,
                    'is_primary': False,
                    'removed_at': now,
                }).eq('thread_id', thread_id).execute()

        except Exception as e:
            logger.error(f"[ConfirmationTracker] Error updating links: {e}")
            raise


# Export
__all__ = ['ConfirmationTracker']
