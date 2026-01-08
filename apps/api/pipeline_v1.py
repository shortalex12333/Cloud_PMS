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

    def search(self, query: str, limit: int = 20) -> PipelineResponse:
        """
        Execute a search query through the full pipeline.

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
            extraction_result = self._extract(query)
            response.extraction_ms = (time.time() - start) * 1000
            response.extraction = extraction_result

            entities = extraction_result.get('entities', [])
            if not entities:
                # No entities extracted - return empty with suggestion
                response.success = True
                response.error = "No entities extracted from query"
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
            # STAGE 6: ATTACH ACTIONS
            # ================================================================
            response.available_actions = self._get_available_actions(plans)

            # ================================================================
            # STAGE 7: GROUP RESULTS BY DOMAIN
            # ================================================================
            response.results_by_domain = self._group_by_domain(ranked_results)

            response.success = True
            response.total_ms = (time.time() - start_total) * 1000

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            response.error = str(e)
            response.total_ms = (time.time() - start_total) * 1000

        return response

    def _extract(self, query: str) -> Dict[str, Any]:
        """
        Stage 1: Extract entities from query.

        Uses the 5-stage extraction pipeline:
        clean → regex → coverage check → AI (conditional) → merge
        """
        try:
            extractor = self._get_extractor()
            result = extractor.extract(query)

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
            'po_number': 'PART_NUMBER',
            'part_name': 'PART_NAME',
            'manufacturer': 'MANUFACTURER',
            'org': 'MANUFACTURER',  # "Racor" extracted as ORG
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
            # Other
            'date': 'DATE',
            'date_range': 'DATE_RANGE',
            'quantity': 'QUANTITY',
            'stock': 'STOCK_QUERY',
        }
        normalized = entity_type.lower().strip()
        return type_mapping.get(normalized, normalized.upper().replace(' ', '_'))

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
            }

        except Exception as e:
            logger.error(f"Prepare failed: {e}")
            return {'plans': [], 'error': str(e)}

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
            result_type = row.get('source_table', 'document')

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

            # Build normalized result
            normalized_result = {
                'id': result_id,
                'type': result_type,
                'title': title,
                'subtitle': subtitle,
                'preview': preview[:500] if preview else '',  # Truncate preview
                'score': row.get('score', 0.5),
                'metadata': {
                    'source_table': result_type,
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
            'graph_node_search': 'systems'
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
