"""
Email Suggestion Service

Generates link suggestions when email threads are synced.
Per doctrine: suggestions never auto-accept, max 3 per thread.

Signals (in priority order):
1. Subject tokens: [WO-####], [PO-####], [FAULT-####], [EQ-####]
2. Vendor participant match: email hash matches supplier contact
3. Time proximity: thread created near object creation (weak signal)
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SuggestedLink:
    """A suggested link between email thread and operational object."""
    thread_id: str
    object_type: str
    object_id: str
    reason: str  # 'wo_pattern', 'po_pattern', 'vendor_domain', 'time_prox', etc.
    confidence: str = 'suggested'  # Always 'suggested' for auto-generated


class EmailSuggestionService:
    """
    Generates link suggestions for email threads.

    Usage:
        service = EmailSuggestionService(supabase_client)
        suggestions = await service.generate_suggestions(thread_id, yacht_id)
    """

    MAX_SUGGESTIONS_PER_THREAD = 3

    # Patterns for extracting object references from subjects
    PATTERNS = {
        'wo_pattern': re.compile(r'\[WO[#-]?(\d+)\]|\bWO[#-]?(\d+)\b', re.IGNORECASE),
        'po_pattern': re.compile(r'\[PO[#-]?(\d+)\]|\bPO[#-]?(\d+)\b', re.IGNORECASE),
        'fault_pattern': re.compile(r'\[FAULT[#-]?(\d+)\]|\bFAULT[#-]?(\d+)\b', re.IGNORECASE),
        'eq_pattern': re.compile(r'\[EQ[#-]?(\d+)\]|\bEQ[#-]?(\d+)\b', re.IGNORECASE),
    }

    # Time proximity window (hours)
    TIME_PROXIMITY_HOURS = 48

    def __init__(self, supabase):
        self.supabase = supabase

    async def generate_suggestions(
        self,
        thread_id: str,
        yacht_id: str
    ) -> List[SuggestedLink]:
        """
        Generate link suggestions for a thread.

        Returns up to MAX_SUGGESTIONS_PER_THREAD suggestions.
        """
        # Check existing suggestions
        existing_count = await self._count_existing_suggestions(thread_id)
        if existing_count >= self.MAX_SUGGESTIONS_PER_THREAD:
            logger.debug(f"Thread {thread_id} already has {existing_count} suggestions, skipping")
            return []

        remaining_slots = self.MAX_SUGGESTIONS_PER_THREAD - existing_count
        suggestions = []
        seen_objects = set()  # Avoid duplicate suggestions

        # Get thread data
        thread = await self._get_thread(thread_id, yacht_id)
        if not thread:
            logger.warning(f"Thread {thread_id} not found for yacht {yacht_id}")
            return []

        # 1. Subject pattern matching (highest priority)
        pattern_suggestions = await self._check_subject_patterns(
            thread, yacht_id, seen_objects
        )
        for s in pattern_suggestions:
            if len(suggestions) < remaining_slots:
                suggestions.append(s)
                seen_objects.add((s.object_type, s.object_id))

        # 2. Vendor participant match
        if len(suggestions) < remaining_slots:
            vendor_suggestions = await self._check_vendor_match(
                thread, yacht_id, seen_objects
            )
            for s in vendor_suggestions:
                if len(suggestions) < remaining_slots:
                    suggestions.append(s)
                    seen_objects.add((s.object_type, s.object_id))

        # 3. Time proximity (weak signal, only if we have room)
        if len(suggestions) < remaining_slots:
            time_suggestions = await self._check_time_proximity(
                thread, yacht_id, seen_objects
            )
            for s in time_suggestions:
                if len(suggestions) < remaining_slots:
                    suggestions.append(s)
                    seen_objects.add((s.object_type, s.object_id))

        # Create suggestions in database
        created = []
        for suggestion in suggestions:
            try:
                await self._create_suggestion(suggestion, yacht_id)
                created.append(suggestion)
            except Exception as e:
                logger.error(f"Failed to create suggestion: {e}")

        logger.info(f"Created {len(created)} suggestions for thread {thread_id}")
        return created

    async def _count_existing_suggestions(self, thread_id: str) -> int:
        """Count existing active suggestions for a thread."""
        try:
            result = self.supabase.table('email_links').select(
                'id', count='exact'
            ).eq('thread_id', thread_id).eq('is_active', True).execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"Error counting suggestions: {e}")
            return 0

    async def _get_thread(self, thread_id: str, yacht_id: str) -> Optional[Dict]:
        """Get thread with its messages."""
        try:
            # Get thread
            thread_result = self.supabase.table('email_threads').select(
                '*'
            ).eq('id', thread_id).eq('yacht_id', yacht_id).single().execute()

            if not thread_result.data:
                return None

            thread = thread_result.data

            # Get messages for participant hashes
            messages_result = self.supabase.table('email_messages').select(
                'from_address_hash, to_addresses_hash, cc_addresses_hash, subject'
            ).eq('thread_id', thread_id).execute()

            thread['messages'] = messages_result.data or []

            # Collect all participant hashes
            participant_hashes = set()
            for msg in thread['messages']:
                if msg.get('from_address_hash'):
                    participant_hashes.add(msg['from_address_hash'])
                for h in (msg.get('to_addresses_hash') or []):
                    participant_hashes.add(h)
                for h in (msg.get('cc_addresses_hash') or []):
                    participant_hashes.add(h)

            thread['all_participant_hashes'] = list(participant_hashes)

            return thread

        except Exception as e:
            logger.error(f"Error getting thread: {e}")
            return None

    async def _check_subject_patterns(
        self,
        thread: Dict,
        yacht_id: str,
        seen_objects: set
    ) -> List[SuggestedLink]:
        """
        Check subject for patterns like [WO-1234], [PO-5678], etc.
        """
        suggestions = []

        # Collect all subjects from thread
        subjects = [thread.get('latest_subject') or '']
        for msg in thread.get('messages', []):
            if msg.get('subject'):
                subjects.append(msg['subject'])

        combined_text = ' '.join(subjects)

        # Check work order patterns
        for match in self.PATTERNS['wo_pattern'].finditer(combined_text):
            wo_number = match.group(1) or match.group(2)
            if wo_number:
                # Look up work order by number (assuming wo_number is a display ID)
                wo = await self._find_work_order_by_number(wo_number, yacht_id)
                if wo and (wo['object_type'], wo['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='work_order',
                        object_id=wo['id'],
                        reason='wo_pattern'
                    ))

        # Check PO patterns
        for match in self.PATTERNS['po_pattern'].finditer(combined_text):
            po_number = match.group(1) or match.group(2)
            if po_number:
                po = await self._find_purchase_order_by_number(po_number, yacht_id)
                if po and ('purchase_order', po['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='purchase_order',
                        object_id=po['id'],
                        reason='po_pattern'
                    ))

        # Check fault patterns
        for match in self.PATTERNS['fault_pattern'].finditer(combined_text):
            fault_number = match.group(1) or match.group(2)
            if fault_number:
                fault = await self._find_fault_by_number(fault_number, yacht_id)
                if fault and ('fault', fault['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='fault',
                        object_id=fault['id'],
                        reason='wo_pattern'  # Using wo_pattern as generic pattern match
                    ))

        # Check equipment patterns
        for match in self.PATTERNS['eq_pattern'].finditer(combined_text):
            eq_number = match.group(1) or match.group(2)
            if eq_number:
                eq = await self._find_equipment_by_number(eq_number, yacht_id)
                if eq and ('equipment', eq['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='equipment',
                        object_id=eq['id'],
                        reason='wo_pattern'
                    ))

        return suggestions

    async def _check_vendor_match(
        self,
        thread: Dict,
        yacht_id: str,
        seen_objects: set
    ) -> List[SuggestedLink]:
        """
        Check if any participant email hash matches a supplier/vendor contact.
        """
        suggestions = []
        participant_hashes = thread.get('all_participant_hashes', [])

        if not participant_hashes:
            return suggestions

        try:
            # Query suppliers with matching contact email hashes
            # Note: This assumes pms_suppliers has a contact_email_hash column
            result = self.supabase.table('pms_suppliers').select(
                'id, name'
            ).eq('yacht_id', yacht_id).in_(
                'contact_email_hash', participant_hashes
            ).execute()

            for supplier in (result.data or []):
                if ('supplier', supplier['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='supplier',
                        object_id=supplier['id'],
                        reason='vendor_domain'
                    ))

            # Also check work orders with vendor assignments
            wo_result = self.supabase.table('pms_work_orders').select(
                'id, title'
            ).eq('yacht_id', yacht_id).in_(
                'vendor_contact_hash', participant_hashes
            ).execute()

            for wo in (wo_result.data or []):
                if ('work_order', wo['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='work_order',
                        object_id=wo['id'],
                        reason='vendor_domain'
                    ))

        except Exception as e:
            # Column may not exist - that's OK, just skip vendor matching
            logger.debug(f"Vendor match skipped: {e}")

        return suggestions

    async def _check_time_proximity(
        self,
        thread: Dict,
        yacht_id: str,
        seen_objects: set
    ) -> List[SuggestedLink]:
        """
        Weak signal: find objects created within TIME_PROXIMITY_HOURS of thread.
        Only suggest if we have very few other suggestions.
        """
        suggestions = []

        thread_created = thread.get('created_at')
        if not thread_created:
            return suggestions

        try:
            # Parse thread creation time
            if isinstance(thread_created, str):
                thread_time = datetime.fromisoformat(thread_created.replace('Z', '+00:00'))
            else:
                thread_time = thread_created

            window_start = thread_time - timedelta(hours=self.TIME_PROXIMITY_HOURS)
            window_end = thread_time + timedelta(hours=self.TIME_PROXIMITY_HOURS)

            # Find work orders created in this window
            result = self.supabase.table('pms_work_orders').select(
                'id, title'
            ).eq('yacht_id', yacht_id).gte(
                'created_at', window_start.isoformat()
            ).lte(
                'created_at', window_end.isoformat()
            ).limit(3).execute()

            for wo in (result.data or []):
                if ('work_order', wo['id']) not in seen_objects:
                    suggestions.append(SuggestedLink(
                        thread_id=thread['id'],
                        object_type='work_order',
                        object_id=wo['id'],
                        reason='time_prox'
                    ))

        except Exception as e:
            logger.debug(f"Time proximity check failed: {e}")

        return suggestions

    async def _find_work_order_by_number(
        self,
        number: str,
        yacht_id: str
    ) -> Optional[Dict]:
        """Find work order by display number."""
        try:
            # Try exact match on display_id or id suffix
            result = self.supabase.table('pms_work_orders').select(
                'id'
            ).eq('yacht_id', yacht_id).or_(
                f"display_id.eq.{number},id.ilike.%{number}"
            ).limit(1).execute()

            if result.data:
                return {'id': result.data[0]['id'], 'object_type': 'work_order'}
        except Exception as e:
            logger.debug(f"Work order lookup failed: {e}")
        return None

    async def _find_purchase_order_by_number(
        self,
        number: str,
        yacht_id: str
    ) -> Optional[Dict]:
        """Find purchase order by display number."""
        try:
            result = self.supabase.table('pms_purchase_orders').select(
                'id'
            ).eq('yacht_id', yacht_id).or_(
                f"display_id.eq.{number},po_number.eq.{number}"
            ).limit(1).execute()

            if result.data:
                return {'id': result.data[0]['id']}
        except Exception as e:
            logger.debug(f"Purchase order lookup failed: {e}")
        return None

    async def _find_fault_by_number(
        self,
        number: str,
        yacht_id: str
    ) -> Optional[Dict]:
        """Find fault by display number."""
        try:
            result = self.supabase.table('pms_faults').select(
                'id'
            ).eq('yacht_id', yacht_id).or_(
                f"display_id.eq.{number},fault_number.eq.{number}"
            ).limit(1).execute()

            if result.data:
                return {'id': result.data[0]['id']}
        except Exception as e:
            logger.debug(f"Fault lookup failed: {e}")
        return None

    async def _find_equipment_by_number(
        self,
        number: str,
        yacht_id: str
    ) -> Optional[Dict]:
        """Find equipment by display number."""
        try:
            result = self.supabase.table('pms_equipment').select(
                'id'
            ).eq('yacht_id', yacht_id).or_(
                f"display_id.eq.{number},equipment_number.eq.{number}"
            ).limit(1).execute()

            if result.data:
                return {'id': result.data[0]['id']}
        except Exception as e:
            logger.debug(f"Equipment lookup failed: {e}")
        return None

    async def _create_suggestion(
        self,
        suggestion: SuggestedLink,
        yacht_id: str
    ) -> None:
        """Create a suggestion in the database."""
        self.supabase.table('email_links').insert({
            'yacht_id': yacht_id,
            'thread_id': suggestion.thread_id,
            'object_type': suggestion.object_type,
            'object_id': suggestion.object_id,
            'confidence': suggestion.confidence,
            'suggested_reason': suggestion.reason,
            'suggested_at': datetime.utcnow().isoformat(),
            'is_active': True,
        }).execute()


# Convenience function for use in sync pipeline
async def generate_suggestions_for_thread(
    supabase,
    thread_id: str,
    yacht_id: str
) -> List[SuggestedLink]:
    """
    Generate link suggestions for a newly synced thread.

    Call this from _process_message() in email sync.
    """
    service = EmailSuggestionService(supabase)
    return await service.generate_suggestions(thread_id, yacht_id)
