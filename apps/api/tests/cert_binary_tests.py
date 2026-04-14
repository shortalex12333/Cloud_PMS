"""
Certificate domain — binary verification tests.
Each test: setup → call → query DB → PASS or FAIL (no middle ground).
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, date, timedelta

# Wire the tenant supabase client directly with service key
TENANT_URL = "https://vzsohavtuotocgrfkfyd.supabase.co"
TENANT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY"
YACHT_ID  = "85fe1119-b04c-41ac-80f1-829d23322598"
USER_ID   = "00000000-0000-0000-0000-000000000001"  # synthetic test user

from supabase import create_client
db = create_client(TENANT_URL, TENANT_KEY)

sys.path.insert(0, '/Users/celeste7/Documents/CLOUD_PMS/apps/api')
from handlers.certificate_handlers import get_certificate_handlers
handlers = get_certificate_handlers(db)

results = []

def record(name, passed, evidence):
    mark = "PASS" if passed else "FAIL"
    results.append((name, passed, evidence))
    print(f"  [{mark}] {name}")
    if not passed:
        print(f"         Evidence: {evidence}")


# ─── HELPERS ────────────────────────────────────────────────────────────────

def make_vessel_cert(extra=None):
    """Insert a test vessel cert, return its id."""
    payload = {
        "yacht_id": YACHT_ID,
        "certificate_type": "TEST",
        "certificate_name": f"Test Cert {uuid.uuid4().hex[:8]}",
        "issuing_authority": "Test Authority",
        "issue_date": "2025-01-01",
        "expiry_date": "2026-01-01",
        "status": "valid",
        "source": "manual",
        "is_seed": False,
    }
    if extra:
        payload.update(extra)
    r = db.table("pms_vessel_certificates").insert(payload).execute()
    return r.data[0]["id"]

def make_crew_cert(extra=None):
    """Insert a test crew cert, return its id."""
    payload = {
        "yacht_id": YACHT_ID,
        "person_name": f"Test Crew {uuid.uuid4().hex[:6]}",
        "certificate_type": "TEST_CREW",
        "issuing_authority": "Test Authority",
        "issue_date": "2025-01-01",
        "expiry_date": "2026-01-01",
        "status": "valid",
    }
    if extra:
        payload.update(extra)
    r = db.table("pms_crew_certificates").insert(payload).execute()
    return r.data[0]["id"]

def get_vessel(cert_id):
    return db.table("pms_vessel_certificates").select("*").eq("id", cert_id).maybe_single().execute().data

def get_crew(cert_id):
    return db.table("pms_crew_certificates").select("*").eq("id", cert_id).maybe_single().execute().data

def get_notes_for_cert(cert_id):
    return db.table("pms_notes").select("*").eq("certificate_id", cert_id).execute().data

def get_audit(cert_id):
    return db.table("pms_audit_log").select("*").eq("entity_id", cert_id).execute().data

def cleanup(*ids_and_tables):
    """Delete test rows."""
    for table, id_ in ids_and_tables:
        try:
            db.table(table).delete().eq("id", id_).execute()
        except Exception:
            pass


# ─── TEST 1: renew_certificate ──────────────────────────────────────────────
print("\nT1: renew_certificate")
old_id = make_vessel_cert()
try:
    result = asyncio.run(handlers["renew_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        certificate_id=old_id,
        new_issue_date="2026-02-01",
        new_expiry_date="2027-02-01",
    ))
    new_id = result.get("renewed_certificate_id")
    # Verify 1: old cert is now superseded
    old_row = get_vessel(old_id)
    record("T1a: old cert status = superseded",
           old_row and old_row["status"] == "superseded",
           f"status={old_row and old_row['status']}")
    # Verify 2: new cert exists with correct expiry
    new_row = get_vessel(new_id) if new_id else None
    record("T1b: new cert exists with new_expiry_date",
           new_row and new_row["expiry_date"] == "2027-02-01" and new_row["status"] == "valid",
           f"new_row={new_row}")
    # Verify 3: audit log written
    audit = get_audit(old_id)
    record("T1c: audit log entry written",
           any(a["action"] == "renew_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_vessel_certificates", old_id), ("pms_vessel_certificates", new_id))
except Exception as e:
    record("T1: renew_certificate raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", old_id))


# ─── TEST 2: suspend_certificate (vessel) ───────────────────────────────────
print("\nT2: suspend_certificate (vessel)")
cert_id = make_vessel_cert()
try:
    asyncio.run(handlers["suspend_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        entity_id=cert_id,
        reason="Test suspension",
        signature={"signer": USER_ID, "method": "test"},
    ))
    row = get_vessel(cert_id)
    record("T2a: vessel cert status = suspended",
           row and row["status"] == "suspended",
           f"status={row and row['status']}")
    audit = get_audit(cert_id)
    record("T2b: audit log written",
           any(a["action"] == "suspended_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_vessel_certificates", cert_id))
except Exception as e:
    record("T2: suspend raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 3: revoke_certificate (crew) ──────────────────────────────────────
print("\nT3: revoke_certificate (crew cert)")
crew_id = make_crew_cert()
try:
    asyncio.run(handlers["revoke_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        entity_id=crew_id,
        reason="Test revocation",
        signature={"signer": USER_ID, "method": "test"},
    ))
    row = get_crew(crew_id)
    record("T3a: crew cert status = revoked",
           row and row["status"] == "revoked",
           f"status={row and row['status']}")
    audit = get_audit(crew_id)
    record("T3b: audit log written",
           any(a["action"] == "revoked_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_crew_certificates", crew_id))
except Exception as e:
    record("T3: revoke raised exception", False, str(e))
    cleanup(("pms_crew_certificates", crew_id))


# ─── TEST 4: archive_certificate — vessel ───────────────────────────────────
print("\nT4: archive_certificate (vessel)")
cert_id = make_vessel_cert()
try:
    asyncio.run(handlers["archive_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        entity_id=cert_id,
    ))
    row = get_vessel(cert_id)
    record("T4a: vessel cert deleted_at is set",
           row and row.get("deleted_at") is not None,
           f"deleted_at={row and row.get('deleted_at')}")
    # Verify it does NOT appear in v_certificates_enriched
    view_row = db.table("v_certificates_enriched").select("id").eq("id", cert_id).execute().data
    record("T4b: archived cert absent from v_certificates_enriched",
           len(view_row) == 0,
           f"view returned {len(view_row)} rows")
    cleanup(("pms_vessel_certificates", cert_id))
except Exception as e:
    record("T4: archive vessel raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 5: archive_certificate — crew ─────────────────────────────────────
print("\nT5: archive_certificate (crew)")
crew_id = make_crew_cert()
try:
    asyncio.run(handlers["archive_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        entity_id=crew_id,
    ))
    row = get_crew(crew_id)
    record("T5a: crew cert deleted_at is set",
           row and row.get("deleted_at") is not None,
           f"deleted_at={row and row.get('deleted_at')}")
    view_row = db.table("v_certificates_enriched").select("id").eq("id", crew_id).execute().data
    record("T5b: archived crew cert absent from view",
           len(view_row) == 0,
           f"view returned {len(view_row)} rows")
    cleanup(("pms_crew_certificates", crew_id))
except Exception as e:
    record("T5: archive crew raised exception", False, str(e))
    cleanup(("pms_crew_certificates", crew_id))


# ─── TEST 6: add_certificate_note ───────────────────────────────────────────
print("\nT6: add_certificate_note")
cert_id = make_vessel_cert()
try:
    from action_router.dispatchers.internal_dispatcher import add_note
    asyncio.run(add_note({
        "yacht_id": YACHT_ID,
        "user_id": USER_ID,
        "certificate_id": cert_id,
        "note_text": "Binary verification test note",
    }))
    notes = get_notes_for_cert(cert_id)
    record("T6a: note row exists with certificate_id set",
           len(notes) == 1 and notes[0]["certificate_id"] == cert_id,
           f"notes={notes}")
    record("T6b: note text is correct",
           len(notes) == 1 and notes[0]["text"] == "Binary verification test note",
           f"text={notes[0]['text'] if notes else None}")
    for n in notes:
        db.table("pms_notes").delete().eq("id", n["id"]).execute()
    cleanup(("pms_vessel_certificates", cert_id))
except Exception as e:
    record("T6: add_note raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 7: refresh_certificate_expiry ─────────────────────────────────────
print("\nT7: refresh_certificate_expiry")
expired_id = make_vessel_cert({"expiry_date": "2020-01-01", "status": "valid"})
expired_crew_id = make_crew_cert({"expiry_date": "2020-01-01", "status": "valid"})
try:
    db.rpc("refresh_certificate_expiry", {"p_yacht_id": YACHT_ID}).execute()
    vessel_row = get_vessel(expired_id)
    crew_row = get_crew(expired_crew_id)
    record("T7a: past-expiry vessel cert status flipped to expired",
           vessel_row and vessel_row["status"] == "expired",
           f"status={vessel_row and vessel_row['status']}")
    record("T7b: past-expiry crew cert status flipped to expired",
           crew_row and crew_row["status"] == "expired",
           f"status={crew_row and crew_row['status']}")
    cleanup(("pms_vessel_certificates", expired_id), ("pms_crew_certificates", expired_crew_id))
except Exception as e:
    record("T7: refresh_certificate_expiry raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", expired_id), ("pms_crew_certificates", expired_crew_id))


# ─── TEST 8: renew blocked on superseded cert ───────────────────────────────
print("\nT8: renew rejected on superseded cert (guard)")
cert_id = make_vessel_cert({"status": "superseded"})
try:
    asyncio.run(handlers["renew_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        certificate_id=cert_id,
        new_issue_date="2026-01-01",
        new_expiry_date="2027-01-01",
    ))
    record("T8: renew on superseded should have raised ValueError", False, "No exception raised")
except ValueError as e:
    record("T8: renew correctly rejected on superseded cert", True, str(e))
except Exception as e:
    record("T8: wrong exception type raised", False, str(e))
finally:
    cleanup(("pms_vessel_certificates", cert_id))


# ─── SUMMARY ────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, p, _ in results if p)
failed = total - passed

print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} PASS  |  {failed}/{total} FAIL")
print(f"{'='*60}")
if failed:
    print("\nFAILED TESTS:")
    for name, ok, ev in results:
        if not ok:
            print(f"  FAIL  {name}")
            print(f"        {ev}")
    sys.exit(1)
else:
    print("ALL PASS — binary verified against live tenant DB.")
