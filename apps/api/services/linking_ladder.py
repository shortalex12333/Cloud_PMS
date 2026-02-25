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
        Run linking ladder to determine primary object.

        Strategy: L1 first (deterministic), then parallel L2.5+L3, choose best by score.
        This avoids "first-wins" masking better downstream candidates.

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

        # =======================================================================
        # PHASE 1: L1 Deterministic (check first, auto-confirm if found)
        # =======================================================================
        l1_result = await self._check_l1_explicit_ids(yacht_id, tokens)
        if l1_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L1 match - {l1_result['candidate']['label']}")
            return {'level': 'L1', 'confidence': 'deterministic', **l1_result}

        # L2: Strong procurement signals (check before parallel phase)
        l2_result = await self._check_l2_procurement(yacht_id, tokens)
        if l2_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L2 match - {l2_result['candidate']['label']}")
            return {'level': 'L2', 'confidence': 'suggested', **l2_result}

        # =======================================================================
        # PHASE 2: Parallel L2.5 + L3 (score-and-choose best)
        # =======================================================================
        # Run L2.5 (semantic) and L3 (heuristic) together, pick highest score
        l25_result = await self._check_l25_hybrid(yacht_id, thread_id, subject, tokens, context)
        l3_result = await self._check_l3_parts_equipment(yacht_id, tokens)

        # Collect all candidates with their levels
        candidates_with_levels = []

        if l25_result and l25_result.get('candidate'):
            candidates_with_levels.append({
                'level': 'L2.5',
                'result': l25_result,
                'score': l25_result.get('candidate', {}).get('score', 0),
                'label': l25_result.get('candidate', {}).get('label', 'unknown')
            })

        if l3_result and l3_result.get('candidate'):
            candidates_with_levels.append({
                'level': 'L3',
                'result': l3_result,
                'score': l3_result.get('candidate', {}).get('score', 0),
                'label': l3_result.get('candidate', {}).get('label', 'unknown')
            })

        # Choose best by score
        if candidates_with_levels:
            # Sort by score descending
            candidates_with_levels.sort(key=lambda x: x['score'], reverse=True)
            best = candidates_with_levels[0]

            # Check for ambiguity: if top two are within 10 points, flag it
            if len(candidates_with_levels) >= 2:
                gap = best['score'] - candidates_with_levels[1]['score']
                if gap < 10:
                    logger.debug(
                        f"[LinkingLadder] Thread {thread_id}: Ambiguous between "
                        f"{best['level']} ({best['score']}) and "
                        f"{candidates_with_levels[1]['level']} ({candidates_with_levels[1]['score']})"
                    )
                    best['result']['candidate']['ambiguous'] = True

            logger.info(
                f"[LinkingLadder] Thread {thread_id}: {best['level']} match "
                f"(score={best['score']}) - {best['label']}"
            )
            return {'level': best['level'], 'confidence': 'suggested', **best['result']}

        # =======================================================================
        # PHASE 3: L4 Fallback (vendor match on open WOs)
        # =======================================================================
        l4_result = await self._check_l4_open_work_orders(yacht_id, tokens, context)
        if l4_result:
            logger.info(f"[LinkingLadder] Thread {thread_id}: L4 match - {l4_result['candidate']['label']}")
            return {'level': 'L4', 'confidence': 'suggested', **l4_result}

        # =======================================================================
        # PHASE 4: L5 No match
        # =======================================================================
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

        # Priority order for L1 - includes both numeric wo_id and full wo_number patterns
        l1_ids = ['wo_id', 'wo_number', 'po_id', 'fault_id', 'eq_id']

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

    async def _check_l25_hybrid(
        self,
        yacht_id: str,
        thread_id: str,
        subject: str,
        tokens: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        L2.5: Hybrid search index retrieval (text + vector + recency + role bias).

        Queries search_index with:
        - Text: subject + top entity values
        - Vector: GPT-1536 embedding (if available)
        - Recency: exponential decay (90-day half-life)
        - Bias: role-based weights

        Only auto-confirms if score >= 130 AND not ambiguous.
        Otherwise creates suggestions.
        """
        # Build query text from subject + top entities
        query_text_parts = [subject]

        # Add top entity values for richer query
        ids = tokens.get('ids', {})
        parts = tokens.get('parts', {})
        vendor = tokens.get('vendor', {})

        # Add explicit IDs (WO, PO, etc.) - but these should have matched L1
        for id_type, values in ids.items():
            if values:
                query_text_parts.append(' '.join(values))

        # Add part/serial numbers for equipment/part context
        for part_type, values in parts.items():
            if values:
                query_text_parts.append(' '.join(values[:3]))  # Top 3 to avoid bloat

        # Add vendor name if present
        if vendor.get('sender_name'):
            query_text_parts.append(vendor['sender_name'])

        query_text = ' '.join(query_text_parts)[:500]  # Cap at 500 chars

        # Try to get embedding for this thread (if prepared by email_rag)
        query_embedding = await self._get_thread_embedding(thread_id)

        # Get user role from context (if available)
        user_role = context.get('user_role') if context else None

        logger.debug(f"[LinkingLadder] L2.5: query_text='{query_text[:100]}...' embedding={'present' if query_embedding else 'missing'}")

        # Query search_index - search across ALL entity types in the index
        # The RPC handles object_types=None by searching all types
        candidates = await self.candidate_finder.find_search_index_candidates(
            yacht_id=yacht_id,
            query_text=query_text,
            query_embedding=query_embedding,
            role=user_role,
            object_types=None,  # Search all entity types (work_order, equipment, part, fault, document, etc.)
            days_back=365,
            limit=20
        )

        if not candidates:
            logger.debug(f"[LinkingLadder] L2.5: No candidates found")
            return None

        # Score candidates using hybrid fusion
        scored = self.scoring_engine.score_hybrid_candidates(candidates, use_rrf=False)

        # Check if top candidate meets auto-confirm threshold
        if scored:
            top_score = scored[0].get('score', 0)
            ambiguous = scored[0].get('ambiguous', False)

            # Auto-confirm only if score >= 130 AND not ambiguous
            if top_score >= self.scoring_engine.THRESHOLDS['auto_confirm'] and not ambiguous:
                logger.info(f"[LinkingLadder] L2.5: Auto-confirming {scored[0]['label']} (score={top_score})")
                return {
                    'candidate': scored[0],
                    'all_candidates': scored[:3],
                    'action': 'auto_link'
                }

            # Otherwise create suggestion if score meets threshold
            if self.scoring_engine.should_create_suggestion(top_score):
                logger.info(f"[LinkingLadder] L2.5: Suggesting {scored[0]['label']} (score={top_score})")
                return {
                    'candidate': scored[0],
                    'all_candidates': scored[:3],
                    'action': 'suggest'
                }

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

    async def _get_thread_embedding(self, thread_id: str) -> Optional[List[float]]:
        """
        Get embedding for thread (from email_messages.embedding or meta_embedding).

        Args:
            thread_id: Email thread ID

        Returns:
            1536-dim embedding vector or None if not found
        """
        try:
            # Get latest message in thread with embedding
            result = self.supabase.table('email_messages').select(
                'embedding, meta_embedding'
            ).eq('thread_id', thread_id).order(
                'sent_at', desc=True
            ).limit(1).maybe_single().execute()

            if result.data:
                # Prefer meta_embedding (summary of thread) over individual message embedding
                embedding = result.data.get('meta_embedding') or result.data.get('embedding')
                if embedding:
                    # Parse string vector format if needed (Supabase returns vector as string)
                    if isinstance(embedding, str):
                        import json
                        try:
                            embedding = json.loads(embedding)
                        except json.JSONDecodeError:
                            logger.warning(f"[LinkingLadder] Invalid embedding format for thread {thread_id}")
                            return None
                    return embedding

        except Exception as e:
            logger.debug(f"[LinkingLadder] Error fetching thread embedding: {e}")

        return None

    def _map_match_reason_to_suggested_reason(self, match_reason: str) -> str:
        """
        Map internal match_reason to database suggested_reason enum.

        Args:
            match_reason: Internal match reason from CandidateFinder

        Returns:
            Valid suggested_reason for email_links table
        """
        mapping = {
            'wo_id_match': 'wo_pattern',
            'po_id_match': 'po_pattern',
            'part_number_match': 'part_number',
            'serial_match': 'serial_match',
            'vendor_email_match': 'vendor_domain',
            'vendor_hash_match': 'vendor_domain',
            'vendor_domain_match': 'vendor_domain',
            'hybrid_search_index': 'token_match',
            'equipment_wo_link': 'token_match',
            'oem_number_match': 'part_number',
        }
        return mapping.get(match_reason, 'token_match')

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

        # Map match_reason to valid suggested_reason
        suggested_reason = self._map_match_reason_to_suggested_reason(
            candidate.get('match_reason', 'unknown')
        )

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
                'suggested_reason': suggested_reason,
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
                alt_suggested_reason = self._map_match_reason_to_suggested_reason(
                    alt.get('match_reason', 'unknown')
                )
                result = self.supabase.table('email_links').insert({
                    'yacht_id': yacht_id,
                    'thread_id': thread_id,
                    'object_type': alt['object_type'],
                    'object_id': alt['object_id'],
                    'confidence': 'suggested',
                    'is_primary': False,
                    'score': alt.get('score'),
                    'score_breakdown': alt.get('score_breakdown'),
                    'suggested_reason': alt_suggested_reason,
                    'is_active': False,
                }).execute()

                if result.data:
                    created_ids.append(result.data[0]['id'])

            except Exception as e:
                logger.error(f"[LinkingLadder] Error creating alternate suggestion: {e}")

        return created_ids


# Export
__all__ = ['LinkingLadder']
