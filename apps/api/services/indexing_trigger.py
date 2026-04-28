"""
PR-IDX-1: Universal Indexing Trigger

Fire-and-forget hook that enqueues any entity change or file upload for
re-indexing by the projection worker.

The enqueue call is SYNC (no async/await) to match the ledger write pattern
used in action_execution_routes.py and attachment_upload.py.

Column names confirmed against search_index schema via projection_worker.py:
  object_type, object_id, yacht_id, embedding_status, filters, updated_at
"""

import json
import logging

logger = logging.getLogger(__name__)


def enqueue_for_projection(
    entity_id: str,
    entity_type: str,
    yacht_id: str,
    db_client,          # Supabase Python client (not asyncpg)
    visibility: dict = None,
) -> None:
    """
    Upsert a row into search_index with embedding_status='pending' so the
    projection worker picks it up on its next pass.

    Idempotent: ON CONFLICT (object_type, object_id) DO UPDATE — safe to call
    multiple times for the same entity.  updated_at is always refreshed so the
    worker treats the row as dirty even if it already existed.

    visibility: if not None, written into filters JSONB as
        {"visibility": <value>}
    If None, filters is set to {}.

    Never raises — any failure is logged as a warning so the caller's
    mutation response is never blocked.
    """
    try:
        filters: dict = {}
        if visibility is not None:
            filters["visibility"] = visibility

        row = {
            "object_type": entity_type,
            "object_id": str(entity_id),
            "yacht_id": str(yacht_id),
            "org_id": str(yacht_id),     # NOT NULL — projection worker overwrites from source row
            "search_text": "",           # NOT NULL — projection worker replaces with real text
            "embedding_status": "pending",
            "filters": json.dumps(filters),
        }

        # ON CONFLICT (object_type, object_id) DO UPDATE — idempotent re-enqueue.
        # updated_at is set server-side via now() so the worker's ORDER BY
        # updated_at ASC picks this row up promptly.
        # NEVER touch: learned_keywords, learned_at, embedding_1536
        # (owned by nightly_feedback_loop.py / embedding_worker_1536.py).
        (
            db_client
            .table("search_index")
            .upsert(
                row,
                on_conflict="object_type,object_id",
            )
            .execute()
        )

    except Exception as _exc:
        logger.warning(
            f"[Indexing trigger] enqueue_for_projection failed "
            f"entity={entity_type}/{str(entity_id)[:8]} yacht={str(yacht_id)[:8]}: {_exc}"
        )
