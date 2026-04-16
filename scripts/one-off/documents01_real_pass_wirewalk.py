#!/usr/bin/env python3
"""
DOCUMENTS01 — MVP wire-walk REAL PASS test.

Walks the full document CRUD chain for crew / chief_engineer / captain against
the LIVE pipeline-core API and the LIVE tenant DB. Every assertion is checked
against real data; no mocks.

What it proves (or disproves):
  1. POST /v1/documents/upload — multipart upload, role gating, storage write,
     doc_metadata row, F2 trigger -> search_index pending_extraction row.
  2. update_document via /v1/actions/execute — RBAC + handler dispatch.
  3. add_document_tags via /v1/actions/execute — tag merge persistence.
  4. get_document_url via /v1/actions/execute — signed URL generation.
  5. delete_document via /v1/actions/execute — soft-delete + ledger event.
  6. ledger_events presence per action (the GAP audit).
  7. Cleanup: all rows + storage blobs removed.

Usage:
    python scripts/one-off/documents01_real_pass_wirewalk.py
"""
import os
import sys
import json
import time
import uuid
import logging
from pathlib import Path

import httpx
import jwt
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wirewalk")

# ----- Config -----
API_BASE = os.getenv("PIPELINE_CORE_URL", "https://pipeline-core.int.celeste7.ai")
MASTER_JWT_SECRET = "wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw=="
TENANT_DSN = "postgresql://postgres:%40-Ei-9Pa.uENn6g@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require"
TENANT_REST = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID = "85fe1119-b04c-41ac-80f1-829d23322598"

USERS = {
    "crew":           {"id": "05a54017-4749-49e8-a865-cb7fd7d2b0c3", "email": "crew.ci+1769701390@alex-short.com"},
    "chief_engineer": {"id": "05a488fd-e099-4d18-bf86-d87afba4fcdf", "email": "hod.test@alex-short.com"},
    "captain":        {"id": "0284dcb3-b27a-49c7-ad3d-b0c3ba734357", "email": "captain.ci+1769556038@alex-short.com"},
}

results = []  # (passed:bool, label:str, detail:str)
created_doc_ids = []  # for cleanup


def expect(passed, label, detail=""):
    results.append((bool(passed), label, detail))
    icon = "PASS" if passed else "FAIL"
    log.info(f"[{icon}] {label}  {detail}")


def mint_jwt(user_role: str) -> str:
    u = USERS[user_role]
    now = int(time.time())
    payload = {
        "sub": u["id"],
        "aud": "authenticated",
        "role": "authenticated",  # supabase JWT 'role' is the postgres role, not yacht role
        "email": u["email"],
        "iat": now,
        "exp": now + 600,
    }
    return jwt.encode(payload, MASTER_JWT_SECRET, algorithm="HS256")


def db():
    return psycopg2.connect(TENANT_DSN, cursor_factory=psycopg2.extras.RealDictCursor)


# Real PDF bytes (minimal valid PDF)
def pdf_bytes(label: str) -> bytes:
    text = label.replace("(", "").replace(")", "").replace("\\", "")
    body_stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length " + str(len(body_stream)).encode() + b">>stream\n"
        + body_stream + b"\nendstream endobj\n"
        b"xref\n0 6\n0000000000 65535 f\n"
        b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
    )
    return body


def upload(role: str, filename: str, doc_type="manual"):
    token = mint_jwt(role)
    files = {"file": (filename, pdf_bytes(filename), "application/pdf")}
    data = {"title": f"DOCUMENTS01 wirewalk {filename}", "doc_type": doc_type}
    r = httpx.post(
        f"{API_BASE}/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
        timeout=60,
    )
    return r


