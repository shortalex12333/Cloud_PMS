"""
Prepare Module - Deterministic Query Builder
=============================================

The core of the Search Orchestration Layer.

Given:
    - SurfaceContext (state, query, user, yacht)
    - TermClassification (classified terms, path, scopes)
    - Intent family (from intent parser)
    - Extracted entities (from entity extraction)

Produces:
    - RetrievalPlan (queries, filters, ranking recipe, explanation)

This module NEVER executes queries.
It ONLY prepares them.

If this layer is wrong, everything downstream becomes untrustworthy.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from .surface_state import SurfaceContext, SurfaceState, get_default_scopes
from .retrieval_plan import (
    RetrievalPlan,
    RetrievalPath,
    TimeWindow,
    ParameterizedQuery,
    VectorQuery,
    DEFAULT_ROW_LIMITS,
)
from .term_classifier import TermClassifier, TermClassification, TermType
from .email_retrieval import EmailRetrieval
from .ranking_recipes import get_recipe_for_surface

logger = logging.getLogger(__name__)


class PrepareModule:
    """
    Deterministic query builder.
    Converts classification into executable RetrievalPlan.
    """

    def __init__(self):
        self.term_classifier = TermClassifier()
        self.email_retrieval = EmailRetrieval()

    def prepare(
        self,
        context: SurfaceContext,
        extracted_entities: List[Dict[str, Any]] = None,
        intent_family: str = None,
    ) -> RetrievalPlan:
        """
        Main entry point. Build a RetrievalPlan from context.

        Args:
            context: Surface context with query, state, user, yacht
            extracted_entities: Entities from extraction pipeline
            intent_family: Intent from intent parser

        Returns:
            RetrievalPlan ready for execution
        """
        extracted_entities = extracted_entities or []
        plan_id = str(uuid.uuid4())[:8]

        # Step 1: Classify terms
        classification = self.term_classifier.classify(
            context=context,
            extracted_entities=extracted_entities,
            intent_family=intent_family,
        )

        logger.info(f"[Prepare:{plan_id}] Classification: {classification.primary_path.value}, "
                    f"scopes={classification.allowed_scopes}, reason={classification.classification_reason}")

        # Step 2: Route to specialized preparers
        if context.is_email_surface():
            plan = self.email_retrieval.prepare(context, classification.terms)
        elif classification.primary_path == RetrievalPath.SQL_ONLY:
            plan = self._prepare_sql_only(context, classification, extracted_entities)
        elif classification.primary_path == RetrievalPath.VECTOR_ONLY:
            plan = self._prepare_vector_only(context, classification)
        else:  # HYBRID
            plan = self._prepare_hybrid(context, classification, extracted_entities)

        # Step 3: Apply must-filters
        plan.must_filters['yacht_id'] = context.yacht_id
        plan.must_filters['user_id'] = context.user_id

        # Step 4: Set plan metadata
        plan.plan_id = plan_id
        plan.created_at = datetime.utcnow()

        logger.info(f"[Prepare:{plan_id}] Plan ready: path={plan.path.value}, "
                    f"sql_queries={len(plan.sql_queries)}, vector_queries={len(plan.vector_queries)}")

        return plan

    def _prepare_sql_only(
        self,
        context: SurfaceContext,
        classification: TermClassification,
        extracted_entities: List[Dict],
    ) -> RetrievalPlan:
        """
        Prepare SQL-only retrieval plan.
        Used when we have resolved IDs or explicit entity patterns.
        """
        sql_queries = []
        yacht_id = context.yacht_id
        scopes = classification.allowed_scopes

        # Get resolved entity IDs
        entity_ids = [
            (t.resolved_id, t.metadata.get('entity_type', 'unknown'))
            for t in classification.get_entities()
            if t.resolved_id
        ]

        # Get pattern-matched IDs
        pattern_ids = [
            (t.text, t.metadata.get('pattern_type', 'unknown'))
            for t in classification.get_entities()
            if not t.resolved_id
        ]

        # Build queries for each scope
        if 'work_orders' in scopes or not scopes:
            sql_queries.append(self._build_work_order_query(
                yacht_id, entity_ids, pattern_ids, context.query_text
            ))

        if 'equipment' in scopes:
            sql_queries.append(self._build_equipment_query(
                yacht_id, entity_ids, context.query_text
            ))

        if 'parts' in scopes:
            sql_queries.append(self._build_parts_query(
                yacht_id, entity_ids, context.query_text
            ))

        if 'faults' in scopes:
            sql_queries.append(self._build_faults_query(
                yacht_id, entity_ids, context.query_text
            ))

        time_days = classification.time_window_days or 90

        return RetrievalPlan(
            path=RetrievalPath.SQL_ONLY,
            allowed_scopes=scopes,
            time_window=TimeWindow(days=time_days),
            row_limits={s: DEFAULT_ROW_LIMITS.get(s, 30) for s in scopes},
            sql_queries=[q for q in sql_queries if q],
            vector_queries=[],
            ranking_recipe=get_recipe_for_surface(context.surface_state.value),
            explain=f"SQL lookup: {len(entity_ids)} resolved IDs, {len(pattern_ids)} patterns",
            explain_details={
                'resolved_entity_count': len(entity_ids),
                'pattern_entity_count': len(pattern_ids),
                'classification_reason': classification.classification_reason,
            },
        )

    def _prepare_vector_only(
        self,
        context: SurfaceContext,
        classification: TermClassification,
    ) -> RetrievalPlan:
        """
        Prepare vector-only retrieval plan.
        Rare - usually hybrid is preferred.
        """
        query = context.query_text.strip()
        scopes = classification.allowed_scopes
        yacht_id = context.yacht_id

        vector_queries = []

        # Vector search on document chunks
        if 'documents' in scopes or 'document_chunks' in scopes:
            vector_queries.append(VectorQuery(
                table='document_chunks',
                column='embedding',
                input_text=query,
                top_k=30,
                threshold=0.70,
                filters={'yacht_id': yacht_id},
            ))

        # Vector search on equipment (if has embedding column)
        if 'equipment' in scopes:
            vector_queries.append(VectorQuery(
                table='pms_equipment',
                column='embedding',
                input_text=query,
                top_k=20,
                threshold=0.70,
                filters={'yacht_id': yacht_id},
            ))

        time_days = classification.time_window_days or 90

        return RetrievalPlan(
            path=RetrievalPath.VECTOR_ONLY,
            allowed_scopes=scopes,
            time_window=TimeWindow(days=time_days),
            row_limits={s: DEFAULT_ROW_LIMITS.get(s, 30) for s in scopes},
            sql_queries=[],
            vector_queries=vector_queries,
            ranking_recipe=get_recipe_for_surface(context.surface_state.value),
            explain=f"Semantic search: '{query[:50]}...'",
            explain_details={
                'query_preview': query[:100],
                'vector_tables': [v.table for v in vector_queries],
            },
        )

    def _prepare_hybrid(
        self,
        context: SurfaceContext,
        classification: TermClassification,
        extracted_entities: List[Dict],
    ) -> RetrievalPlan:
        """
        Prepare hybrid retrieval plan.
        SQL for filters + vector for semantic ranking.
        """
        yacht_id = context.yacht_id
        query = context.query_text.strip()
        scopes = classification.allowed_scopes

        sql_queries = []
        vector_queries = []

        # SQL queries for structured data
        if 'work_orders' in scopes:
            sql_queries.append(self._build_work_order_query(
                yacht_id, [], [], query
            ))

        if 'equipment' in scopes:
            sql_queries.append(self._build_equipment_query(
                yacht_id, [], query
            ))

        # Vector queries for semantic search
        if 'documents' in scopes or 'document_chunks' in scopes:
            vector_queries.append(VectorQuery(
                table='document_chunks',
                column='embedding',
                input_text=query,
                top_k=30,
                threshold=0.70,
                filters={'yacht_id': yacht_id},
            ))

        # Search graph nodes if available
        vector_queries.append(VectorQuery(
            table='graph_nodes',
            column='embedding',
            input_text=query,
            top_k=20,
            threshold=0.70,
            filters={'yacht_id': yacht_id},
        ))

        time_days = classification.time_window_days or 90

        return RetrievalPlan(
            path=RetrievalPath.HYBRID,
            allowed_scopes=scopes,
            time_window=TimeWindow(days=time_days),
            row_limits={s: DEFAULT_ROW_LIMITS.get(s, 30) for s in scopes},
            sql_queries=[q for q in sql_queries if q],
            vector_queries=vector_queries,
            ranking_recipe=get_recipe_for_surface(context.surface_state.value),
            explain=f"Hybrid search: SQL filters + semantic on '{query[:30]}...'",
            explain_details={
                'query_preview': query[:100],
                'sql_domains': [q.domain for q in sql_queries if q],
                'vector_tables': [v.table for v in vector_queries],
                'classification_reason': classification.classification_reason,
            },
        )

    # =========================================================================
    # SQL Query Builders
    # =========================================================================

    def _build_work_order_query(
        self,
        yacht_id: str,
        entity_ids: List[tuple],
        pattern_ids: List[tuple],
        query: str,
    ) -> ParameterizedQuery:
        """Build work order SQL query."""
        sql = """
            SELECT
                id, wo_number, title, status, priority,
                equipment_id, created_at, updated_at
            FROM public.pms_work_orders
            WHERE yacht_id = :yacht_id
        """
        params = {'yacht_id': yacht_id}

        # Add ID filters if present
        wo_ids = [eid for eid, etype in entity_ids if etype == 'work_order']
        wo_patterns = [p for p, ptype in pattern_ids if ptype == 'work_order']

        if wo_ids:
            sql += " AND id = ANY(:wo_ids)"
            params['wo_ids'] = wo_ids

        if wo_patterns:
            # Match WO number patterns
            pattern_conditions = " OR ".join([f"wo_number ILIKE '%{p}%'" for p in wo_patterns])
            sql += f" AND ({pattern_conditions})"

        if query and not wo_ids and not wo_patterns:
            sql += " AND (title ILIKE :query OR wo_number ILIKE :query)"
            params['query'] = f'%{query}%'

        sql += " ORDER BY updated_at DESC LIMIT 30"

        return ParameterizedQuery(sql=sql, params=params, domain='work_orders')

    def _build_equipment_query(
        self,
        yacht_id: str,
        entity_ids: List[tuple],
        query: str,
    ) -> ParameterizedQuery:
        """Build equipment SQL query."""
        sql = """
            SELECT
                id, name, system_type, serial_number,
                model, manufacturer, status
            FROM public.pms_equipment
            WHERE yacht_id = :yacht_id
        """
        params = {'yacht_id': yacht_id}

        eq_ids = [eid for eid, etype in entity_ids if etype == 'equipment']
        if eq_ids:
            sql += " AND id = ANY(:eq_ids)"
            params['eq_ids'] = eq_ids
        elif query:
            sql += " AND (name ILIKE :query OR serial_number ILIKE :query)"
            params['query'] = f'%{query}%'

        sql += " ORDER BY name LIMIT 30"

        return ParameterizedQuery(sql=sql, params=params, domain='equipment')

    def _build_parts_query(
        self,
        yacht_id: str,
        entity_ids: List[tuple],
        query: str,
    ) -> ParameterizedQuery:
        """Build parts SQL query."""
        sql = """
            SELECT
                id, name, part_number, quantity_on_hand,
                minimum_quantity, location
            FROM public.pms_parts
            WHERE yacht_id = :yacht_id
        """
        params = {'yacht_id': yacht_id}

        if query:
            sql += " AND (name ILIKE :query OR part_number ILIKE :query)"
            params['query'] = f'%{query}%'

        sql += " ORDER BY name LIMIT 30"

        return ParameterizedQuery(sql=sql, params=params, domain='parts')

    def _build_faults_query(
        self,
        yacht_id: str,
        entity_ids: List[tuple],
        query: str,
    ) -> ParameterizedQuery:
        """Build faults SQL query."""
        sql = """
            SELECT
                id, equipment_id, fault_code, description,
                severity, status, reported_at
            FROM public.pms_faults
            WHERE yacht_id = :yacht_id
        """
        params = {'yacht_id': yacht_id}

        fault_ids = [eid for eid, etype in entity_ids if etype == 'fault']
        if fault_ids:
            sql += " AND id = ANY(:fault_ids)"
            params['fault_ids'] = fault_ids
        elif query:
            sql += " AND (description ILIKE :query OR fault_code ILIKE :query)"
            params['query'] = f'%{query}%'

        sql += " ORDER BY reported_at DESC LIMIT 20"

        return ParameterizedQuery(sql=sql, params=params, domain='faults')
