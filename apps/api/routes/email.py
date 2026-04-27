"""
CelesteOS Backend - Email Transport Layer Routes
================================================
Thin coordinator. All logic lives in the sub-route files below.

Route files:
  email_thread_routes.py  — thread, message, attachment, links
  email_inbox_routes.py   — search, inbox, related, focus, search-objects, unread, worker/status
  email_link_routes.py    — link CRUD, action/execute, evidence
  email_sync_routes.py    — sync, backfill, ledger, debug

Service files:
  services/email_link_service.py    — audit, idempotency, upsert_email_link
  services/email_search_service.py  — EmbeddingCache, extract_query_entities, search_email_threads

Doctrine compliance:
- All queries scoped by yacht_id
- Render uses READ token only
- Evidence uses WRITE token only
- No email body storage
- All link changes audited
"""

from fastapi import APIRouter

from routes.email_thread_routes import router as _thread_router
from routes.email_inbox_routes import router as _inbox_router
from routes.email_link_routes import router as _link_router
from routes.email_sync_routes import router as _sync_router

router = APIRouter(prefix="/email", tags=["email"])

router.include_router(_thread_router)
router.include_router(_inbox_router)
router.include_router(_link_router)
router.include_router(_sync_router)

__all__ = ['router']