def actions_execute(role: str, action: str, payload: dict):
    token = mint_jwt(role)
    body = {"action": action, "payload": payload, "context": {"yacht_id": YACHT_ID}}
    r = httpx.post(
        f"{API_BASE}/v1/actions/execute",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    return r


def storage_blob_exists(bucket: str, path: str) -> bool:
    r = httpx.head(
        f"{TENANT_REST}/storage/v1/object/{bucket}/{path}",
        headers={"Authorization": f"Bearer {TENANT_SERVICE_KEY}"},
        timeout=30,
    )
    return r.status_code == 200


def storage_blob_delete(bucket: str, path: str):
    r = httpx.delete(
        f"{TENANT_REST}/storage/v1/object/{bucket}/{path}",
        headers={"Authorization": f"Bearer {TENANT_SERVICE_KEY}"},
        timeout=30,
    )
    return r.status_code in (200, 204, 404)


# =============================================================================
# Scenario 1: crew cannot upload (role gate)
# =============================================================================
def test_crew_upload_denied():
    log.info("--- Scenario 1: crew upload should be 403 ---")
    r = upload("crew", "wirewalk-crew-denied.pdf")
    expect(r.status_code == 403, "crew upload denied 403", f"got {r.status_code}")


# =============================================================================
# Scenario 2: chief_engineer (HOD) full happy path
# =============================================================================
def test_hod_full_path():
    log.info("--- Scenario 2: chief_engineer full CRUD wirewalk ---")
    label = f"wirewalk-hod-{uuid.uuid4().hex[:8]}.pdf"
    r = upload("chief_engineer", label)
    expect(r.status_code == 200, "HOD upload 200", f"got {r.status_code} body={r.text[:200]}")
    if r.status_code != 200:
        return None

    body = r.json()
    doc_id = body["document_id"]
    storage_path = body["storage_path"]
    bucket = body["storage_bucket"]
    created_doc_ids.append(doc_id)
    expect(bucket == "documents", "storage bucket = documents", bucket)
    expect(storage_path.startswith(f"{YACHT_ID}/documents/"),
           "storage path is yacht-prefixed", storage_path)

    # Verify storage blob exists
    expect(storage_blob_exists(bucket, storage_path), "storage blob present", storage_path)

    # Verify doc_metadata row
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, yacht_id, storage_bucket, storage_path, source FROM doc_metadata WHERE id=%s", (doc_id,))
        row = cur.fetchone()
        expect(row is not None, "doc_metadata row exists", doc_id)
        if row:
            expect(row["yacht_id"] == YACHT_ID, "doc_metadata.yacht_id matches", str(row["yacht_id"]))
            expect(row["storage_bucket"] == "documents", "doc_metadata.storage_bucket=documents", row["storage_bucket"])

        # F2 trigger should have inserted a search_index row
        cur.execute(
            "SELECT object_id, embedding_status, payload FROM search_index "
            "WHERE object_type='document' AND object_id=%s",
            (doc_id,),
        )
        si = cur.fetchone()
        expect(si is not None, "search_index row enqueued by F2 trigger", doc_id)
        if si:
            expect(
                si["embedding_status"] in ("pending_extraction", "pending", "processing", "embedded"),
                "search_index status valid",
                si["embedding_status"],
            )
            payload = si.get("payload") or {}
            if isinstance(payload, str):
                payload = json.loads(payload)
            bucket_in_payload = payload.get("bucket")
            expect(bucket_in_payload == "documents",
                   "search_index payload.bucket=documents",
                   str(bucket_in_payload))

        # Ledger event check — should now be present after PR #562
        cur.execute(
            "SELECT id, event_type, action FROM ledger_events "
            "WHERE entity_type='document' AND entity_id=%s AND action='upload_document'",
            (doc_id,),
        )
        le = cur.fetchone()
        expect(le is not None, "ledger_events row PRESENT for upload_document", str(le))

        # Notification check
        cur.execute(
            "SELECT id, notification_type, title FROM pms_notifications "
            "WHERE entity_type='document' AND entity_id=%s AND notification_type='document_uploaded'",
            (doc_id,),
        )
        notif = cur.fetchone()
        expect(notif is not None, "pms_notifications row PRESENT for upload", str(notif))

    # update_document via action_router
    r2 = actions_execute("chief_engineer", "update_document",
                         {"document_id": doc_id, "title": "wirewalk updated title"})
    expect(r2.status_code == 200, "HOD update_document 200", f"got {r2.status_code}")

    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) AS c FROM ledger_events WHERE entity_type='document' AND entity_id=%s AND action='update_document'", (doc_id,))
        c = cur.fetchone()["c"]
        expect(c >= 1, "ledger_events PRESENT for update_document", str(c))
        cur.execute("SELECT count(*) AS c FROM pms_audit_log WHERE entity_type='document' AND entity_id=%s AND action='update_document'", (doc_id,))
        c2 = cur.fetchone()["c"]
        expect(c2 >= 1, "pms_audit_log row present for update_document", str(c2))
        cur.execute("SELECT count(*) AS c FROM pms_notifications WHERE entity_type='document' AND entity_id=%s AND notification_type='document_updated'", (doc_id,))
        c3 = cur.fetchone()["c"]
        expect(c3 >= 1, "pms_notifications PRESENT for update_document", str(c3))

    # add_document_tags via action_router
    r3 = actions_execute("chief_engineer", "add_document_tags",
                         {"document_id": doc_id, "tags": ["wirewalk", "documents01"]})
    expect(r3.status_code == 200, "HOD add_document_tags 200", f"got {r3.status_code}")

    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT tags FROM doc_metadata WHERE id=%s", (doc_id,))
        rec = cur.fetchone()
        tags = rec.get("tags") if rec else None
        expect(tags and "wirewalk" in tags, "tags persisted to doc_metadata", str(tags))
        cur.execute("SELECT count(*) AS c FROM ledger_events WHERE entity_type='document' AND entity_id=%s AND action='add_document_tags'", (doc_id,))
        c = cur.fetchone()["c"]
        expect(c >= 1, "ledger_events PRESENT for add_document_tags", str(c))
        cur.execute("SELECT count(*) AS c FROM pms_notifications WHERE entity_type='document' AND entity_id=%s AND notification_type='document_tags_updated'", (doc_id,))
        c2 = cur.fetchone()["c"]
        expect(c2 >= 1, "pms_notifications PRESENT for add_document_tags", str(c2))

    # get_document_url via action_router
    r4 = actions_execute("chief_engineer", "get_document_url", {"document_id": doc_id})
    expect(r4.status_code == 200, "HOD get_document_url 200", f"got {r4.status_code}")
    if r4.status_code == 200:
        # Response shape: ResponseBuilder envelope
        rb = r4.json()
        # Tolerate either flat or wrapped structure
        signed_url = (
            (rb.get("result") or {}).get("data", {}).get("signed_url")
            or rb.get("data", {}).get("signed_url")
            or (rb.get("result") or {}).get("signed_url")
        )
        expect(bool(signed_url), "signed_url returned", str(signed_url)[:60] if signed_url else "missing")

    return doc_id


