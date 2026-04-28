"""
Email Sync Routes
=================
POST /email/sync/now
POST /email/sync/all-folders
POST /email/backfill-embeddings
POST /email/backfill-weblinks
GET  /email/ledger/{entity_type}/{entity_id}
GET  /email/debug/search-folders
GET  /email/debug/graph-me
GET  /email/debug/inbox-compare
GET  /email/debug/thread-yacht-check
POST /email/debug/force-sync-missing
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from middleware.auth import get_authenticated_user
from integrations.supabase import get_tenant_client
from integrations.feature_flags import check_email_feature
import handlers.email_handlers as email_handlers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["email"])

_SYNC_ROLES = ('chief_engineer', 'manager', 'captain', 'admin')

_VALID_LEDGER_TYPES = ['email_thread', 'email_message', 'work_order', 'equipment', 'part', 'document']


@router.post("/sync/now")
async def sync_now(
    auth: dict = Depends(get_authenticated_user),
    full_resync: bool = False,
    upgrade_to_mailbox: bool = False,
):
    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    if auth.get('role', '') not in _SYNC_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions for sync")
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.sync_now(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
        full_resync=full_resync, upgrade_to_mailbox=upgrade_to_mailbox,
    )


@router.post("/sync/all-folders")
async def sync_all_folders(
    auth: dict = Depends(get_authenticated_user),
    max_per_folder: int = 100,
):
    enabled, error_msg = check_email_feature('sync')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.sync_all_folders(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
        max_per_folder=max_per_folder,
    )


@router.post("/backfill-embeddings")
async def backfill_embeddings(auth: dict = Depends(get_authenticated_user), limit: int = 100):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.backfill_embeddings(
        supabase=supabase, yacht_id=auth['yacht_id'], limit=limit,
    )


@router.post("/backfill-weblinks")
async def backfill_weblinks(auth: dict = Depends(get_authenticated_user), limit: int = 100):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.backfill_weblinks(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'], limit=limit,
    )


@router.get("/ledger/{entity_type}/{entity_id}")
async def get_entity_ledger(
    entity_type: str,
    entity_id: str,
    limit: int = 50,
    offset: int = 0,
    auth: dict = Depends(get_authenticated_user),
):
    enabled, error_msg = check_email_feature('focus')
    if not enabled:
        raise HTTPException(status_code=503, detail=error_msg)
    if entity_type not in _VALID_LEDGER_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {_VALID_LEDGER_TYPES}")
    limit, offset = min(max(1, limit), 100), max(0, offset)
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.get_entity_ledger(
        supabase=supabase, yacht_id=auth['yacht_id'],
        entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset,
    )


@router.get("/debug/search-folders")
async def debug_search_folders(q: str, auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.debug_search_folders(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'], q=q,
    )


@router.get("/debug/graph-me")
async def debug_graph_me(auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.debug_graph_me(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
    )


@router.get("/debug/inbox-compare")
async def debug_inbox_compare(auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.debug_inbox_compare(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
    )


@router.get("/debug/thread-yacht-check")
async def debug_thread_yacht_check(thread_ids: str, auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.debug_thread_yacht_check(
        supabase=supabase, user_yacht_id=auth['yacht_id'],
        tenant_key_alias=auth['tenant_key_alias'], thread_ids_str=thread_ids,
    )


@router.post("/debug/force-sync-missing")
async def debug_force_sync_missing(auth: dict = Depends(get_authenticated_user)):
    supabase = get_tenant_client(auth['tenant_key_alias'])
    return await email_handlers.debug_force_sync_missing(
        supabase=supabase, user_id=auth['user_id'], yacht_id=auth['yacht_id'],
    )
