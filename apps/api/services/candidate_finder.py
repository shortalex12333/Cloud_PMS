"""
Email Watcher - Candidate Finder

Finds PMS objects that might match an email thread based on extracted tokens.
Phase 7e-g: Work Orders, Equipment/Parts, Vendors
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CandidateFinder:
    """
    Find candidate PMS objects matching email tokens.

    Queries indexed fields in PMS tables:
    - pms_work_orders (wo_number, vendor_contact_hash)
    - equipment (serial_number)
    - pms_parts (part_number)
    - vendors (email_hash, domain)
    """

    def __init__(self, supabase_client):
        """
        Initialize candidate finder.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def find_all_candidates(
        self,
        yacht_id: str,
        tokens: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find all candidate objects for given tokens.

        Args:
            yacht_id: Yacht ID for isolation
            tokens: Extracted tokens from TokenExtractor

        Returns:
            List of candidate objects with scores
        """
        candidates = []

        # Get ID tokens
        ids = tokens.get('ids', {})
        parts = tokens.get('parts', {})
        vendor = tokens.get('vendor', {})

        # Phase 7e: Work Order candidates
        wo_candidates = await self.find_work_order_candidates(yacht_id, ids, vendor)
        candidates.extend(wo_candidates)

        # Phase 7f: Equipment candidates
        eq_candidates = await self.find_equipment_candidates(yacht_id, parts)
        candidates.extend(eq_candidates)

        # Phase 7f: Part candidates
        part_candidates = await self.find_part_candidates(yacht_id, parts)
        candidates.extend(part_candidates)

        # Phase 7g: Vendor candidates
        vendor_candidates = await self.find_vendor_candidates(yacht_id, vendor)
        candidates.extend(vendor_candidates)

        return candidates

    # ==========================================================================
    # Phase 7e: Work Order Candidates
    # ==========================================================================

    async def find_work_order_candidates(
        self,
        yacht_id: str,
        ids: Dict[str, List[str]],
        vendor: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find work order candidates.

        Matches:
        - WO number (120 points - hard match)
        - Vendor hash on open WO (45 points)

        Args:
            yacht_id: Yacht ID
            ids: Extracted ID tokens
            vendor: Vendor signals

        Returns:
            List of candidates
        """
        candidates = []

        # 1. Exact WO number match (highest priority)
        if 'wo_id' in ids:
            for wo_num in ids['wo_id']:
                try:
                    result = self.supabase.table('pms_work_orders').select(
                        'id, wo_number, title, status, updated_at'
                    ).eq('yacht_id', yacht_id).ilike(
                        'wo_number', f'%{wo_num}%'
                    ).execute()

                    for row in result.data or []:
                        candidates.append({
                            'object_type': 'work_order',
                            'object_id': row['id'],
                            'label': f"WO-{row['wo_number']}: {row['title']}",
                            'match_reason': 'wo_id_match',
                            'score': 120,  # Hard match
                            'status': row.get('status'),
                            'updated_at': row.get('updated_at'),
                        })

                except Exception as e:
                    logger.error(f"[CandidateFinder] WO number search error: {e}")

        # 2. Vendor hash match on open work orders
        sender_hash = vendor.get('sender_hash')
        if sender_hash:
            try:
                result = self.supabase.table('pms_work_orders').select(
                    'id, wo_number, title, status'
                ).eq('yacht_id', yacht_id).eq(
                    'vendor_contact_hash', sender_hash
                ).eq('status', 'open').execute()

                for row in result.data or []:
                    # Don't duplicate if already matched by WO number
                    if not any(c['object_id'] == row['id'] for c in candidates):
                        candidates.append({
                            'object_type': 'work_order',
                            'object_id': row['id'],
                            'label': f"WO-{row['wo_number']}: {row['title']}",
                            'match_reason': 'vendor_hash_match',
                            'score': 45,
                            'status': row.get('status'),
                        })

            except Exception as e:
                logger.error(f"[CandidateFinder] Vendor hash WO search error: {e}")

        return candidates

    # ==========================================================================
    # Phase 7f: Equipment Candidates
    # ==========================================================================

    async def find_equipment_candidates(
        self,
        yacht_id: str,
        parts: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Find equipment candidates by serial number.

        Args:
            yacht_id: Yacht ID
            parts: Extracted part/serial tokens

        Returns:
            List of candidates
        """
        candidates = []

        # Serial number match
        serial_numbers = parts.get('serial_number', [])
        for serial in serial_numbers:
            try:
                result = self.supabase.table('equipment').select(
                    'id, name, serial_number, model, manufacturer'
                ).eq('yacht_id', yacht_id).ilike(
                    'serial_number', f'%{serial}%'
                ).execute()

                for row in result.data or []:
                    candidates.append({
                        'object_type': 'equipment',
                        'object_id': row['id'],
                        'label': f"{row['name']} (S/N: {row['serial_number']})",
                        'match_reason': 'serial_match',
                        'score': 70,
                        'model': row.get('model'),
                        'manufacturer': row.get('manufacturer'),
                    })

            except Exception as e:
                logger.error(f"[CandidateFinder] Serial number search error: {e}")

        return candidates

    # ==========================================================================
    # Phase 7f: Part Candidates
    # ==========================================================================

    async def find_part_candidates(
        self,
        yacht_id: str,
        parts: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Find part candidates by part number.

        Args:
            yacht_id: Yacht ID
            parts: Extracted part tokens

        Returns:
            List of candidates
        """
        candidates = []

        # Part number match
        part_numbers = parts.get('part_number', [])
        for pn in part_numbers:
            try:
                result = self.supabase.table('pms_parts').select(
                    'id, name, part_number, manufacturer, quantity_on_hand'
                ).eq('yacht_id', yacht_id).ilike(
                    'part_number', f'%{pn}%'
                ).execute()

                for row in result.data or []:
                    candidates.append({
                        'object_type': 'part',
                        'object_id': row['id'],
                        'label': f"{row['name']} (P/N: {row['part_number']})",
                        'match_reason': 'part_number_match',
                        'score': 70,
                        'manufacturer': row.get('manufacturer'),
                        'quantity': row.get('quantity_on_hand'),
                    })

            except Exception as e:
                logger.error(f"[CandidateFinder] Part number search error: {e}")

        # OEM number match
        oem_numbers = parts.get('oem_number', [])
        for oem in oem_numbers:
            try:
                # Search in metadata or alternate part numbers if available
                result = self.supabase.table('pms_parts').select(
                    'id, name, part_number, manufacturer'
                ).eq('yacht_id', yacht_id).ilike(
                    'part_number', f'%{oem}%'
                ).execute()

                for row in result.data or []:
                    # Don't duplicate
                    if not any(c['object_id'] == row['id'] for c in candidates):
                        candidates.append({
                            'object_type': 'part',
                            'object_id': row['id'],
                            'label': f"{row['name']} (OEM: {oem})",
                            'match_reason': 'oem_number_match',
                            'score': 60,
                        })

            except Exception as e:
                logger.error(f"[CandidateFinder] OEM number search error: {e}")

        return candidates

    # ==========================================================================
    # Phase 7g: Vendor Candidates
    # ==========================================================================

    async def find_vendor_candidates(
        self,
        yacht_id: str,
        vendor: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find vendor candidates by email hash or domain.

        Args:
            yacht_id: Yacht ID
            vendor: Vendor signals

        Returns:
            List of candidates
        """
        candidates = []

        # Skip if no vendor info
        if not vendor:
            return candidates

        # Email hash match (stronger)
        sender_hash = vendor.get('sender_hash')
        if sender_hash:
            try:
                result = self.supabase.table('vendors').select(
                    'id, name, category, email'
                ).eq('yacht_id', yacht_id).eq(
                    'email_hash', sender_hash
                ).execute()

                for row in result.data or []:
                    candidates.append({
                        'object_type': 'vendor',
                        'object_id': row['id'],
                        'label': f"{row['name']} ({row.get('category', 'Vendor')})",
                        'match_reason': 'vendor_email_match',
                        'score': 45,
                        'category': row.get('category'),
                    })

            except Exception as e:
                logger.error(f"[CandidateFinder] Vendor email search error: {e}")

        # Domain match (weaker, only if no email match)
        sender_domain = vendor.get('sender_domain')
        is_personal = vendor.get('is_personal_domain', False)

        if sender_domain and not candidates and not is_personal:
            try:
                result = self.supabase.table('vendors').select(
                    'id, name, category, domain'
                ).eq('yacht_id', yacht_id).eq(
                    'domain', sender_domain
                ).execute()

                for row in result.data or []:
                    candidates.append({
                        'object_type': 'vendor',
                        'object_id': row['id'],
                        'label': f"{row['name']} ({row.get('category', 'Vendor')})",
                        'match_reason': 'vendor_domain_match',
                        'score': 30,
                        'category': row.get('category'),
                    })

            except Exception as e:
                logger.error(f"[CandidateFinder] Vendor domain search error: {e}")

        return candidates

    async def find_open_work_orders_by_equipment(
        self,
        yacht_id: str,
        equipment_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find open work orders related to specific equipment.

        Args:
            yacht_id: Yacht ID
            equipment_id: Equipment ID

        Returns:
            List of related work orders
        """
        try:
            result = self.supabase.table('pms_work_orders').select(
                'id, wo_number, title, status, updated_at'
            ).eq('yacht_id', yacht_id).eq(
                'equipment_id', equipment_id
            ).eq('status', 'open').execute()

            return [{
                'object_type': 'work_order',
                'object_id': row['id'],
                'label': f"WO-{row['wo_number']}: {row['title']}",
                'match_reason': 'equipment_wo_link',
                'score': 35,
                'status': row.get('status'),
            } for row in result.data or []]

        except Exception as e:
            logger.error(f"[CandidateFinder] Equipment WO search error: {e}")
            return []

    # ==========================================================================
    # L2.5: Hybrid Search Index Candidates
    # ==========================================================================

    async def find_search_index_candidates(
        self,
        yacht_id: str,
        query_text: str,
        query_embedding: Optional[List[float]] = None,
        role: Optional[str] = None,
        object_types: Optional[List[str]] = None,
        days_back: int = 365,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        L2.5: Find candidates from search_index using hybrid fusion.

        Calls match_link_targets RPC which:
        - Text: ts_rank_cd on search_index.tsv
        - Vector: cosine similarity on search_index.embedding (1536)
        - Recency: exponential decay (90-day half-life)
        - Bias: role-based weights from search_role_bias

        Args:
            yacht_id: Yacht ID for isolation
            query_text: Text query (subject + top entities from email)
            query_embedding: Optional 1536-dim GPT embedding
            role: Optional user role for bias weighting
            object_types: Optional filter ['work_order', 'equipment', 'part', ...]
            days_back: Recency window in days (default: 365)
            limit: Max candidates to return (default: 20)

        Returns:
            List of candidates with score_inputs for fusion scoring
        """
        candidates = []

        try:
            # Call match_link_targets RPC
            result = self.supabase.rpc('match_link_targets', {
                'p_yacht_id': yacht_id,
                'p_query': query_text,
                'p_query_embedding': query_embedding,
                'p_object_types': object_types,
                'p_role': role,
                'p_days_back': days_back,
                'p_limit': limit
            }).execute()

            # Map RPC results to candidate format
            for row in result.data or []:
                candidates.append({
                    'object_type': row['object_type'],
                    'object_id': row['object_id'],
                    'label': row['label'],
                    'match_reason': 'hybrid_search_index',
                    'score': 0,  # Will be computed by ScoringEngine from score_inputs
                    'score_inputs': {
                        's_text': float(row['s_text']),
                        's_vector': float(row['s_vector']),
                        's_recency': float(row['s_recency']),
                        's_bias': float(row['s_bias']),
                        'rank_text': int(row['rank_text']),
                        'rank_vector': int(row['rank_vector']),
                    },
                    'payload': row.get('payload', {}),
                })

            logger.info(f"[CandidateFinder] L2.5 Hybrid: Found {len(candidates)} candidates for query_text={query_text[:50]}...")

        except Exception as e:
            logger.error(f"[CandidateFinder] L2.5 Hybrid search error: {e}")

        return candidates


# Export
__all__ = ['CandidateFinder']
