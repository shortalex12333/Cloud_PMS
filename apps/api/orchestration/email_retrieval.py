"""
Email Retrieval - Email-Specific Retrieval Logic
==================================================

Handles two distinct email retrieval modes:

1. INBOX SCAN (no query text):
   - SQL-only
   - Date-bounded (default 30 days)
   - Direction bias: inbound (90%) default
   - Sorted by recency
   - No embeddings required

2. EMAIL SEARCH (query text present):
   - Hybrid: SQL text match + vector similarity
   - Uses meta_embedding column
   - Thread cohesion via conversation_id
   - Cheaper than global search (scoped to emails only)

IMPORTANT: No folder metaphors. Use 'direction' (inbound/outbound).
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .retrieval_plan import (
    RetrievalPlan,
    RetrievalPath,
    TimeWindow,
    ParameterizedQuery,
    VectorQuery,
    DEFAULT_ROW_LIMITS,
)
from .surface_state import SurfaceContext, SurfaceState
from .ranking_recipes import get_ranking_recipe

logger = logging.getLogger(__name__)


class EmailRetrieval:
    """
    Email-specific retrieval logic.
    Produces RetrievalPlans for inbox scan and email search.
    """

    # Default time windows
    DEFAULT_INBOX_DAYS = 30
    DEFAULT_SEARCH_DAYS = 90

    # Row limits
    INBOX_LIMIT = 50
    SEARCH_LIMIT = 30
    ATTACHMENT_LIMIT = 10

    def prepare_inbox_scan(
        self,
        context: SurfaceContext,
    ) -> RetrievalPlan:
        """
        Prepare inbox scan plan (no query text).

        SQL-only, date-bounded, sorted by recency.
        No embeddings involved.
        """
        yacht_id = context.yacht_id
        user_id = context.user_id
        direction_bias = context.email_direction_bias  # Frontend default: 'inbound'

        # Build SQL query for inbox fetch
        inbox_sql = """
            SELECT
                em.id,
                em.thread_id,
                em.subject,
                em.from_display_name,
                em.direction,
                em.sent_at,
                em.received_at,
                em.has_attachments,
                et.provider_conversation_id,
                et.message_count
            FROM public.email_messages em
            JOIN public.email_threads et ON em.thread_id = et.id
            WHERE em.yacht_id = :yacht_id
              AND em.sent_at >= NOW() - INTERVAL :days_interval
              AND (:direction IS NULL OR em.direction = :direction)
            ORDER BY em.sent_at DESC
            LIMIT :limit
        """

        sql_query = ParameterizedQuery(
            sql=inbox_sql,
            params={
                'yacht_id': yacht_id,
                'days_interval': f'{self.DEFAULT_INBOX_DAYS} days',
                'direction': direction_bias if direction_bias != 'both' else None,
                'limit': self.INBOX_LIMIT,
            },
            domain='emails',
        )

        return RetrievalPlan(
            path=RetrievalPath.EMAIL_INBOX,
            allowed_scopes=['emails'],
            time_window=TimeWindow(days=self.DEFAULT_INBOX_DAYS),
            row_limits={'emails': self.INBOX_LIMIT},
            must_filters={
                'yacht_id': yacht_id,
                'user_id': user_id,
            },
            sql_queries=[sql_query],
            vector_queries=[],  # No vectors for inbox
            ranking_recipe='email_inbox',
            explain=f"Inbox scan: last {self.DEFAULT_INBOX_DAYS} days, {direction_bias} direction bias",
            explain_details={
                'mode': 'inbox_scan',
                'direction_bias': direction_bias,
                'time_window_days': self.DEFAULT_INBOX_DAYS,
                'uses_vector': False,
            },
        )

    def prepare_email_search(
        self,
        context: SurfaceContext,
        classified_terms: List[Dict[str, Any]] = None,
    ) -> RetrievalPlan:
        """
        Prepare email search plan (query text present).

        Hybrid: SQL text match + vector similarity on meta_embedding.
        """
        yacht_id = context.yacht_id
        query = context.query_text.strip()
        open_thread_id = context.open_thread_id

        sql_queries = []
        vector_queries = []

        # SQL: Subject/sender text match
        text_match_sql = """
            SELECT
                em.id,
                em.thread_id,
                em.subject,
                em.from_display_name,
                em.direction,
                em.sent_at,
                em.has_attachments,
                et.provider_conversation_id,
                1 as match_type  -- text match
            FROM public.email_messages em
            JOIN public.email_threads et ON em.thread_id = et.id
            WHERE em.yacht_id = :yacht_id
              AND em.sent_at >= NOW() - INTERVAL :days_interval
              AND (
                  em.subject ILIKE :query_pattern
                  OR em.from_display_name ILIKE :query_pattern
              )
            ORDER BY em.sent_at DESC
            LIMIT :limit
        """

        sql_queries.append(ParameterizedQuery(
            sql=text_match_sql,
            params={
                'yacht_id': yacht_id,
                'days_interval': f'{self.DEFAULT_SEARCH_DAYS} days',
                'query_pattern': f'%{query}%',
                'limit': self.SEARCH_LIMIT,
            },
            domain='emails',
        ))

        # Vector: Semantic search on meta_embedding
        vector_queries.append(VectorQuery(
            table='email_messages',
            column='meta_embedding',
            input_text=query,
            top_k=self.SEARCH_LIMIT,
            threshold=0.70,
            filters={
                'yacht_id': yacht_id,
                'days_back': self.DEFAULT_SEARCH_DAYS,
            },
        ))

        # If thread is open, add thread cohesion query
        if open_thread_id:
            thread_sql = """
                SELECT
                    em.id,
                    em.thread_id,
                    em.subject,
                    em.from_display_name,
                    em.direction,
                    em.sent_at,
                    em.has_attachments,
                    2 as match_type  -- thread cohesion
                FROM public.email_messages em
                WHERE em.thread_id = :thread_id
                ORDER BY em.sent_at DESC
                LIMIT 20
            """
            sql_queries.append(ParameterizedQuery(
                sql=thread_sql,
                params={'thread_id': open_thread_id},
                domain='emails_thread',
            ))

        # Attachment name search
        attachment_sql = """
            SELECT
                em.id,
                em.thread_id,
                em.subject,
                em.attachments,
                3 as match_type  -- attachment match
            FROM public.email_messages em
            WHERE em.yacht_id = :yacht_id
              AND em.has_attachments = true
              AND em.attachments::text ILIKE :query_pattern
              AND em.sent_at >= NOW() - INTERVAL :days_interval
            LIMIT :limit
        """
        sql_queries.append(ParameterizedQuery(
            sql=attachment_sql,
            params={
                'yacht_id': yacht_id,
                'query_pattern': f'%{query}%',
                'days_interval': f'{self.DEFAULT_SEARCH_DAYS} days',
                'limit': self.ATTACHMENT_LIMIT,
            },
            domain='email_attachments',
        ))

        return RetrievalPlan(
            path=RetrievalPath.EMAIL_SEARCH,
            allowed_scopes=['emails', 'email_attachments'],
            time_window=TimeWindow(days=self.DEFAULT_SEARCH_DAYS),
            row_limits={
                'emails': self.SEARCH_LIMIT,
                'email_attachments': self.ATTACHMENT_LIMIT,
            },
            must_filters={
                'yacht_id': yacht_id,
            },
            sql_queries=sql_queries,
            vector_queries=vector_queries,
            ranking_recipe='email_search',
            explain=f"Email search: '{query[:50]}...', SQL + vector hybrid",
            explain_details={
                'mode': 'email_search',
                'query_preview': query[:100],
                'time_window_days': self.DEFAULT_SEARCH_DAYS,
                'uses_vector': True,
                'has_thread_context': open_thread_id is not None,
            },
        )

    def prepare(self, context: SurfaceContext, classified_terms: List[Dict] = None) -> RetrievalPlan:
        """
        Main entry point. Routes to inbox scan or email search.
        """
        if context.is_system_triggered():
            return self.prepare_inbox_scan(context)
        else:
            return self.prepare_email_search(context, classified_terms)
