"""
Execution Layer - Run RetrievalPlan Queries
============================================

Executes the queries specified in a RetrievalPlan.
Handles SQL execution, vector similarity, and result merging.

This layer:
    - ONLY executes what's in the plan
    - Never modifies the plan
    - Enforces yacht isolation
    - Applies ranking recipes
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import time

from .retrieval_plan import RetrievalPlan, RetrievalPath, ParameterizedQuery, VectorQuery
from .ranking_recipes import get_ranking_recipe, calculate_recency_score

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result from plan execution."""
    results: List[Dict[str, Any]]
    results_by_domain: Dict[str, List[Dict[str, Any]]]
    total_count: int
    execution_time_ms: float
    sql_results_count: int
    vector_results_count: int
    merged_count: int
    explain: Dict[str, Any]


class PlanExecutor:
    """
    Executes RetrievalPlan queries against Supabase.
    """

    def __init__(self, supabase_client, yacht_id: str):
        """
        Initialize executor with tenant-specific client.

        Args:
            supabase_client: Supabase client for the tenant
            yacht_id: Yacht ID for isolation verification
        """
        self.client = supabase_client
        self.yacht_id = yacht_id

    async def execute(self, plan: RetrievalPlan) -> ExecutionResult:
        """
        Execute all queries in the plan and merge results.

        Args:
            plan: RetrievalPlan from orchestration layer

        Returns:
            ExecutionResult with merged, ranked results
        """
        start_time = time.time()

        # Verify yacht isolation
        if plan.must_filters.get('yacht_id') != self.yacht_id:
            raise ValueError("Yacht ID mismatch - plan does not match executor context")

        sql_results = []
        vector_results = []
        results_by_domain: Dict[str, List[Dict]] = {}

        # Execute SQL queries
        for sql_query in plan.sql_queries:
            try:
                domain_results = await self._execute_sql(sql_query)
                sql_results.extend(domain_results)

                # Group by domain
                domain = sql_query.domain
                if domain not in results_by_domain:
                    results_by_domain[domain] = []
                results_by_domain[domain].extend(domain_results)

            except Exception as e:
                logger.error(f"SQL query failed for domain {sql_query.domain}: {e}")

        # Execute vector queries (if path requires it)
        if plan.is_vector_involved():
            for vector_query in plan.vector_queries:
                try:
                    vr = await self._execute_vector(vector_query)
                    vector_results.extend(vr)

                    # Group by table as domain
                    domain = vector_query.table
                    if domain not in results_by_domain:
                        results_by_domain[domain] = []
                    results_by_domain[domain].extend(vr)

                except Exception as e:
                    logger.error(f"Vector query failed for {vector_query.table}: {e}")

        # Merge and deduplicate
        merged = self._merge_results(sql_results, vector_results)

        # Apply ranking
        ranked = self._apply_ranking(merged, plan.ranking_recipe)

        # Apply row limits
        for domain, limit in plan.row_limits.items():
            if domain in results_by_domain:
                results_by_domain[domain] = results_by_domain[domain][:limit]

        execution_time_ms = (time.time() - start_time) * 1000

        return ExecutionResult(
            results=ranked,
            results_by_domain=results_by_domain,
            total_count=len(ranked),
            execution_time_ms=execution_time_ms,
            sql_results_count=len(sql_results),
            vector_results_count=len(vector_results),
            merged_count=len(merged),
            explain={
                'sql_queries_executed': len(plan.sql_queries),
                'vector_queries_executed': len(plan.vector_queries),
                'ranking_recipe': plan.ranking_recipe,
                'path': plan.path.value,
            },
        )

    def execute_sync(self, plan: RetrievalPlan) -> ExecutionResult:
        """
        Synchronous execution wrapper.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.execute(plan))

    async def _execute_sql(self, query: ParameterizedQuery) -> List[Dict[str, Any]]:
        """
        Execute a parameterized SQL query.
        Uses Supabase's query builder for safety.
        """
        # For Supabase, we need to use the table API
        # The SQL in the plan is for documentation/debugging
        # Actual execution uses Supabase query builder

        domain = query.domain
        params = query.params

        try:
            if domain == 'emails':
                return await self._query_emails(params)
            elif domain == 'emails_thread':
                return await self._query_email_thread(params)
            elif domain == 'email_attachments':
                return await self._query_email_attachments(params)
            elif domain == 'work_orders':
                return await self._query_work_orders(params)
            elif domain == 'equipment':
                return await self._query_equipment(params)
            elif domain == 'parts':
                return await self._query_parts(params)
            elif domain == 'faults':
                return await self._query_faults(params)
            else:
                logger.warning(f"Unknown domain: {domain}")
                return []

        except Exception as e:
            logger.error(f"Query execution failed for {domain}: {e}")
            return []

    async def _execute_vector(self, query: VectorQuery) -> List[Dict[str, Any]]:
        """
        Execute vector similarity search.

        LAW 21: Vector searches must query search_index table with embedding_1536 column.
        """
        try:
            # Generate embedding for input text
            embedding = await self._get_embedding(query.input_text)
            if not embedding:
                return []

            # LAW 21: Primary vector search against search_index table
            if query.table == 'search_index':
                result = self.client.rpc(
                    'match_search_index',
                    {
                        'p_yacht_id': self.yacht_id,
                        'p_query_embedding': embedding,
                        'p_match_threshold': query.threshold,
                        'p_match_count': query.top_k,
                        'p_object_type': query.filters.get('object_type'),
                    }
                ).execute()

                # Transform results to include similarity score and standard fields
                results = []
                for item in (result.data or []):
                    results.append({
                        'id': item.get('object_id'),
                        'object_type': item.get('object_type'),
                        'object_id': item.get('object_id'),
                        'search_text': item.get('search_text'),
                        'payload': item.get('payload'),
                        'similarity': item.get('similarity'),
                        '_source': 'vector',
                    })
                return results

            # Use Supabase match function for legacy tables
            elif query.table == 'email_messages':
                result = self.client.rpc(
                    'match_email_messages',
                    {
                        'p_yacht_id': self.yacht_id,
                        'p_query_embedding': embedding,
                        'p_match_threshold': query.threshold,
                        'p_match_count': query.top_k,
                        'p_direction': query.filters.get('direction'),
                        'p_days_back': query.filters.get('days_back', 90),
                    }
                ).execute()
                return result.data or []

            elif query.table == 'document_chunks':
                result = self.client.rpc(
                    'match_documents',
                    {
                        'query_embedding': embedding,
                        'match_threshold': query.threshold,
                        'match_count': query.top_k,
                        'filter_yacht_id': self.yacht_id,
                    }
                ).execute()
                return result.data or []

            else:
                logger.warning(f"No vector match function for table: {query.table}")
                return []

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding for text using OpenAI text-embedding-3-small.
        """
        import os
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    def _merge_results(
        self,
        sql_results: List[Dict],
        vector_results: List[Dict],
    ) -> List[Dict]:
        """
        Merge SQL and vector results, deduplicating by ID.
        """
        seen_ids = set()
        merged = []

        # SQL results first (higher trust)
        for r in sql_results:
            rid = r.get('id')
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                r['_source'] = 'sql'
                merged.append(r)

        # Vector results (may have similarity score)
        for r in vector_results:
            rid = r.get('id')
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                r['_source'] = 'vector'
                merged.append(r)

        return merged

    def _apply_ranking(
        self,
        results: List[Dict],
        recipe_name: str,
    ) -> List[Dict]:
        """
        Apply ranking recipe to results.
        """
        recipe = get_ranking_recipe(recipe_name)

        for r in results:
            score = 0.0

            # Similarity score (from vector search)
            if 'similarity' in r:
                score += r['similarity'] * recipe.get('similarity', 0)

            # Recency score
            if 'sent_at' in r or 'updated_at' in r or 'created_at' in r:
                date_field = r.get('sent_at') or r.get('updated_at') or r.get('created_at')
                if date_field:
                    try:
                        if isinstance(date_field, str):
                            from datetime import datetime
                            dt = datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                            days_ago = (datetime.now(dt.tzinfo) - dt).days
                        else:
                            days_ago = 0
                        recency = calculate_recency_score(days_ago)
                        score += recency * recipe.get('recency', 0)
                    except:
                        pass

            # Source boost (SQL = exact match)
            if r.get('_source') == 'sql':
                score += recipe.get('exact_match_boost', 0)

            r['_rank_score'] = score

        # Sort by rank score descending
        results.sort(key=lambda x: x.get('_rank_score', 0), reverse=True)
        return results

    # =========================================================================
    # Domain-specific query methods
    # =========================================================================

    async def _query_emails(self, params: Dict) -> List[Dict]:
        """Query email_messages table."""
        query = self.client.table('email_messages').select(
            'id, thread_id, subject, from_display_name, direction, sent_at, has_attachments'
        ).eq('yacht_id', self.yacht_id)

        if params.get('direction'):
            query = query.eq('direction', params['direction'])

        if params.get('limit'):
            query = query.limit(params['limit'])

        query = query.order('sent_at', desc=True)
        result = query.execute()
        return result.data or []

    async def _query_email_thread(self, params: Dict) -> List[Dict]:
        """Query messages in a specific thread."""
        thread_id = params.get('thread_id')
        if not thread_id:
            return []

        result = self.client.table('email_messages').select(
            'id, thread_id, subject, from_display_name, direction, sent_at, has_attachments'
        ).eq('thread_id', thread_id).order('sent_at', desc=True).limit(20).execute()

        return result.data or []

    async def _query_email_attachments(self, params: Dict) -> List[Dict]:
        """Query emails with attachments matching pattern."""
        query_pattern = params.get('query_pattern', '')
        if not query_pattern:
            return []

        result = self.client.table('email_messages').select(
            'id, thread_id, subject, attachments'
        ).eq('yacht_id', self.yacht_id).eq(
            'has_attachments', True
        ).ilike('attachments', query_pattern).limit(
            params.get('limit', 10)
        ).execute()

        return result.data or []

    async def _query_work_orders(self, params: Dict) -> List[Dict]:
        """Query pms_work_orders table with ILIKE + trigram fallback."""
        query = self.client.table('pms_work_orders').select(
            'id, wo_number, title, status, priority, equipment_id, created_at, updated_at'
        ).eq('yacht_id', self.yacht_id)

        if params.get('wo_ids'):
            query = query.in_('id', params['wo_ids'])
        elif params.get('query'):
            query = query.or_(f"title.ilike.{params['query']},wo_number.ilike.{params['query']}")

        query = query.order('updated_at', desc=True).limit(params.get('limit', 30))
        result = query.execute()
        results = result.data or []

        # Phase 2: pg_trgm fuzzy search if ILIKE found few results
        # LAW 20: Universal trigram matching
        if len(results) < 5 and params.get('query') and not params.get('wo_ids'):
            try:
                fuzzy_result = self.client.rpc('search_work_orders_fuzzy', {
                    'p_yacht_id': self.yacht_id,
                    'p_query': params['query'].replace('%', ''),
                    'p_threshold': 0.3,
                    'p_limit': params.get('limit', 30)
                }).execute()

                if fuzzy_result.data:
                    seen_ids = {r['id'] for r in results}
                    for item in fuzzy_result.data:
                        if item.get('work_order_id') not in seen_ids:
                            results.append({
                                'id': item['work_order_id'],
                                'wo_number': item.get('work_order_number'),
                                'title': item.get('title'),
                                'status': item.get('status'),
                                'priority': item.get('priority'),
                                '_fuzzy_match': True,
                                '_similarity': item.get('similarity')
                            })
                    logger.info(f"[Executor] Trigram found {len(fuzzy_result.data)} fuzzy matches for work orders")
            except Exception as e:
                logger.warning(f"[Executor] Work orders trigram search failed: {e}")

        return results

    async def _query_equipment(self, params: Dict) -> List[Dict]:
        """Query pms_equipment table with ILIKE + trigram fallback."""
        query = self.client.table('pms_equipment').select(
            'id, name, system_type, serial_number, model, manufacturer, status'
        ).eq('yacht_id', self.yacht_id)

        if params.get('eq_ids'):
            query = query.in_('id', params['eq_ids'])
        elif params.get('query'):
            query = query.or_(f"name.ilike.{params['query']},serial_number.ilike.{params['query']}")

        query = query.order('name').limit(params.get('limit', 30))
        result = query.execute()
        results = result.data or []

        # Phase 2: pg_trgm fuzzy search if ILIKE found few results
        # LAW 20: Universal trigram matching
        if len(results) < 5 and params.get('query') and not params.get('eq_ids'):
            try:
                fuzzy_result = self.client.rpc('search_equipment_fuzzy', {
                    'p_yacht_id': self.yacht_id,
                    'p_query': params['query'].replace('%', ''),
                    'p_threshold': 0.3,
                    'p_limit': params.get('limit', 30)
                }).execute()

                if fuzzy_result.data:
                    seen_ids = {r['id'] for r in results}
                    for item in fuzzy_result.data:
                        if item.get('equipment_id') not in seen_ids:
                            results.append({
                                'id': item['equipment_id'],
                                'name': item.get('equipment_name'),
                                'serial_number': item.get('serial_number'),
                                'manufacturer': item.get('manufacturer'),
                                'model': item.get('model'),
                                '_fuzzy_match': True,
                                '_similarity': item.get('similarity')
                            })
                    logger.info(f"[Executor] Trigram found {len(fuzzy_result.data)} fuzzy matches for equipment")
            except Exception as e:
                logger.warning(f"[Executor] Equipment trigram search failed: {e}")

        return results

    async def _query_parts(self, params: Dict) -> List[Dict]:
        """Query pms_parts table with ILIKE + trigram fallback."""
        # Phase 1: ILIKE substring search (fast, indexed)
        query = self.client.table('pms_parts').select(
            'id, name, part_number, quantity_on_hand, minimum_quantity, location'
        ).eq('yacht_id', self.yacht_id)

        if params.get('query'):
            query = query.or_(f"name.ilike.{params['query']},part_number.ilike.{params['query']}")

        query = query.order('name').limit(params.get('limit', 30))
        result = query.execute()
        results = result.data or []

        # Phase 2: pg_trgm fuzzy search if ILIKE found few results
        # LAW 20: Universal trigram matching for typo tolerance
        if len(results) < 5 and params.get('query'):
            try:
                fuzzy_result = self.client.rpc('search_parts_fuzzy', {
                    'p_yacht_id': self.yacht_id,
                    'p_query': params['query'].replace('%', ''),
                    'p_threshold': 0.3,
                    'p_limit': params.get('limit', 30)
                }).execute()

                if fuzzy_result.data:
                    seen_ids = {r['id'] for r in results}
                    for item in fuzzy_result.data:
                        if item.get('part_id') not in seen_ids:
                            results.append({
                                'id': item['part_id'],
                                'name': item.get('part_name'),
                                'part_number': item.get('part_number'),
                                'quantity_on_hand': item.get('on_hand'),
                                'location': item.get('location'),
                                '_fuzzy_match': True,
                                '_similarity': item.get('similarity')
                            })
                    logger.info(f"[Executor] Trigram found {len(fuzzy_result.data)} fuzzy matches for parts")
            except Exception as e:
                logger.warning(f"[Executor] Parts trigram search failed: {e}")

        return results

    async def _query_faults(self, params: Dict) -> List[Dict]:
        """Query pms_faults table."""
        query = self.client.table('pms_faults').select(
            'id, equipment_id, fault_code, description, severity, status, reported_at'
        ).eq('yacht_id', self.yacht_id)

        if params.get('fault_ids'):
            query = query.in_('id', params['fault_ids'])
        elif params.get('query'):
            query = query.or_(f"description.ilike.{params['query']},fault_code.ilike.{params['query']}")

        query = query.order('reported_at', desc=True).limit(params.get('limit', 20))
        result = query.execute()
        return result.data or []
