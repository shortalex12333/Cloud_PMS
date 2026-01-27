#!/usr/bin/env python3
"""
Email Search Preparation

Purpose
- Wire regex entity extraction + embeddings into the database so hybrid
  search can leverage both vector similarity and keyword/entity matches.

Responsibilities
- Fetch email metadata (subject, preview_text) for a message
- Ensure an embedding exists (generate and store if missing)
- Run regex entity extraction on subject + preview_text
- Persist results into `email_extraction_results`
- Mark `email_messages.extraction_status = 'completed'` upon success

Notes
- This module performs deterministic extraction only; no AI intent.
- It reuses existing `email_rag.entity_extractor` and `email_rag.embedder` utilities.
- Designed to be called from sync jobs or ad‑hoc backfill scripts.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from integrations.supabase import get_supabase_client
from email_rag.entity_extractor import (
    EmailEntityExtractor,
    store_extraction_results,
)
from email_rag.embedder import get_openai_client

logger = logging.getLogger(__name__)


async def _get_message_record(supabase, yacht_id: str, message_id: str) -> Optional[Dict[str, Any]]:
    """Fetch minimal fields required for preparation."""
    res = supabase.table('email_messages').select(
        'id, subject, preview_text, embedding, extraction_status'
    ).eq('id', message_id).eq('yacht_id', yacht_id).single().execute()
    return res.data if res and res.data else None


def _generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate an embedding for given text using text-embedding-3-small.
    Does not perform any DB writes; caller is responsible for persisting.
    """
    try:
        client = get_openai_client()
        resp = client.embeddings.create(model='text-embedding-3-small', input=text[:8000])
        return resp.data[0].embedding
    except Exception as e:
        logger.error(f"[prepare] Embedding generation failed: {e}")
        return None


async def _persist_embedding(supabase, yacht_id: str, message_id: str, embedding: List[float]) -> None:
    """Store embedding and touch indexed_at; do not alter extraction_status here."""
    supabase.table('email_messages').update({
        'embedding': embedding,
        'indexed_at': datetime.utcnow().isoformat(),
    }).eq('id', message_id).eq('yacht_id', yacht_id).execute()


async def prepare_email_for_search(message_id: str, yacht_id: str, supabase=None) -> Dict[str, Any]:
    """
    Prepare a single email for hybrid search.

    Steps
    1) Read subject + preview_text
    2) Ensure embedding exists; generate and store if missing
    3) Extract entities via regex and store rows in email_extraction_results
    4) Set extraction_status = 'completed'

    Args:
        message_id: UUID of the email message
        yacht_id: UUID of the yacht (tenant)
        supabase: Optional Supabase client (uses get_supabase_client() if not provided)

    Returns
    - Dict summary with flags for each step and counts of stored entities
    """
    if supabase is None:
        supabase = get_supabase_client()

    # 1) Fetch
    msg = await _get_message_record(supabase, yacht_id=yacht_id, message_id=message_id)
    if not msg:
        return {
            'message_id': message_id,
            'yacht_id': yacht_id,
            'status': 'not_found',
        }

    subject = (msg.get('subject') or '').strip()
    preview = (msg.get('preview_text') or '').strip()
    base_text = f"{subject}\n\n{preview}".strip()

    summary: Dict[str, Any] = {
        'message_id': message_id,
        'yacht_id': yacht_id,
        'had_embedding': bool(msg.get('embedding')),
        'generated_embedding': False,
        'stored_entities': 0,
        'status': 'ok',
    }

    # 2) Ensure embedding
    if not msg.get('embedding') and base_text:
        emb = _generate_embedding(base_text)
        if emb:
            await _persist_embedding(supabase, yacht_id, message_id, emb)
            summary['generated_embedding'] = True
        else:
            # Continue; hybrid query can still use entity_score even if vector is missing
            logger.warning(f"[prepare] Proceeding without embedding for message {message_id}")

    # 3) Extract + store entities
    try:
        extractor = EmailEntityExtractor()
        entities = extractor.extract(base_text)

        # Persist deterministic results to email_extraction_results
        await store_extraction_results(
            message_id=message_id,
            yacht_id=yacht_id,
            entities=entities,
            supabase=supabase,
        )

        # Count flattened insert size
        summary['stored_entities'] = sum(len(v) for v in entities.values())
    except Exception as e:
        logger.error(f"[prepare] Extraction failed for {message_id}: {e}")
        # Mark failed status to avoid endless retries by upstream scheduler
        supabase.table('email_messages').update({
            'extraction_status': 'failed',
        }).eq('id', message_id).eq('yacht_id', yacht_id).execute()
        summary['status'] = 'failed'
        return summary

    # 4) Finalize status
    supabase.table('email_messages').update({
        'extraction_status': 'completed',
    }).eq('id', message_id).eq('yacht_id', yacht_id).execute()

    return summary


