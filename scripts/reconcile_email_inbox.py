#!/usr/bin/env python3
"""
One-shot email reconciliation script.

Fixes the gap between live Outlook mailbox and DB after deploying
all-folder delta sync. Delta only captures changes AFTER the bookmark
was set — pre-existing emails and deletions before deployment are invisible.

This script:
  1. Fetches all messages from live Outlook (inbox + sent, paginated)
  2. Fetches all active DB records for the yacht
  3. Marks ghosts (in DB but not Outlook) as is_deleted=true
  4. Backfills missing emails (in Outlook but not DB) via _process_message_v2
  5. Verifies counts match
  6. Resets sync_interval_minutes to 15

Run inside the API container:
  docker exec cloud_pms-api-1 python3 scripts/reconcile_email_inbox.py

NOT a migration. NOT an endpoint. One-time operational cleanup.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Support both local repo layout (apps/api/...) and container layout (/app/...)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
sys.path.insert(0, _repo_root)

# In Docker container, code lives at /app/ directly
if os.path.isdir("/app/services"):
    sys.path.insert(0, "/app")

import httpx
from supabase import create_client

try:
    # Container layout: /app/services/..., /app/integrations/...
    from services.email_sync_service import EmailSyncService
    from integrations.graph_client import get_valid_token
except ImportError:
    # Local repo layout: apps/api/services/...
    from apps.api.services.email_sync_service import EmailSyncService
    from apps.api.integrations.graph_client import get_valid_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
MESSAGE_SELECT = (
    "id,conversationId,subject,from,toRecipients,ccRecipients,"
    "receivedDateTime,sentDateTime,hasAttachments,internetMessageId,"
    "webLink,bodyPreview,parentFolderId"
)
# Folders we reconcile (match FOLDER_NAME_MAP in EmailSyncService)
RECONCILE_WELL_KNOWN = {"inbox", "sentitems"}
FOLDER_NAME_MAP = {
    "inbox": "inbox",
    "sentitems": "sent",
}
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes")

# ── Helpers ─────────────────────────────────────────────────────────────────


async def fetch_all_messages_in_folder(
    access_token: str, folder_id: str, page_size: int = 50
) -> list[dict]:
    """Paginate through every message in a Graph folder. Returns raw msgs."""
    url = (
        f"{GRAPH_BASE}/me/mailFolders/{folder_id}/messages"
        f"?$select={MESSAGE_SELECT}&$top={page_size}"
    )
    all_msgs: list[dict] = []
    api_calls = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {access_token}"}
            )
            api_calls += 1
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Graph API {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
            all_msgs.extend(data.get("value", []))
            url = data.get("@odata.nextLink")

    logger.info(
        f"  Fetched {len(all_msgs)} messages from folder {folder_id[:12]}... "
        f"({api_calls} API calls)"
    )
    return all_msgs


async def get_folder_map(access_token: str) -> dict[str, str]:
    """folder_guid → wellKnownName (lowercase, no spaces)."""
    url = f"{GRAPH_BASE}/me/mailFolders?$top=100"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            url, headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch folders: {resp.status_code}")
        folder_map = {}
        for f in resp.json().get("value", []):
            name = (f.get("wellKnownName") or f.get("displayName", "")).lower().replace(" ", "")
            folder_map[f["id"]] = name
        return folder_map


# ── Main ────────────────────────────────────────────────────────────────────


async def main():
    # Try multiple env var naming conventions
    supabase_url = (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("yTEST_YACHT_001_SUPABASE_URL")
    )
    supabase_key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("yTEST_YACHT_001_SUPABASE_SERVICE_KEY")
    )
    if not supabase_url or not supabase_key:
        logger.error(
            "Need SUPABASE_URL/SUPABASE_SERVICE_KEY or "
            "yTEST_YACHT_001_SUPABASE_URL/yTEST_YACHT_001_SUPABASE_SERVICE_KEY"
        )
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)

    # ── 0. Find the watcher for this yacht ──────────────────────────────
    watcher_resp = (
        supabase.table("email_watchers")
        .select("id, user_id, yacht_id, mailbox_address_hash, sync_interval_minutes")
        .eq("yacht_id", YACHT_ID)
        .eq("is_paused", False)
        .limit(1)
        .execute()
    )
    if not watcher_resp.data:
        logger.error(f"No active watcher for yacht {YACHT_ID}")
        sys.exit(1)

    watcher = watcher_resp.data[0]
    watcher_id = watcher["id"]
    user_id = watcher["user_id"]
    mailbox_address_hash = watcher.get("mailbox_address_hash", "")

    logger.info(f"Watcher: {watcher_id}")
    logger.info(f"User:    {user_id}")
    logger.info(f"Yacht:   {YACHT_ID}")
    if DRY_RUN:
        logger.info("*** DRY RUN — no DB writes ***")

    # ── 1. Get Graph token & folder map ─────────────────────────────────
    access_token = await get_valid_token(supabase, user_id, YACHT_ID, purpose="read")
    folder_map = await get_folder_map(access_token)

    target_folders = {
        fid: name
        for fid, name in folder_map.items()
        if name in RECONCILE_WELL_KNOWN
    }
    logger.info(f"Reconciling {len(target_folders)} folders: {list(target_folders.values())}")

    # ── 2. Fetch ALL live messages from target folders ──────────────────
    live_msgs_by_id: dict[str, dict] = {}  # provider_message_id → msg
    live_folder_ids: dict[str, str] = {}   # provider_message_id → folder_guid
    live_folder_names: dict[str, str] = {} # provider_message_id → folder_name

    for folder_id, well_known in target_folders.items():
        folder_name = FOLDER_NAME_MAP.get(well_known, well_known)
        msgs = await fetch_all_messages_in_folder(access_token, folder_id)
        for m in msgs:
            mid = m.get("id")
            if mid:
                live_msgs_by_id[mid] = m
                live_folder_ids[mid] = folder_id
                live_folder_names[mid] = folder_name

    live_ids = set(live_msgs_by_id.keys())
    logger.info(f"Live messages total: {len(live_ids)}")

    # ── 3. Fetch all active DB records for this yacht ───────────────────
    db_resp = (
        supabase.table("email_messages")
        .select("id, provider_message_id, folder")
        .eq("yacht_id", YACHT_ID)
        .eq("is_deleted", False)
        .execute()
    )
    db_records = db_resp.data or []
    # Filter to only inbox/sent records (don't touch archive, etc.)
    db_records = [r for r in db_records if r.get("folder") in ("inbox", "sent")]
    db_ids = {r["provider_message_id"] for r in db_records if r.get("provider_message_id")}

    logger.info(f"DB active records (inbox+sent): {len(db_ids)}")

    # ── 4. Compute deltas ───────────────────────────────────────────────
    ghost_ids = db_ids - live_ids       # in DB, not in Outlook
    missing_ids = live_ids - db_ids     # in Outlook, not in DB
    matching = db_ids & live_ids        # correct

    logger.info(f"Matching (correct):        {len(matching)}")
    logger.info(f"Ghosts (DB only → delete): {len(ghost_ids)}")
    logger.info(f"Missing (Outlook → add):   {len(missing_ids)}")

    if not ghost_ids and not missing_ids:
        logger.info("Nothing to reconcile — DB matches Outlook.")
        return

    # ── 5. Mark ghosts as deleted ───────────────────────────────────────
    if ghost_ids:
        logger.info(f"Marking {len(ghost_ids)} ghost records as is_deleted=true ...")
        if not DRY_RUN:
            # Batch in chunks of 100 to avoid query size limits
            ghost_list = list(ghost_ids)
            for i in range(0, len(ghost_list), 100):
                batch = ghost_list[i : i + 100]
                supabase.table("email_messages").update(
                    {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}
                ).eq("yacht_id", YACHT_ID).in_(
                    "provider_message_id", batch
                ).execute()
            logger.info(f"  ✓ {len(ghost_ids)} ghosts soft-deleted")
        else:
            logger.info("  [DRY RUN] Would soft-delete these ghosts")

    # ── 6. Backfill missing emails via _process_message_v2 ──────────────
    if missing_ids:
        logger.info(f"Backfilling {len(missing_ids)} missing emails ...")
        sync_service = EmailSyncService(supabase, access_token)
        backfilled = 0
        errors = 0

        for mid in missing_ids:
            msg = live_msgs_by_id[mid]
            folder_id = live_folder_ids[mid]
            folder_name = live_folder_names[mid]

            # Determine direction from envelope
            from_addr = (
                msg.get("from", {}).get("emailAddress", {}).get("address", "")
            )
            from_hash = sync_service._hash_email(from_addr)
            direction = "outbound" if from_hash == mailbox_address_hash else "inbound"

            if DRY_RUN:
                backfilled += 1
                continue

            try:
                thread_id = await sync_service._process_message_v2(
                    yacht_id=YACHT_ID,
                    watcher_id=watcher_id,
                    msg=msg,
                    folder=folder_name,
                    direction=direction,
                    parent_folder_id=folder_id,
                )
                if thread_id:
                    backfilled += 1
                else:
                    errors += 1
                    logger.warning(
                        f"  No thread_id for {mid[:12]}... (missing conversationId?)"
                    )
            except Exception as e:
                errors += 1
                logger.error(f"  Failed to backfill {mid[:12]}...: {e}")

        logger.info(f"  ✓ Backfilled {backfilled}, errors {errors}")

    # ── 7. Verify ───────────────────────────────────────────────────────
    logger.info("Running verification ...")
    verify_resp = (
        supabase.table("email_messages")
        .select("id, provider_message_id, is_deleted, folder")
        .eq("yacht_id", YACHT_ID)
        .execute()
    )
    verify_data = verify_resp.data or []
    active = [r for r in verify_data if not r.get("is_deleted") and r.get("folder") in ("inbox", "sent")]
    deleted = [r for r in verify_data if r.get("is_deleted")]
    active_ids = {r["provider_message_id"] for r in active}

    logger.info(f"  Live Outlook count:  {len(live_ids)}")
    logger.info(f"  DB active count:     {len(active)}")
    logger.info(f"  DB deleted count:    {len(deleted)}")

    still_missing = live_ids - active_ids
    still_ghost = active_ids - live_ids
    if still_missing:
        logger.warning(f"  ⚠ Still missing from DB: {len(still_missing)}")
    if still_ghost:
        logger.warning(f"  ⚠ Still ghost in DB: {len(still_ghost)}")
    if not still_missing and not still_ghost:
        logger.info("  ✓ DB matches Outlook perfectly")

    # ── 8. Reset sync interval to 15 min ────────────────────────────────
    current_interval = watcher.get("sync_interval_minutes")
    if current_interval != 15:
        logger.info(
            f"Resetting sync_interval_minutes from {current_interval} to 15 ..."
        )
        if not DRY_RUN:
            supabase.table("email_watchers").update(
                {"sync_interval_minutes": 15}
            ).eq("id", watcher_id).execute()
            logger.info("  ✓ sync_interval_minutes = 15")
    else:
        logger.info("sync_interval_minutes already 15 — no change")

    logger.info("Reconciliation complete.")


if __name__ == "__main__":
    asyncio.run(main())
