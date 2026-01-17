"""
Email Watcher - Linking Ladder

Phase 8: Deterministic linking ladder (L1-L5) for primary object selection.
"""

from typing import Dict, List, Any, Optional
import logging

from .token_extractor import TokenExtractor
from .candidate_finder import CandidateFinder
from .scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class LinkingLadder:
    """
    Deterministic linking ladder for email-to-object matching.

    Levels:
    - L1: Explicit ID match (WO-####, PO-####) → Auto-primary
    - L2: Strong procurement signals → Suggest with high confidence
    - L3: Part/serial match → Suggest equipment/part
    - L4: Open WO by vendor → Weak suggest
    - L5: Ambiguous / no match → Create procurement intent or skip
    """

    def __init__(self, supabase_client):
        """
        Initialize linking ladder.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client
        self.token_extractor = TokenExtractor()
        self.candidate_finder = CandidateFinder(supabase_client)
        self.scoring_engine = ScoringEngine()

    async def determine_primary(
        self,
        yacht_id: str,
        thread_id: str,
        subject: str,
        from_address: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        participant_hashes: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Run linking ladder L1-L5 to determine primary object.

        Args:
            yacht_id: Yacht ID for isolation
            thread_id: Email thread ID
            subject: Email subject line
            from_address: Sender email address
            attachments: List of attachment metadata
            participant_hashes: List of participant email hashes
            context: Additional context (vendor_affinity, etc.)

        Returns:
            Primary object selection or None
        """
        # Extract tokens
        tokens = self.token_extractor.extract_all(
            subject=subject,
            from_address=from_address,
            attachments=attachments,
            participant_hashes=participant_hashes
        )

        logger.debug(f"[LinkingLadder] Thread {thread_id}: Extracted tokens: {tokens}")

        # Store extracted tokens on thread
        await self._save_extracted_tokens(thread_id, tokens)

        # L1: Explicit IDs in subject (auto-primary)
        l1_result = await self._check_l1_explicit_ids(yacht_id, tokens)
        if l1_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L1 match - {l1_result['candidate']['label']}")
            return {'level': 'L1', 'confidence': 'deterministic', **l1_result}

        # L2: Strong procurement signals
        l2_result = await self._check_l2_procurement(yacht_id, tokens)
        if l2_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L2 match - {l2_result['candidate']['label']}")
            return {'level': 'L2', 'confidence': 'suggested', **l2_result}

        # L3: Part/serial match
        l3_result = await self._check_l3_parts_equipment(yacht_id, tokens)
        if l3_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L3 match - {l3_result['candidate']['label']}")
            return {'level': 'L3', 'confidence': 'suggested', **l3_result}

        # L4: Open WO by vendor
        l4_result = await self._check_l4_open_work_orders(yacht_id, tokens, context)
        if l4_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L4 match - {l4_result['candidate']['label']}")
            return {'level': 'L4', 'confidence': 'suggested', **l4_result}

        # L5: Ambiguous / no match
        logger.info(f"[LinkingLadder] Thread {thread_id}: L5 - No primary match found")
        return await self._handle_l5_no_match(yacht_id, thread_id, tokens)

    async def _check_l1_explicit_ids(
        self,
        yacht_id: str,
        tokens: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        L1: Check for explicit ID matches (WO-####, PO-####, etc.)

        These are deterministic - auto-confirm if found.
        """
        ids = tokens.get('ids', {})

        # Priority order for L1
        l1_ids = ['wo_id', 'po_id', 'fault_id', 'eq_id']

        for id_type in l1_ids:
            if id_type in ids and ids[id_type]:
                # Find matching object
                candidates = await self.candidate_finder.find_all_candidates(
                    yacht_id,
                    {'ids': {id_type: ids[id_type]}}
                )

                if candidates:
                    # Score and select
                    scored = self.scoring_engine.score_candidates(candidates)
                    if scored and self.scoring_engine.should_auto_confirm(scored[0].get('score', 0)):
                        return {
                            'candidate': scored[0],
                            'all_candidates': scored[:3],
                            'action': 'auto_link'
                        }

        return None

    async def _check_l2_procurement(
        self,
        yacht_id: str,
        tokens: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        L2: Check for strong procurement signals.

        Quote/Invoice IDs + procurement attachments.
        """
        # Check for procurement signals
        if not self.token_extractor.has_procurement_signal(tokens):
            return None

        ids = tokens.get('ids', {})
        vendor = tokens.get('vendor', {})

        # Find candidates for quote/invoice IDs
        candidates = []

        if 'quote_id' in ids or 'invoice_id' in ids:
            # These might link to POs or open WOs
            wo_candidates = await self.candidate_finder.find_work_order_candidates(
                yacht_id, ids, vendor
            )
            candidates.extend(wo_candidates)

        # Also check vendor match for procurement context
        if vendor.get('sender_hash'):
            vendor_candidates = await self.candidate_finder.find_vendor_candidates(
                yacht_id, vendor
            )
            candidates.extend(vendor_candidates)

        if candidates:
            scored = self.scoring_engine.score_candidates(candidates)
            selection = self.scoring_engine.select_primary(scored)

            if selection and selection.get('confidence') in ('deterministic', 'suggested'):
                return selection

        return None

    async def _check_l3_parts_equipment(
        self,
        yacht_id: str,
        tokens: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        L3: Check for part/serial number matches.
        """
        parts = tokens.get('parts', {})

        if not parts:
            return None

        candidates = []

        # Equipment by serial
        eq_candidates = await self.candidate_finder.find_equipment_candidates(
            yacht_id, parts
        )
        candidates.extend(eq_candidates)

        # Parts by part number
        part_candidates = await self.candidate_finder.find_part_candidates(
            yacht_id, parts
        )
        candidates.extend(part_candidates)

        if candidates:
            scored = self.scoring_engine.score_candidates(candidates)
            selection = self.scoring_engine.select_primary(scored)

            if selection:
                # For equipment matches, also look for related open WOs
                if selection['candidate'].get('object_type') == 'equipment':
                    equipment_id = selection['candidate']['object_id']
                    related_wos = await self.candidate_finder.find_open_work_orders_by_equipment(
                        yacht_id, equipment_id
                    )
                    if related_wos:
                        selection['related_work_orders'] = related_wos

                return selection

        return None

    async def _check_l4_open_work_orders(
        self,
        yacht_id: str,
        tokens: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        L4: Check for open work orders by vendor match.
        """
        vendor = tokens.get('vendor', {})

        if not vendor.get('sender_hash'):
            return None

        # Skip if personal email domain
        if vendor.get('is_personal_domain'):
            return None

        candidates = await self.candidate_finder.find_work_order_candidates(
            yacht_id,
            {},  # No ID match
            vendor
        )

        if candidates:
            scored = self.scoring_engine.score_candidates(candidates, context)
            selection = self.scoring_engine.select_primary(scored)

            if selection:
                return selection

        return None

    async def _handle_l5_no_match(
        self,
        yacht_id: str,
        thread_id: str,
        tokens: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        L5: Handle no match case.

        Options:
        - If procurement signals, create procurement_intent stub
        - Otherwise, return None (no suggestion)
        """
        # Check if this looks like a vendor conversation
        vendor = tokens.get('vendor', {})
        has_procurement = self.token_extractor.has_procurement_signal(tokens)

        if has_procurement and vendor.get('sender_hash') and not vendor.get('is_personal_domain'):
            # Could create procurement_intent here
            logger.info(
                f"[LinkingLadder] Thread {thread_id}: L5 - Potential procurement intent "
                f"from domain {vendor.get('sender_domain')}"
            )

            return {
                'level': 'L5',
                'confidence': 'none',
                'action': 'procurement_intent',
                'vendor_domain': vendor.get('sender_domain'),
                'vendor_hash': vendor.get('sender_hash'),
            }

        return None

    async def _save_extracted_tokens(
        self,
        thread_id: str,
        tokens: Dict[str, Any]
    ) -> None:
        """Save extracted tokens to thread record."""
        try:
            self.supabase.rpc('mark_thread_suggestions_generated', {
                'p_thread_id': thread_id,
                'p_extracted_tokens': tokens
            }).execute()
        except Exception as e:
            logger.error(f"[LinkingLadder] Error saving tokens: {e}")

    async def create_link_suggestion(
        self,
        yacht_id: str,
        thread_id: str,
        selection: Dict[str, Any],
        max_suggestions: int = 3
    ) -> List[str]:
        """
        Create email_links suggestions based on ladder result.

        Args:
            yacht_id: Yacht ID
            thread_id: Email thread ID
            selection: Ladder selection result
            max_suggestions: Maximum suggestions to create (default 3)

        Returns:
            List of created link IDs
        """
        created_ids = []

        if not selection or selection.get('action') == 'procurement_intent':
            return created_ids

        candidate = selection.get('candidate')
        if not candidate:
            return created_ids

        # Determine confidence level
        confidence = selection.get('confidence', 'suggested')

        # Create primary suggestion
        try:
            result = self.supabase.table('email_links').insert({
                'yacht_id': yacht_id,
                'thread_id': thread_id,
                'object_type': candidate['object_type'],
                'object_id': candidate['object_id'],
                'confidence': confidence,
                'is_primary': True,
                'score': candidate.get('score'),
                'score_breakdown': candidate.get('score_breakdown'),
                'suggested_reason': candidate.get('match_reason'),
                'is_active': confidence == 'deterministic',  # Auto-active for L1
            }).execute()

            if result.data:
                created_ids.append(result.data[0]['id'])

        except Exception as e:
            logger.error(f"[LinkingLadder] Error creating primary suggestion: {e}")

        # Create additional suggestions (non-primary)
        all_candidates = selection.get('all_candidates', selection.get('candidates', []))
        for i, alt in enumerate(all_candidates[1:max_suggestions]):
            try:
                result = self.supabase.table('email_links').insert({
                    'yacht_id': yacht_id,
                    'thread_id': thread_id,
                    'object_type': alt['object_type'],
                    'object_id': alt['object_id'],
                    'confidence': 'suggested',
                    'is_primary': False,
                    'score': alt.get('score'),
                    'score_breakdown': alt.get('score_breakdown'),
                    'suggested_reason': alt.get('match_reason'),
                    'is_active': False,
                }).execute()

                if result.data:
                    created_ids.append(result.data[0]['id'])

            except Exception as e:
                logger.error(f"[LinkingLadder] Error creating alternate suggestion: {e}")

        return created_ids


# Export
__all__ = ['LinkingLadder']