async def prepare_backlog(yacht_id: str, limit: int = 100, supabase=None) -> Dict[str, Any]:
    """
    Prepare a backlog of messages needing extraction or missing entity rows.

    Selection logic (deny-by-default):
    - email_messages where extraction_status != 'completed' OR is NULL
    - plus messages with zero rows in email_extraction_results
    Limited by `limit` to control load.

    Args:
        yacht_id: UUID of the yacht (tenant)
        limit: Maximum messages to process
        supabase: Optional Supabase client (uses get_supabase_client() if not provided)
    """
    if supabase is None:
        supabase = get_supabase_client()

    # Find candidates by status first
    pending = supabase.table('email_messages').select(
        'id'
    ).eq('yacht_id', yacht_id).neq('extraction_status', 'completed').limit(limit).execute()

    ids: List[str] = [r['id'] for r in (pending.data or [])]

    # If under limit, top up with those missing extraction rows
    if len(ids) < limit:
        # Fetch message IDs that have no extraction rows
        # Note: Supabase Py client lacks NOT EXISTS; do in two queries
        msgs = supabase.table('email_messages').select('id').eq('yacht_id', yacht_id).limit(limit * 2).execute()
        existing = supabase.table('email_extraction_results').select('message_id').eq('yacht_id', yacht_id).limit(limit * 4).execute()
        have_rows = {r['message_id'] for r in (existing.data or [])}
        for m in (msgs.data or []):
            mid = m['id']
            if mid not in have_rows and mid not in ids:
                ids.append(mid)
            if len(ids) >= limit:
                break

    processed = []
    for mid in ids:
        try:
            summary = await prepare_email_for_search(mid, yacht_id, supabase=supabase)
            processed.append(summary)
        except Exception as e:
            logger.error(f"[prepare_backlog] Failed for {mid}: {e}")

    return {
        'yacht_id': yacht_id,
        'count': len(processed),
        'summaries': processed,
    }


if __name__ == '__main__':
    import asyncio
    import os
    import sys

    # Allow quick ad-hoc runs:
    # python3 email_rag/prepare.py <yacht_id> <message_id|all> [limit]
    if len(sys.argv) < 3:
        print('Usage: python3 email_rag/prepare.py <yacht_id> <message_id|all> [limit]')
        sys.exit(1)

    yacht_id = sys.argv[1]
    target = sys.argv[2]

    # Ensure Supabase env vars are configured in shell
    try:
        get_supabase_client()
    except Exception as e:
        print(f"Supabase not configured: {e}")
        sys.exit(2)

    if target == 'all':
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        print(f"Preparing backlog for yacht {yacht_id}, limit={limit}...")
        out = asyncio.run(prepare_backlog(yacht_id, limit=limit))
        print(out)
    else:
        print(f"Preparing single message {target} for yacht {yacht_id}...")
        out = asyncio.run(prepare_email_for_search(target, yacht_id))
        print(out)