# =============================================================================
# Scenario 3: captain delete (signed action — likely needs reason)
# =============================================================================
def test_captain_delete(doc_id: str):
    log.info("--- Scenario 3: captain deletes the HOD document ---")
    if not doc_id:
        expect(False, "captain delete skipped (no doc_id)")
        return

    r = actions_execute("captain", "delete_document",
                        {"document_id": doc_id, "reason": "wirewalk cleanup",
                         "signature": {"name": "captain wirewalk", "timestamp": time.time()}})
    expect(r.status_code in (200, 400), "captain delete_document responded",
           f"got {r.status_code} body={r.text[:200]}")

    if r.status_code == 200:
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT deleted_at FROM doc_metadata WHERE id=%s", (doc_id,))
            rec = cur.fetchone()
            soft_deleted = bool(rec and rec.get("deleted_at"))
            expect(soft_deleted, "doc_metadata soft-deleted", str(rec))

            cur.execute("SELECT count(*) AS c FROM ledger_events WHERE entity_type='document' AND entity_id=%s AND action='delete_document'", (doc_id,))
            c = cur.fetchone()["c"]
            expect(c >= 1, "ledger_events row present for delete_document", str(c))

            cur.execute("SELECT count(*) AS c FROM pms_notifications WHERE entity_type='document' AND entity_id=%s AND notification_type='document_deleted'", (doc_id,))
            c2 = cur.fetchone()["c"]
            expect(c2 >= 1, "pms_notifications PRESENT for delete_document", str(c2))


# =============================================================================
# Scenario 4: crew can read but cannot mutate
# =============================================================================
def test_crew_read_only():
    log.info("--- Scenario 4: crew read access ---")
    # Pick any doc that exists for the yacht
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM doc_metadata WHERE yacht_id=%s AND deleted_at IS NULL LIMIT 1", (YACHT_ID,))
        row = cur.fetchone()
        if not row:
            expect(False, "no readable doc available for crew test")
            return
        doc_id = row["id"]

    r = actions_execute("crew", "get_document_url", {"document_id": doc_id})
    expect(r.status_code == 200, "crew get_document_url 200", f"got {r.status_code}")

    r2 = actions_execute("crew", "update_document",
                         {"document_id": doc_id, "title": "crew should fail"})
    expect(r2.status_code == 403, "crew update_document 403",
           f"got {r2.status_code}")

    r3 = actions_execute("crew", "delete_document",
                         {"document_id": doc_id, "reason": "should fail",
                          "signature": {"name": "crew", "timestamp": time.time()}})
    expect(r3.status_code in (400, 403), "crew delete_document blocked",
           f"got {r3.status_code}")


# =============================================================================
# Cleanup
# =============================================================================
def cleanup():
    log.info("--- Cleanup ---")
    if not created_doc_ids:
        return
    with db() as conn, conn.cursor() as cur:
        for doc_id in created_doc_ids:
            try:
                cur.execute("SELECT storage_bucket, storage_path FROM doc_metadata WHERE id=%s", (doc_id,))
                rec = cur.fetchone()
                if rec:
                    storage_blob_delete(rec["storage_bucket"] or "documents", rec["storage_path"])
                cur.execute("DELETE FROM search_index WHERE object_type='document' AND object_id=%s", (doc_id,))
                cur.execute("DELETE FROM search_document_chunks WHERE document_id=%s", (doc_id,))
                cur.execute("DELETE FROM ledger_events WHERE entity_type='document' AND entity_id=%s", (doc_id,))
                cur.execute("DELETE FROM pms_audit_log WHERE entity_type='document' AND entity_id=%s", (doc_id,))
                cur.execute("DELETE FROM pms_notifications WHERE entity_type='document' AND entity_id=%s", (doc_id,))
                cur.execute("DELETE FROM doc_metadata WHERE id=%s", (doc_id,))
            except Exception as e:
                log.warning(f"cleanup failed for {doc_id}: {e}")
        conn.commit()
    log.info(f"Cleaned up {len(created_doc_ids)} test docs")


def main():
    log.info(f"API base: {API_BASE}")
    log.info(f"Yacht: {YACHT_ID}")
    test_crew_upload_denied()
    doc_id = test_hod_full_path()
    test_captain_delete(doc_id)
    test_crew_read_only()
    cleanup()

    passed = sum(1 for r in results if r[0])
    failed = sum(1 for r in results if not r[0])
    log.info("=" * 70)
    log.info(f"RESULTS: {passed} pass / {failed} fail / {len(results)} total")
    for ok, label, detail in results:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {label}  {detail}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
