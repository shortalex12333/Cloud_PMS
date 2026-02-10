"""
Pipeline V1 - Unified Search Pipeline
=====================================

Integrates the 4 stages from best-of-breed branches:

STAGE 1: EXTRACTION (entity-extraction-api)
    orchestrator.py → text_cleaner → regex_extractor → coverage_controller → ai_extractor → entity_merger

STAGE 2: PREPARE (prepare-module)
    capability_composer.py → maps entities to capabilities → builds execution plans

STAGE 3: EXECUTE (prepare-module + deploy/microactions)
    capability_executor.py + table_capabilities.py → secure SQL execution

STAGE 4: MICROACTIONS (prepare-module + frontend-microactions)
    action_gating.py + action_registry.py → attach available actions to results

USAGE:
    from pipeline_v1 import Pipeline, search

    # Simple usage
    results = search(supabase_client, yacht_id, "inventory in deck 1")

    # Full pipeline control
    pipeline = Pipeline(supabase_client, yacht_id)
    response = pipeline.search("parts for main engine")
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Vector fallback imports (Fix #5: Zero-entity semantic search - 2026-02-02)
from gpt_extractor import GPTExtractor
from integrations.supabase import vector_search

logger = logging.getLogger(__name__)


@dataclass
class PipelineResponse:
    """Response from the unified pipeline."""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    available_actions: List[Dict[str, Any]]

    # Stage outputs for debugging
    extraction: Dict[str, Any] = field(default_factory=dict)
    prepare: Dict[str, Any] = field(default_factory=dict)
    execute: Dict[str, Any] = field(default_factory=dict)

    # Grouped results by domain (NEW)
    results_by_domain: Dict[str, Any] = field(default_factory=dict)

    # Metrics
    extraction_ms: float = 0.0
    prepare_ms: float = 0.0
    execute_ms: float = 0.0
    total_ms: float = 0.0

    # Error handling
    error: Optional[str] = None
    failed_stage: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "query": self.query,
            "results": self.results,
            "total_count": self.total_count,
            "available_actions": self.available_actions,
            "results_by_domain": self.results_by_domain,
            "metadata": {
                "extraction_ms": self.extraction_ms,
                "prepare_ms": self.prepare_ms,
                "execute_ms": self.execute_ms,
                "total_ms": self.total_ms,
                "extraction": self.extraction,
                "prepare": self.prepare,
                "execute": self.execute,
            },
            "error": self.error,
            "failed_stage": self.failed_stage,
        }


class Pipeline:
    """
    Unified search pipeline integrating extraction → prepare → execute → actions.

    This is the single entry point for all search queries.
    """

    def __init__(self, supabase_client, yacht_id: str):
        """
        Initialize the pipeline.

        Args:
            supabase_client: Supabase client instance
            yacht_id: UUID of the yacht (required for all queries)
        """
        self.client = supabase_client
        self.yacht_id = yacht_id

        # Lazy-load modules to avoid circular imports
        self._extractor = None
        self._composer = None
        self._executor = None
        self._microaction_registry = None
        self._gpt_extractor = None  # For embedding generation (vector fallback)

        # Initialize microaction registry for lens-based action suggestions
        try:
            from microactions.microaction_registry import MicroactionRegistry
            self._microaction_registry = MicroactionRegistry(self.client)
            self._microaction_registry.discover_and_register()
            logger.info("✅ MicroactionRegistry initialized")
        except Exception as e:
            logger.warning(f"MicroactionRegistry not available: {e}. Microactions disabled.")

    def _get_extractor(self):
        """Lazy-load extraction orchestrator."""
        if self._extractor is None:
            from extraction.orchestrator import ExtractionOrchestrator
            self._extractor = ExtractionOrchestrator()
        return self._extractor

    def _get_executor(self):
        """Lazy-load capability executor."""
        if self._executor is None:
            from execute.capability_executor import CapabilityExecutor
            self._executor = CapabilityExecutor(self.client, self.yacht_id)
        return self._executor

    def _get_gpt_extractor(self):
        """Lazy-load GPT extractor for embedding generation."""
        if self._gpt_extractor is None:
            self._gpt_extractor = GPTExtractor()
        return self._gpt_extractor

    async def _vector_fallback(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fix #5: Vector search fallback when entity extraction yields zero entities.

        When we can't extract any entities from the query, we fall back to
        semantic vector search against document chunks. This handles:
        - Completely unknown terms (not in gazetteer or fuzzy match)
        - Heavily misspelled queries
        - Queries in other languages
        - Very vague natural language queries

        Args:
            query: The original user query
            limit: Max results to return

        Returns:
            Dict with vector search results and metadata
        """
        try:
            # Generate embedding for the query
            start = time.time()
            gpt = self._get_gpt_extractor()
            query_embedding = gpt.embed(query)
            embed_ms = (time.time() - start) * 1000

            # Perform vector search
            start = time.time()
            results = await vector_search(
                yacht_id=self.yacht_id,
                query_embedding=query_embedding,
                limit=limit
            )
            search_ms = (time.time() - start) * 1000

            logger.info(f"Vector fallback: query='{query}', results={len(results)}, "
                       f"embed_ms={embed_ms:.1f}, search_ms={search_ms:.1f}")

            return {
                'success': True,
                'fallback_type': 'vector_search',
                'results': results,
                'count': len(results),
                'embed_ms': embed_ms,
                'search_ms': search_ms,
            }

        except Exception as e:
            logger.error(f"Vector fallback failed: {e}")
            return {
                'success': False,
                'fallback_type': 'vector_search',
                'results': [],
                'count': 0,
                'error': str(e),
            }

    async def _text_search_fallback(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fix #6: Text-based search fallback when embeddings not populated.

        When vector search returns empty (because embeddings don't exist yet),
        fall back to basic text matching on filename and tags. This provides
        degraded search functionality until embeddings are generated.

        Args:
            query: The original user query
            limit: Max results to return

        Returns:
            Dict with text search results and metadata
        """
        try:
            start = time.time()

            # Query doc_metadata directly with text matching
            response = self.client.table('doc_metadata') \
                .select('id, filename, storage_path, yacht_id, document_type, tags') \
                .eq('yacht_id', self.yacht_id) \
                .is_('deleted_at', 'null') \
                .or_(f'filename.ilike.%{query}%,tags.cs.{{"{query}"}}') \
                .limit(limit) \
                .execute()

            search_ms = (time.time() - start) * 1000

            # Transform to pipeline result format
            results = []
            for doc in (response.data or []):
                results.append({
                    'document_id': doc['id'],
                    'title': doc['filename'],
                    'storage_path': doc.get('storage_path', ''),
                    'document_type': doc.get('document_type', 'unknown'),
                    'score': 0.5,  # Fixed score for text match
                    'source': 'text_search',
                })

            logger.info(f"Text fallback: query='{query}', results={len(results)}, "
                       f"search_ms={search_ms:.1f}")

            return {
                'success': True,
                'fallback_type': 'text_search',
                'results': results,
                'count': len(results),
                'search_ms': search_ms,
            }

        except Exception as e:
            logger.error(f"Text fallback failed: {e}")
            return {
                'success': False,
                'fallback_type': 'text_search',
                'results': [],
                'count': 0,
                'error': str(e),
            }

    async def search(self, query: str, limit: int = 20) -> PipelineResponse:
        """
        Execute a search query through the full pipeline (async).

        Args:
            query: Natural language query
            limit: Maximum results per capability

        Returns:
            PipelineResponse with results and metadata
        """
        start_total = time.time()
        response = PipelineResponse(
            success=False,
            query=query,
            results=[],
            total_count=0,
            available_actions=[],
        )

        try:
            # ================================================================
            # STAGE 1: EXTRACTION
            # ================================================================
            start = time.time()
            extraction_result = await self._extract(query)
            response.extraction_ms = (time.time() - start) * 1000
            response.extraction = extraction_result

            entities = extraction_result.get('entities', [])
            if not entities:
                # ================================================================
                # FIX #5: VECTOR FALLBACK (2026-02-02)
                # No entities extracted - try semantic vector search
                # ================================================================
                logger.info(f"Zero entities for '{query}' - trying vector fallback")
                vector_result = await self._vector_fallback(query, limit)

                if vector_result.get('success') and vector_result.get('results'):
                    # Vector search found results
                    response.success = True
                    response.results = vector_result['results']
                    response.total_count = vector_result['count']
                    response.extraction['fallback'] = vector_result
                    response.error = None  # Clear error - we found results via fallback
                    logger.info(f"Vector fallback returned {vector_result['count']} results")
                else:
                    # Vector search returned empty - try text-based fallback
                    logger.warning(f"Vector search empty - trying text fallback for '{query}'")
                    text_result = await self._text_search_fallback(query, limit)

                    if text_result.get('success') and text_result.get('results'):
                        # Text search found results
                        response.success = True
                        response.results = text_result['results']
                        response.total_count = text_result['count']
                        response.extraction['fallback'] = text_result
                        response.error = "Using text search (embeddings not populated)"
                        logger.info(f"Text fallback returned {text_result['count']} results")
                    else:
                        # All fallbacks failed - return empty
                        response.success = True
                        response.error = "No entities extracted and all search fallbacks returned no results"
                        logger.info(f"All search fallbacks returned no results")

                response.total_ms = (time.time() - start_total) * 1000
                return response

            # ================================================================
            # STAGE 2: PREPARE
            # ================================================================
            start = time.time()
            prepare_result = self._prepare(entities)
            response.prepare_ms = (time.time() - start) * 1000
            response.prepare = prepare_result

            plans = prepare_result.get('plans', [])
            if not plans:
                response.success = True
                response.error = "No capabilities matched the extracted entities"
                response.total_ms = (time.time() - start_total) * 1000
                return response

            # ================================================================
            # STAGE 3: EXECUTE
            # ================================================================
            start = time.time()
            execute_result = self._execute(plans, limit)
            response.execute_ms = (time.time() - start) * 1000
            response.execute = execute_result

            raw_results = execute_result.get('results', [])

            # ================================================================
            # STAGE 4: NORMALIZE RESULTS
            # ================================================================
            # Transform raw database rows into frontend-expected format
            start = time.time()
            normalized_results = self._normalize_results(raw_results)
            normalize_ms = (time.time() - start) * 1000
            logger.info(f"Normalization completed in {normalize_ms:.2f}ms")

            # ================================================================
            # STAGE 5: RANK RESULTS
            # ================================================================
            start = time.time()
            ranked_results = self._rank_results(normalized_results, query, entities)
            rank_ms = (time.time() - start) * 1000
            logger.info(f"Ranking completed in {rank_ms:.2f}ms")

            response.results = ranked_results
            response.total_count = len(ranked_results)

            # ================================================================
            # STAGE 6: ENRICH RESULTS WITH MICROACTIONS
            # ================================================================
            start = time.time()
            enriched_results = await self._enrich_results_with_microactions(
                ranked_results,
                user_role="chief_engineer",  # TODO: Get from auth context
                query_intent="general_search"  # TODO: Derive from query/entities
            )
            microaction_ms = (time.time() - start) * 1000
            logger.info(f"Microaction enrichment completed in {microaction_ms:.2f}ms")

            response.results = enriched_results
            response.total_count = len(enriched_results)

            # ================================================================
            # STAGE 7: ATTACH ACTIONS (Global Action List)
            # ================================================================
            response.available_actions = self._get_available_actions(plans)

            # ================================================================
            # STAGE 8: GROUP RESULTS BY DOMAIN
            # ================================================================
            response.results_by_domain = self._group_by_domain(enriched_results)

            # ================================================================
            # STAGE 9: TRANSLATE ENTITY TYPES FOR FRONTEND
            # ================================================================
            # Backend uses specific extraction types (EQUIPMENT_NAME, PART_NUMBER)
            # for capability mapping. Translate to frontend domain types (equipment,
            # part) for card rendering and action surfacing.
            if response.extraction.get('entities'):
                response.extraction['entities'] = self._translate_entity_types_for_frontend(
                    response.extraction['entities']
                )

            response.success = True
            response.total_ms = (time.time() - start_total) * 1000

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            response.error = str(e)
            response.total_ms = (time.time() - start_total) * 1000

        return response

    async def _extract(self, query: str) -> Dict[str, Any]:
        """
        Stage 1: Extract entities from query (async).

        Uses the 5-stage extraction pipeline:
        clean → regex → coverage check → AI (conditional) → merge
        """
        try:
            extractor = self._get_extractor()
            result = await extractor.extract(query)

            # Normalize entity format for downstream stages
            # Orchestrator returns: {'entities': {'location_on_board': ['Deck'], 'equipment': ['Pump']}}
            entities = []
            raw_entities = result.get('entities', {})

            if isinstance(raw_entities, dict):
                # Handle dict format: {entity_type: [values]}
                for entity_type, values in raw_entities.items():
                    if not isinstance(values, list):
                        values = [values]
                    for value in values:
                        # Normalize entity type to match capability mapping
                        normalized_type = self._normalize_entity_type(entity_type)
                        entities.append({
                            'type': normalized_type,
                            'value': value,
                            'confidence': 0.8,
                        })
            elif isinstance(raw_entities, list):
                # Handle list format (legacy or alternate)
                for entity in raw_entities:
                    if hasattr(entity, 'type'):
                        entities.append({
                            'type': entity.type.upper(),
                            'value': entity.text,
                            'confidence': getattr(entity, 'confidence', 0.8),
                        })
                    elif isinstance(entity, dict):
                        entities.append({
                            'type': entity.get('type', 'UNKNOWN').upper(),
                            'value': entity.get('text', entity.get('value', '')),
                            'confidence': entity.get('confidence', 0.8),
                        })

            # Inventory Lens: Refine STOCK_STATUS entities into specific types based on value
            # When AI extracts stock_status: ["low stock"], convert to LOW_STOCK entity
            inventory_entities = []
            for entity in entities[:]:  # Iterate over copy to allow modification
                entity_type = entity.get('type', '')
                entity_value = entity.get('value', '').lower()
                entity_conf = entity.get('confidence', 0.8)

                if entity_type == 'STOCK_STATUS':
                    # Map stock status values to specific entity types
                    if any(keyword in entity_value for keyword in ['low stock', 'low', 'below minimum', 'critically low']):
                        inventory_entities.append({
                            'type': 'LOW_STOCK',
                            'value': entity.get('value'),
                            'confidence': entity_conf,
                            'source': 'inventory_lens_transformation',
                        })
                    elif any(keyword in entity_value for keyword in ['out of stock', 'out', 'no stock', 'zero']):
                        inventory_entities.append({
                            'type': 'OUT_OF_STOCK',
                            'value': entity.get('value'),
                            'confidence': entity_conf,
                            'source': 'inventory_lens_transformation',
                        })
                    elif any(keyword in entity_value for keyword in ['reorder', 'needs reorder', 'order']):
                        inventory_entities.append({
                            'type': 'REORDER_NEEDED',
                            'value': entity.get('value'),
                            'confidence': entity_conf,
                            'source': 'inventory_lens_transformation',
                        })

            # Add inventory entities to the list
            entities.extend(inventory_entities)

            # Work Order Lens: Create additional entities for work order title/description search
            # When equipment or action entities are extracted, also search work orders that mention them
            work_order_entities = []
            for entity in entities:
                entity_type = entity.get('type', '')
                entity_value = entity.get('value', '')

                # Equipment entities (e.g., "generator") should also search work order titles/descriptions
                if entity_type == 'EQUIPMENT_NAME':
                    work_order_entities.append({
                        'type': 'WORK_ORDER_EQUIPMENT',
                        'value': entity_value,
                        'confidence': entity.get('confidence', 0.8) * 0.9,  # Slightly lower confidence for cross-lens search
                        'source': 'work_order_lens_transformation',
                    })

                # Action entities related to maintenance (e.g., "maintenance", "service", "repair")
                # should search work order titles
                elif entity_type in ['ACTION', 'MAINTENANCE_ACTION']:
                    maintenance_keywords = {'maintenance', 'service', 'repair', 'change', 'replace', 'inspect', 'check'}
                    if entity_value.lower() in maintenance_keywords:
                        work_order_entities.append({
                            'type': 'WORK_ORDER_TITLE',
                            'value': entity_value,
                            'confidence': entity.get('confidence', 0.8) * 0.85,  # Lower confidence for action-based search
                            'source': 'work_order_lens_transformation',
                        })

            # Add work order entities to the list
            entities.extend(work_order_entities)

            # Shopping List Lens: Create shopping list entities when context indicates procurement/ordering
            # Detects shopping list queries and transforms generic entities into shopping list-specific types
            shopping_list_entities = []
            # Expanded keywords to catch paraphrases and common misspellings
            shopping_list_keywords = {
                'shopping list', 'shoping list', 'shop list',  # Common misspellings
                'procurement', 'procure',
                'order', 'ordering',
                'purchase', 'purchasing',
                'request', 'requested', 'requesting',
                'approve', 'approval', 'approved', 'approving',
                'reject', 'rejected', 'rejecting',
                'waiting', 'pending',
                'priority', 'urgent', 'critical',
                'add', 'adding', 'create',
                'candidate', 'parts list',
            }
            query_lower = query.lower()
            # Check keywords or partial match for "shop" + "list" to catch more misspellings
            is_shopping_list_context = (
                any(keyword in query_lower for keyword in shopping_list_keywords) or
                ('shop' in query_lower and 'list' in query_lower)
            )

            if is_shopping_list_context:
                for entity in entities:
                    entity_type = entity.get('type', '')
                    entity_value = entity.get('value', '').lower()
                    entity_conf = entity.get('confidence', 0.8)

                    # Status words in shopping list context → APPROVAL_STATUS
                    status_keywords = {'pending', 'approved', 'rejected', 'under review', 'candidate', 'waiting', 'approval'}
                    if entity_type in ['SYMPTOM', 'STATUS', 'OPERATIONAL_STATE'] and entity_value in status_keywords:
                        shopping_list_entities.append({
                            'type': 'APPROVAL_STATUS',
                            'value': entity_value,
                            'confidence': entity_conf * 0.95,
                            'source': 'shopping_list_lens_transformation',
                        })

                    # Urgency indicators → URGENCY_LEVEL
                    urgency_keywords = {'urgent', 'critical', 'asap', 'high', 'low', 'normal', 'priority'}
                    if any(keyword in entity_value for keyword in urgency_keywords):
                        shopping_list_entities.append({
                            'type': 'URGENCY_LEVEL',
                            'value': entity_value,
                            'confidence': entity_conf * 0.9,
                            'source': 'shopping_list_lens_transformation',
                        })

                    # Part names in shopping list context → REQUESTED_PART
                    if entity_type in ['PART_NAME', 'EQUIPMENT_NAME', 'VESSEL_EQUIPMENT']:
                        shopping_list_entities.append({
                            'type': 'REQUESTED_PART',
                            'value': entity.get('value', ''),  # Preserve original casing
                            'confidence': entity_conf * 0.9,
                            'source': 'shopping_list_lens_transformation',
                        })

                    # Source type indicators → SOURCE_TYPE
                    source_keywords = {'manual', 'inventory', 'work order', 'receiving', 'damaged'}
                    if any(keyword in entity_value for keyword in source_keywords):
                        shopping_list_entities.append({
                            'type': 'SOURCE_TYPE',
                            'value': entity_value,
                            'confidence': entity_conf * 0.85,
                            'source': 'shopping_list_lens_transformation',
                        })

                # If no specific entities but shopping list keywords present, create generic SHOPPING_LIST_ITEM
                if not shopping_list_entities and is_shopping_list_context:
                    shopping_list_entities.append({
                        'type': 'SHOPPING_LIST_ITEM',
                        'value': 'shopping list',
                        'confidence': 0.75,
                        'source': 'shopping_list_lens_transformation',
                    })

            # Add shopping list entities to the list
            entities.extend(shopping_list_entities)

            # Receiving Lens: Transform generic entities in receiving context
            # Detects receiving/PO/invoice queries and transforms org → SUPPLIER_NAME
            receiving_entities = []
            receiving_keywords = {
                'receiving', 'recieving', 'reciving',  # Common misspellings
                'receive', 'received',
                'delivery', 'delivered',
                'supplier', 'vendor',
                'invoice', 'invoices',
                'po', 'purchase order', 'p.o.', 'p/o',
                'shipment', 'shipped',
                'goods received',
            }
            is_receiving_context = any(keyword in query_lower for keyword in receiving_keywords)

            if is_receiving_context:
                for entity in entities:
                    entity_type = entity.get('type', '')
                    entity_value = entity.get('value', '')
                    entity_conf = entity.get('confidence', 0.8)

                    # ORG/BRAND entities in receiving context → SUPPLIER_NAME
                    # Fix: Use lowercase comparison (entity extraction returns lowercase types)
                    # Fix: Add 'brand' - Racor, Caterpillar extracted as 'brand' not 'org'
                    if entity_type.lower() in ['org', 'brand', 'manufacturer', 'organization']:
                        receiving_entities.append({
                            'type': 'SUPPLIER_NAME',
                            'value': entity_value,
                            'confidence': entity_conf * 0.95,
                            'source': 'receiving_lens_transformation',
                        })

                    # Status words in receiving context → RECEIVING_STATUS
                    # Fix: Use lowercase comparison (entity extraction returns lowercase types)
                    status_keywords = {'draft', 'in review', 'accepted', 'rejected', 'pending', 'approved'}
                    if entity_type.lower() in ['symptom', 'status', 'operational_state'] and entity_value.lower() in status_keywords:
                        receiving_entities.append({
                            'type': 'RECEIVING_STATUS',
                            'value': entity_value,
                            'confidence': entity_conf * 0.9,
                            'source': 'receiving_lens_transformation',
                        })

            # Add receiving entities to the list
            entities.extend(receiving_entities)

            return {
                'entities': entities,
                'unknown_terms': result.get('unknown_term', []),
                'source_mix': result.get('source_mix', {}),
                'timings': result.get('metadata', {}).get('timings', {}),
            }

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {'entities': [], 'error': str(e)}

    def _normalize_entity_type(self, entity_type: str) -> str:
        """
        Normalize entity type from extraction format to capability mapping format.

        Extraction returns: location_on_board, equipment, po_number
        Capabilities expect: LOCATION, EQUIPMENT_NAME, PART_NUMBER

        See ENTITY_TO_SEARCH_COLUMN in prepare/capability_composer.py for valid types.
        """
        type_mapping = {
            # Location types
            'location_on_board': 'LOCATION',
            'location': 'LOCATION',
            # Equipment types
            'equipment': 'EQUIPMENT_NAME',
            'equipment_name': 'EQUIPMENT_NAME',
            'equipment_type': 'EQUIPMENT_TYPE',
            'product_name': 'EQUIPMENT_NAME',  # "Perkins AC" extracted as PRODUCT_NAME
            # Part types
            'part_number': 'PART_NUMBER',
            'part_name': 'PART_NAME',
            'manufacturer': 'MANUFACTURER',
            # Fault types
            'fault_code': 'FAULT_CODE',
            'model': 'FAULT_CODE',  # "E122" extracted as MODEL
            'symptom': 'SYMPTOM',
            'status': 'SYMPTOM',  # "fault", "error" extracted as STATUS
            # Work order types
            'work_order': 'WORK_ORDER_ID',
            'wo_number': 'WO_NUMBER',
            # Document types
            'document': 'DOCUMENT_QUERY',
            'document_type': 'DOCUMENT_QUERY',  # "manual" extracted as DOCUMENT_TYPE
            'manual': 'MANUAL_SEARCH',
            'procedure': 'PROCEDURE_SEARCH',
            # Graph types
            'system': 'SYSTEM_NAME',
            'system_name': 'SYSTEM_NAME',
            'component': 'COMPONENT_NAME',
            'component_name': 'COMPONENT_NAME',
            'subcomponent': 'PART_NAME',  # Subcomponents are searchable as parts
            # Email types
            'email_search': 'EMAIL_SEARCH',
            'email': 'EMAIL_SEARCH',
            'email_subject': 'EMAIL_SUBJECT',
            # Receiving Lens types (PR #47 - Receiving Lens)
            # FIX: po_number maps to PO_NUMBER for receiving, not PART_NUMBER
            'po_number': 'PO_NUMBER',
            'receiving_id': 'RECEIVING_ID',
            'supplier_name': 'SUPPLIER_NAME',
            'invoice_number': 'INVOICE_NUMBER',
            'delivery_date': 'DELIVERY_DATE',
            'receiver_name': 'RECEIVER_NAME',
            'receiving_status': 'RECEIVING_STATUS',
            # Shopping List types (context-aware)
            # Note: These are extracted by maritime NER as generic types,
            # but in shopping list context they map to shopping list entity types
            'shopping_list_item': 'SHOPPING_LIST_ITEM',
            'shopping_list': 'SHOPPING_LIST_ITEM',
            'procurement_list': 'SHOPPING_LIST_ITEM',
            'parts_request': 'REQUESTED_PART',
            'request': 'REQUESTED_PART',
            'urgency': 'URGENCY_LEVEL',
            'priority': 'URGENCY_LEVEL',
            'approval_status': 'APPROVAL_STATUS',
            'source': 'SOURCE_TYPE',
            'requester': 'REQUESTER_NAME',
            # Inventory types (PR #44 - Inventory Lens fix)
            'stock_status': 'STOCK_STATUS',
            'low_stock': 'LOW_STOCK',
            'out_of_stock': 'OUT_OF_STOCK',
            'part_category': 'PART_CATEGORY',
            # Crew Lens types (PR #64)
            'rest_compliance': 'REST_COMPLIANCE',
            'warning_severity': 'WARNING_SEVERITY',
            # Work Order Lens types (PR #64)
            'work_order_status': 'WORK_ORDER_STATUS',
            # Receiving Lens types (PR #64)
            'delivery_date': 'DELIVERY_DATE',
            'receiving_status': 'RECEIVING_STATUS',
            # Other
            'date': 'DATE',
            'date_range': 'DATE_RANGE',
            'quantity': 'QUANTITY',
            'stock': 'STOCK_QUERY',
        }
        normalized = entity_type.lower().strip()
        return type_mapping.get(normalized, normalized.upper().replace(' ', '_'))

    def _translate_entity_types_for_frontend(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Translate Lens extraction types to frontend domain types.

        Backend uses specific extraction types (EQUIPMENT_NAME, PART_NUMBER, etc.)
        for capability mapping. Frontend expects simpler domain types (equipment,
        part, fault, etc.) for card rendering and action surfacing.

        This preserves extraction_type for debugging while setting type to
        the frontend-expected value.
        """
        EXTRACTION_TO_FRONTEND = {
            # Parts & Inventory
            'PART_NUMBER': 'part',
            'PART_NAME': 'part',
            'MANUFACTURER': 'part',
            # Part Lens - Brand/Manufacturer types (PR #69)
            'BRAND': 'part',              # From ENTITY_EXTRACTION_EXPORT
            'EQUIPMENT_BRAND': 'part',    # From ENTITY_EXTRACTION_EXPORT
            'ORG': 'part',                # From REGEX_PRODUCTION (fallback)
            'LOCATION': 'inventory',
            'STOCK_QUERY': 'inventory',
            # Inventory - Stock Status (7 new types)
            'STOCK_STATUS': 'inventory',
            'REORDER_NEEDED': 'inventory',
            'CRITICAL_PART': 'inventory',
            'RECENT_USAGE': 'inventory',
            'PART_CATEGORY': 'inventory',
            'LOW_STOCK': 'inventory',
            'OUT_OF_STOCK': 'inventory',
            # Equipment
            'EQUIPMENT_NAME': 'equipment',
            'MODEL_NUMBER': 'equipment',
            'SYSTEM_NAME': 'equipment',
            'COMPONENT_NAME': 'equipment',
            'EQUIPMENT_TYPE': 'equipment',
            # Faults
            'FAULT_CODE': 'fault',
            'SYMPTOM': 'fault',
            # Work Orders
            'WORK_ORDER_ID': 'work_order',
            'WO_NUMBER': 'work_order',
            # Documents
            'DOCUMENT_QUERY': 'document',
            'MANUAL_SEARCH': 'document',
            'PROCEDURE_SEARCH': 'document',
            'EMAIL_SUBJECT': 'email_thread',
            'EMAIL_SEARCH': 'email_thread',
            # Certificates (new)
            'CERTIFICATE_NAME': 'certificate',
            'CERTIFICATE_NUMBER': 'certificate',
            'CERTIFICATE_TYPE': 'certificate',
            'ISSUING_AUTHORITY': 'certificate',
            'VESSEL_CERTIFICATE': 'certificate',
            'CREW_CERTIFICATE': 'certificate',
            'EXPIRY_DATE': 'certificate',
            # Receiving (new)
            'PO_NUMBER': 'receiving',
            'RECEIVING_ID': 'receiving',
            'SUPPLIER_NAME': 'receiving',
            'INVOICE_NUMBER': 'receiving',
            'DELIVERY_DATE': 'receiving',
            'RECEIVER_NAME': 'receiving',
            'RECEIVING_STATUS': 'receiving',
            # Shopping List (new)
            'SHOPPING_LIST_ITEM': 'shopping_list',
            'SHOPPING_LIST_TERM': 'shopping_list',     # From ENTITY_EXTRACTION_EXPORT
            'REQUESTED_PART': 'shopping_list',
            'REQUESTER_NAME': 'shopping_list',
            'URGENCY_LEVEL': 'shopping_list',
            'APPROVAL_STATUS': 'shopping_list',
            'SOURCE_TYPE': 'shopping_list',
            # Crew (new)
            'CREW_NAME': 'crew',
            'CREW_ROLE': 'crew',
            'CREW_ID': 'crew',
            'CERTIFICATION_STATUS': 'crew',
            'WATCHKEEPING_SCHEDULE': 'crew',
            'CREW_QUALIFICATION': 'crew',
            # Crew - Hours of Rest (only types that map to actual columns)
            'REST_COMPLIANCE': 'crew',
            'WARNING_SEVERITY': 'crew',
            'WARNING_STATUS': 'crew',
        }

        translated = []
        for entity in entities:
            extraction_type = entity.get('type', '')
            frontend_type = EXTRACTION_TO_FRONTEND.get(
                extraction_type,
                extraction_type.lower().replace('_', ' ')  # Fallback: lowercase with spaces
            )

            translated_entity = {
                **entity,
                'extraction_type': extraction_type,  # Preserve for debugging
                'type': frontend_type,               # Frontend-friendly type
            }
            translated.append(translated_entity)

        return translated

    async def _enrich_results_with_microactions(
        self,
        results: List[Dict[str, Any]],
        user_role: str = "chief_engineer",
        query_intent: str = "general_search"
    ) -> List[Dict[str, Any]]:
        """
        Enrich search results with lens-based microaction suggestions.

        For each result, queries the MicroactionRegistry to get relevant action
        suggestions based on:
        - Lens type (part_lens, equipment_lens, etc.)
        - Entity type and ID
        - User role
        - Query intent

        Args:
            results: List of search results
            user_role: User's role (captain, chief_engineer, crew)
            query_intent: Search intent (general_search, troubleshoot, etc.)

        Returns:
            Results enriched with 'actions' field containing microaction suggestions
        """
        if not self._microaction_registry:
            logger.debug("Microaction registry not available, skipping enrichment")
            return results

        import asyncio

        async def enrich_result(result: Dict[str, Any]) -> Dict[str, Any]:
            """Enrich a single result with microactions."""
            # Get lens name from result source table
            source_table = result.get('source_table') or result.get('type', '')
            lens_name = self._get_lens_name_from_source_table(source_table)

            if not lens_name:
                result['actions'] = []
                return result

            # Get entity type and ID
            entity_type = self._get_entity_type_from_source_table(source_table)
            entity_id = result.get('primary_id') or result.get('id')

            if not entity_id:
                result['actions'] = []
                return result

            # Get microaction suggestions
            try:
                suggestions = await self._microaction_registry.get_suggestions(
                    lens_name=lens_name,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_data=result,
                    user_role=user_role,
                    yacht_id=self.yacht_id,
                    query_intent=query_intent
                )

                # Convert to dict format
                result['actions'] = [
                    {
                        'action_id': s.action_id,
                        'label': s.label,
                        'variant': s.variant,
                        'priority': s.priority,
                        'prefill_data': s.prefill_data
                    }
                    for s in suggestions
                ]
            except Exception as e:
                logger.warning(f"Failed to get microactions for result {entity_id}: {e}")
                result['actions'] = []

            return result

        # Run async enrichment
        try:
            enriched_results = await asyncio.gather(*[enrich_result(result) for result in results])
            return list(enriched_results)
        except Exception as e:
            logger.error(f"Failed to enrich results with microactions: {e}")
            # Return results without enrichment if anything fails
            for result in results:
                if 'actions' not in result:
                    result['actions'] = []
            return results

    def _get_lens_name_from_source_table(self, source_table: str) -> Optional[str]:
        """Map source table to lens name."""
        table_to_lens = {
            'pms_parts': 'part_lens',
            'part': 'part_lens',
            'crew': 'crew_lens',
            'pms_crew': 'crew_lens',
            'certificates': 'certificate_lens',
            'pms_equipment': 'equipment_lens',
            'equipment': 'equipment_lens',
            'pms_work_orders': 'work_order_lens',
            'work_order': 'work_order_lens',
            'receiving': 'receiving_lens',
            'shopping_list': 'shopping_list_lens',
            'documents': 'document_lens',
        }
        return table_to_lens.get(source_table)

    def _get_entity_type_from_source_table(self, source_table: str) -> str:
        """Map source table to entity type for microaction lookup."""
        table_to_entity = {
            'pms_parts': 'part',
            'part': 'part',
            'crew': 'crew_member',
            'pms_crew': 'crew_member',
            'certificates': 'certificate',
            'pms_equipment': 'equipment',
            'equipment': 'equipment',
            'pms_work_orders': 'work_order',
            'work_order': 'work_order',
            'receiving': 'receiving_item',
            'shopping_list': 'shopping_list_item',
            'documents': 'document',
        }
        return table_to_entity.get(source_table, source_table)

    def _prepare(self, entities: List[Dict]) -> Dict[str, Any]:
        """
        Stage 2: Map entities to capability execution plans.

        Uses capability_composer to:
        1. Map entity types to capabilities
        2. Build execution plans with search columns
        3. Identify blocked capabilities
        """
        try:
            from prepare.capability_composer import plan_capabilities, ENTITY_TO_SEARCH_COLUMN
            from execute.table_capabilities import get_active_capabilities

            # DEBUG: Collect diagnostic info
            entity_types = [e.get('type') for e in entities]
            active_caps = get_active_capabilities()
            mappings_for_entities = {
                et: ENTITY_TO_SEARCH_COLUMN.get(et)
                for et in entity_types
            }

            plans = plan_capabilities(entities)

            return {
                'plans': [
                    {
                        'capability': p.capability_name,
                        'entity_type': p.entity_type,
                        'entity_value': p.entity_value,
                        'search_column': p.search_column,
                        'blocked': p.blocked,
                        'blocked_reason': p.blocked_reason,
                    }
                    for p in plans
                ],
                'active_plans': [p for p in plans if not p.blocked],
                'blocked_plans': [p for p in plans if p.blocked],
                # DEBUG INFO
                'debug': {
                    'entity_count': len(entities),
                    'entity_types': entity_types,
                    'total_mappings': len(ENTITY_TO_SEARCH_COLUMN),
                    'mappings_for_entities': mappings_for_entities,
                    'active_capabilities_count': len(active_caps),
                    'inventory_by_location_active': 'inventory_by_location' in active_caps,
                    'plans_returned': len(plans),
                },
            }

        except Exception as e:
            logger.error(f"Prepare failed: {e}")
            import traceback
            return {'plans': [], 'error': str(e), 'traceback': traceback.format_exc()}

    def _execute(self, plans: List[Dict], limit: int) -> Dict[str, Any]:
        """
        Stage 3: Execute capability queries.

        Uses capability_executor for secure SQL generation.
        """
        try:
            executor = self._get_executor()
            all_results = []
            execution_details = []

            for plan in plans:
                if plan.get('blocked'):
                    continue

                search_terms = {plan['search_column']: plan['entity_value']}

                result = executor.execute(
                    plan['capability'],
                    search_terms,
                    limit=limit
                )

                execution_details.append({
                    'capability': plan['capability'],
                    'success': result.success,
                    'row_count': result.row_count,
                    'execution_time_ms': result.execution_time_ms,
                    'error': result.error,
                })

                if result.success and result.rows:
                    all_results.extend(result.rows)

            return {
                'results': all_results,
                'execution_details': execution_details,
            }

        except Exception as e:
            logger.error(f"Execute failed: {e}")
            return {'results': [], 'error': str(e)}

    def _normalize_results(
        self,
        raw_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 4: Normalize raw database rows into frontend-expected format.

        Transforms database column names into standardized fields:
        - id: primary key
        - type: source table or entity type
        - title: human-readable name
        - subtitle: secondary info / description
        - preview: full text preview
        - metadata: additional structured data
        """
        normalized = []

        for row in raw_results:
            # Determine ID (try common primary key column names)
            result_id = (
                row.get('id') or
                row.get('primary_id') or
                row.get('stock_id') or
                row.get('chunk_id') or
                str(row.get('uuid', ''))
            )

            # Determine type (from source_table or infer from structure)
            # BUG FIX: Executor sets _source_table (with underscore), check both variants
            result_type = (
                row.get('source_table') or      # Without underscore (legacy/future)
                row.get('_source_table') or     # With underscore (current executor)
                'unknown'                        # Don't default to 'document'!
            )

            # Determine title (try common title-like columns)
            title = (
                row.get('title') or
                row.get('name') or
                row.get('equipment_name') or
                row.get('part_name') or
                row.get('section_title') or
                row.get('code') or
                'Untitled'
            )

            # Determine subtitle/description
            subtitle_parts = []
            if row.get('manufacturer'):
                subtitle_parts.append(f"Manufacturer: {row['manufacturer']}")
            if row.get('category'):
                subtitle_parts.append(f"Category: {row['category']}")
            if row.get('part_number'):
                subtitle_parts.append(f"P/N: {row['part_number']}")
            if row.get('location'):
                subtitle_parts.append(f"Location: {row['location']}")
            if row.get('equipment_type'):
                subtitle_parts.append(f"Type: {row['equipment_type']}")

            subtitle = (
                row.get('subtitle') or
                row.get('snippet') or
                row.get('description') or
                ' | '.join(subtitle_parts) or
                ''
            )

            # Truncate if too long
            if len(subtitle) > 200:
                subtitle = subtitle[:200] + '...'

            # Preview (for longer text content)
            preview = (
                row.get('preview') or
                row.get('content') or
                row.get('text') or
                row.get('searchable_text') or
                ''
            )

            # Build normalized result with canonical fields (Phase 2)
            # Ensure consistency with GraphRAG responses (/v1/search endpoint)
            normalized_result = {
                'id': result_id,                # Backwards compatibility
                'primary_id': result_id,        # PHASE 2: Canonical field name (matches GraphRAG)
                'type': result_type,            # Table name (e.g., "search_document_chunks")
                'source_table': result_type,    # PHASE 2: Top-level canonical field (matches GraphRAG)
                'title': title,
                'subtitle': subtitle,
                'preview': preview[:500] if preview else '',  # Truncate preview
                'score': row.get('score', 0.5),
                'metadata': {
                    'source_table': result_type,  # Backwards compatibility (kept in metadata too)
                    **{k: v for k, v in row.items() if k not in ['id', 'title', 'name', 'content', 'text']}
                },
                'actions': row.get('actions', []),
            }

            normalized.append(normalized_result)

        logger.info(f"Normalized {len(normalized)} results")
        return normalized

    def _rank_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 5: Rank and score results based on match quality, intent, and relevance.

        Uses result_ranker for comprehensive scoring:
        - Match mode hierarchy (EXACT_ID > CANONICAL > FUZZY > VECTOR)
        - Conjunction bonus for multi-entity matches
        - Intent-table priors based on query signals
        - Recency bonus for operational data
        - Noise penalties for low-quality matches
        """
        try:
            from execute.result_ranker import (
                rank_results,
                create_scoring_context,
                group_results_by_domain
            )

            # Create scoring context from query and entities
            context = create_scoring_context(query, entities)

            # Rank results with diversification
            ranked = rank_results(
                results,
                context,
                max_per_table=10,      # Max 10 results from same table
                max_per_parent=3,      # Max 3 chunks from same PDF/work order
            )

            logger.info(f"Ranked {len(ranked)}/{len(results)} results (context: vague={context.is_vague}, diagnostic={context.is_diagnostic}, signals={context.intent_signals})")

            return ranked

        except Exception as e:
            logger.error(f"Ranking failed: {e}", exc_info=True)
            # Fallback: return original results unranked
            return results

    def _get_available_actions(self, plans: List[Dict]) -> List[Dict[str, Any]]:
        """
        Stage 5: Get available actions from executed capabilities.

        Uses table_capabilities to look up available_actions per capability.
        """
        try:
            from execute.table_capabilities import TABLE_CAPABILITIES
            from actions.action_gating import GATED_ACTIONS, STATE_CHANGING_ACTIONS, ExecutionClass

            actions = []
            seen_actions = set()

            for plan in plans:
                if plan.get('blocked'):
                    continue

                cap = TABLE_CAPABILITIES.get(plan['capability'])
                if cap and hasattr(cap, 'available_actions'):
                    for action_id in cap.available_actions:
                        if action_id in seen_actions:
                            continue
                        seen_actions.add(action_id)

                        # Determine execution class
                        if action_id in GATED_ACTIONS:
                            exec_class = ExecutionClass.CONFIRM
                        elif action_id in STATE_CHANGING_ACTIONS:
                            exec_class = ExecutionClass.SUGGEST
                        else:
                            exec_class = ExecutionClass.AUTO

                        actions.append({
                            'action': action_id,
                            'label': action_id.replace('_', ' ').title(),
                            'execution_class': exec_class.value,
                        })

            return actions

        except Exception as e:
            logger.error(f"Get actions failed: {e}")
            return []

    def _group_by_domain(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Stage 6: Group results by capability/domain for frontend display.

        Results are already ranked, so grouping preserves rank order within each domain.

        Returns dict with structure:
        {
            'parts': {'count': 2, 'results': [...], 'source_capability': '...'},
            'inventory': {'count': 1, 'results': [...], 'source_capability': '...'},
            ...
        }
        """
        from collections import defaultdict

        # Map capability names to user-facing domain names
        domain_mapping = {
            'part_by_part_number_or_name': 'parts',
            'inventory_by_location': 'inventory',
            'fault_by_fault_code': 'faults',
            'equipment_by_name_or_model': 'equipment',
            'work_order_by_id': 'work_orders',
            'documents_search': 'documents',
            'graph_node_search': 'systems',
            'email_threads_search': 'emails'
        }

        grouped = defaultdict(lambda: {
            'count': 0,
            'results': [],
            'source_capability': None
        })

        # Group results by their source capability
        for result in results:
            source_capability = result.get('_capability')
            if not source_capability:
                # Fallback if _capability metadata is missing
                continue

            domain = domain_mapping.get(source_capability, 'other')

            grouped[domain]['count'] += 1
            grouped[domain]['results'].append(result)
            grouped[domain]['source_capability'] = source_capability

        return dict(grouped)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def search(supabase_client, yacht_id: str, query: str, limit: int = 20) -> PipelineResponse:
    """
    Convenience function for quick searches.

    Args:
        supabase_client: Supabase client instance
        yacht_id: UUID of the yacht
        query: Natural language query
        limit: Maximum results per capability

    Returns:
        PipelineResponse with results
    """
    pipeline = Pipeline(supabase_client, yacht_id)
    return pipeline.search(query, limit)


def get_pipeline(supabase_client, yacht_id: str) -> Pipeline:
    """
    Get a pipeline instance for repeated searches.

    Args:
        supabase_client: Supabase client instance
        yacht_id: UUID of the yacht

    Returns:
        Pipeline instance
    """
    return Pipeline(supabase_client, yacht_id)


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PIPELINE V1 - Module Structure")
    print("=" * 60)

    print("\n📦 EXTRACTION (from entity-extraction-api):")
    print("   extraction/orchestrator.py - 5-stage coordinator")
    print("   extraction/text_cleaner.py - Input normalization")
    print("   extraction/regex_extractor.py - Deterministic patterns")
    print("   extraction/coverage_controller.py - AI decision gate")
    print("   extraction/ai_extractor_openai.py - GPT fallback")
    print("   extraction/entity_merger.py - Result combination")

    print("\n📦 PREPARE (from prepare-module):")
    print("   prepare/capability_composer.py - Entity → capability mapping")
    print("   prepare/lane_enforcer.py - Lane contracts")

    print("\n📦 EXECUTE (from prepare-module + deploy/microactions):")
    print("   execute/capability_executor.py - Secure SQL generation")
    print("   execute/table_capabilities.py - Capability registry")
    print("   execute/result_normalizer.py - Result normalization")

    print("\n📦 ACTIONS (from prepare-module + frontend-microactions):")
    print("   actions/action_gating.py - Execution class rules")
    print("   actions/action_registry.py - Action definitions")
    print("   actions/action_executor.py - Action handlers")

    print("\n" + "=" * 60)
    print("Usage:")
    print("  from pipeline_v1 import search, Pipeline")
    print("  results = search(supabase, yacht_id, 'inventory in deck 1')")
    print("=" * 60)
