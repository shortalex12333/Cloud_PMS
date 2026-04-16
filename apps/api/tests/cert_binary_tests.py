"""
Certificate domain — binary verification tests.
Each test: setup → call → query DB → PASS or FAIL (no middle ground).

LEDGER NOTE: Handlers do NOT write ledger_events directly. The Phase B
safety net at p0_actions_routes.py:1137 writes a generic ledger event
using ACTION_METADATA when handler response lacks _ledger_written=True.
Since these tests call handlers directly (bypassing the route), ledger
writes cannot be tested here. Test T-META verifies all cert actions have
ACTION_METADATA entries, proving the safety net WILL fire on the real
wire path. Full ledger verification requires a live API call through
p0_actions_routes — see T-LEDGER section.
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
# _cert_mutation_gate requires user_context with role for domain-based narrowing
USER_CTX  = {"role": "captain", "user_id": USER_ID}

import os
os.environ.setdefault("SUPABASE_URL", TENANT_URL)
os.environ.setdefault("SUPABASE_SERVICE_KEY", TENANT_KEY)
os.environ.setdefault("yTEST_YACHT_001_SUPABASE_URL", TENANT_URL)
os.environ.setdefault("yTEST_YACHT_001_SUPABASE_SERVICE_KEY", TENANT_KEY)

from supabase import create_client
db = create_client(TENANT_URL, TENANT_KEY)

sys.path.insert(0, '/Users/celeste7/Documents/Cloud_PMS/apps/api')
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
    r = db.table("pms_vessel_certificates").select("*").eq("id", cert_id).limit(1).execute()
    rows = getattr(r, "data", None) or []
    return rows[0] if rows else None

def get_crew(cert_id):
    r = db.table("pms_crew_certificates").select("*").eq("id", cert_id).limit(1).execute()
    rows = getattr(r, "data", None) or []
    return rows[0] if rows else None

def get_notes_for_cert(cert_id):
    return db.table("pms_notes").select("*").eq("certificate_id", cert_id).execute().data

def get_audit(cert_id):
    return db.table("pms_audit_log").select("*").eq("entity_id", cert_id).execute().data

def get_ledger(cert_id):
    return db.table("ledger_events").select("*").eq("entity_id", cert_id).execute().data

def cleanup(*ids_and_tables):
    """Delete test rows. Also cleans audit_log and notes."""
    for table, id_ in ids_and_tables:
        try:
            db.table(table).delete().eq("id", id_).execute()
        except Exception:
            pass
        try:
            db.table("pms_audit_log").delete().eq("entity_id", id_).execute()
        except Exception:
            pass
        try:
            db.table("pms_notes").delete().eq("certificate_id", id_).execute()
        except Exception:
            pass


# ─── TEST 1: renew_certificate ──────────────────────────────────────────────
# Handler: certificate_handlers.py → _renew_certificate_adapter
# Wire: entity_actions.py → registry.py:3703 → internal_dispatcher.py:4200
print("\nT1: renew_certificate")
old_id = make_vessel_cert()
try:
    result = asyncio.run(handlers["renew_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        certificate_id=old_id,
        new_issue_date="2026-02-01",
        new_expiry_date="2027-02-01",
    ))
    new_id = result.get("renewed_certificate_id")
    old_row = get_vessel(old_id)
    record("T1a: old cert status = superseded",
           old_row and old_row["status"] == "superseded",
           f"status={old_row and old_row['status']}")
    new_row = get_vessel(new_id) if new_id else None
    record("T1b: new cert exists with new_expiry_date",
           new_row and new_row["expiry_date"] == "2027-02-01" and new_row["status"] == "valid",
           f"new_row exists={new_row is not None}, expiry={new_row and new_row.get('expiry_date')}")
    audit = get_audit(old_id)
    record("T1c: audit log entry written",
           any(a["action"] == "renew_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_vessel_certificates", old_id))
    if new_id:
        cleanup(("pms_vessel_certificates", new_id))
except Exception as e:
    record("T1: renew_certificate raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", old_id))


# ─── TEST 2: suspend_certificate (vessel) ───────────────────────────────────
# Handler: certificate_handlers.py:1332 → _change_certificate_status_adapter("suspended")
# Wire: internal_dispatcher.py:4207 → _cert_suspend
print("\nT2: suspend_certificate (vessel)")
cert_id = make_vessel_cert()
try:
    asyncio.run(handlers["suspend_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        entity_id=cert_id,
        reason="Test suspension",
        signature={"signer": USER_ID, "method": "test"},
    ))
    row = get_vessel(cert_id)
    record("T2a: vessel cert status = suspended",
           row and row["status"] == "suspended",
           f"status={row and row['status']}")
    # Verify properties contain suspension metadata
    props = (row or {}).get("properties") or {}
    record("T2b: properties.suspended_reason set",
           props.get("suspended_reason") == "Test suspension",
           f"suspended_reason={props.get('suspended_reason')}")
    audit = get_audit(cert_id)
    record("T2c: audit log written with old/new values",
           any(a["action"] == "suspended_certificate" and
               a.get("old_values", {}).get("status") == "valid" and
               a.get("new_values", {}).get("status") == "suspended"
               for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_vessel_certificates", cert_id))
except Exception as e:
    record("T2: suspend raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 3: revoke_certificate (crew) ──────────────────────────────────────
# Handler: certificate_handlers.py:1332 → _change_certificate_status_adapter("revoked")
# Wire: internal_dispatcher.py:4208 → _cert_revoke
print("\nT3: revoke_certificate (crew cert)")
crew_id = make_crew_cert()
try:
    asyncio.run(handlers["revoke_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        entity_id=crew_id,
        reason="Test revocation",
        signature={"signer": USER_ID, "method": "test"},
    ))
    row = get_crew(crew_id)
    record("T3a: crew cert status = revoked",
           row and row["status"] == "revoked",
           f"status={row and row['status']}")
    props = (row or {}).get("properties") or {}
    record("T3b: properties.revoked_reason set",
           props.get("revoked_reason") == "Test revocation",
           f"revoked_reason={props.get('revoked_reason')}")
    audit = get_audit(crew_id)
    record("T3c: audit log written",
           any(a["action"] == "revoked_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_crew_certificates", crew_id))
except Exception as e:
    record("T3: revoke raised exception", False, str(e))
    cleanup(("pms_crew_certificates", crew_id))


# ─── TEST 4: archive_certificate — vessel ───────────────────────────────────
# Handler: certificate_handlers.py:1397 → _archive_certificate_adapter
# Wire: internal_dispatcher.py:4206 → _cert_archive
print("\nT4: archive_certificate (vessel)")
cert_id = make_vessel_cert()
try:
    asyncio.run(handlers["archive_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        entity_id=cert_id,
    ))
    row = get_vessel(cert_id)
    record("T4a: vessel cert deleted_at is set",
           row and row.get("deleted_at") is not None,
           f"deleted_at={row and row.get('deleted_at')}")
    record("T4b: deleted_by = test user",
           row and row.get("deleted_by") == USER_ID,
           f"deleted_by={row and row.get('deleted_by')}")
    view_row = db.table("v_certificates_enriched").select("id").eq("id", cert_id).execute().data
    record("T4c: archived cert absent from v_certificates_enriched",
           len(view_row) == 0,
           f"view returned {len(view_row)} rows")
    audit = get_audit(cert_id)
    record("T4d: audit log written for archive",
           any(a["action"] == "archive_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
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
        user_context=USER_CTX,
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
    audit = get_audit(crew_id)
    record("T5c: audit log written for archive",
           any(a["action"] == "archive_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_crew_certificates", crew_id))
except Exception as e:
    record("T5: archive crew raised exception", False, str(e))
    cleanup(("pms_crew_certificates", crew_id))


# ─── TEST 6: add_certificate_note ───────────────────────────────────────────
# Handler: internal_dispatcher.py:175 → add_note (shared handler)
# Wire: internal_dispatcher.py:4178 → "add_certificate_note": add_note
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
    record("T6a: note row exists with certificate_id FK set",
           len(notes) == 1 and notes[0]["certificate_id"] == cert_id,
           f"count={len(notes)}, fk={notes[0].get('certificate_id') if notes else None}")
    record("T6b: note text matches input",
           len(notes) == 1 and notes[0]["text"] == "Binary verification test note",
           f"text={notes[0]['text'] if notes else None}")
    record("T6c: note yacht_id scoped correctly",
           len(notes) == 1 and notes[0]["yacht_id"] == YACHT_ID,
           f"yacht_id={notes[0].get('yacht_id') if notes else None}")
    cleanup(("pms_vessel_certificates", cert_id))
except Exception as e:
    record("T6: add_note raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 7: refresh_certificate_expiry ─────────────────────────────────────
# DB function: refresh_certificate_expiry(p_yacht_id uuid)
# Worker: workers/nightly_certificate_expiry.py → render.yaml cron at 02:15 UTC
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
    # The DB function writes ledger_events directly (not via handler safety net)
    ledger = get_ledger(expired_id)
    record("T7c: ledger_events row written for vessel expiry",
           any(e.get("event_type") == "status_change" for e in ledger),
           f"ledger_count={len(ledger)}, types={[e.get('event_type') for e in ledger]}")
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
        user_context=USER_CTX,
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


# ─── TEST 9: create_vessel_certificate ───────────────────────────────────────
# Handler: certificate_handlers.py:744 → _create_vessel_certificate_adapter
# Wire: certificate_phase4_handler.py:100 → CERT_HANDLERS → _ACTION_HANDLERS
print("\nT9: create_vessel_certificate")
try:
    result = asyncio.run(handlers["create_vessel_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        certificate_type="SAFETY_RADIO",
        certificate_name="Test Radio Safety Certificate",
        issuing_authority="Maritime Authority",
        certificate_number=f"RSC-{uuid.uuid4().hex[:6]}",
        issue_date="2026-01-01",
        expiry_date="2027-06-01",
    ))
    new_id = result.get("certificate_id") or result.get("id")
    row = get_vessel(new_id) if new_id else None
    record("T9a: vessel cert row created in pms_vessel_certificates",
           row is not None,
           f"id={new_id}, row_exists={row is not None}")
    record("T9b: certificate_name matches input",
           row and row.get("certificate_name") == "Test Radio Safety Certificate",
           f"name={row and row.get('certificate_name')}")
    record("T9c: status defaults to valid",
           row and row.get("status") in ("valid", "active"),
           f"status={row and row.get('status')}")
    record("T9d: yacht_id scoped correctly",
           row and row.get("yacht_id") == YACHT_ID,
           f"yacht_id={row and row.get('yacht_id')}")
    if new_id:
        cleanup(("pms_vessel_certificates", new_id))
except Exception as e:
    record("T9: create_vessel_certificate raised exception", False, str(e))


# ─── TEST 10: create_crew_certificate ────────────────────────────────────────
# Handler: certificate_handlers.py → _create_crew_certificate_adapter
print("\nT10: create_crew_certificate")
try:
    result = asyncio.run(handlers["create_crew_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        person_name="John Testcrew",
        certificate_type="STCW_BST",
        issuing_authority="UK MCA",
        certificate_number=f"STCW-{uuid.uuid4().hex[:6]}",
        issue_date="2026-01-01",
        expiry_date="2031-01-01",
    ))
    new_id = result.get("certificate_id") or result.get("id")
    row = get_crew(new_id) if new_id else None
    record("T10a: crew cert row created in pms_crew_certificates",
           row is not None,
           f"id={new_id}, row_exists={row is not None}")
    record("T10b: person_name matches input",
           row and row.get("person_name") == "John Testcrew",
           f"person_name={row and row.get('person_name')}")
    if new_id:
        view = db.table("v_certificates_enriched").select("id, domain").eq("id", new_id).execute().data
        record("T10c: appears in v_certificates_enriched with domain=crew",
               len(view) == 1 and view[0].get("domain") == "crew",
               f"view_rows={len(view)}, domain={view[0].get('domain') if view else None}")
        cleanup(("pms_crew_certificates", new_id))
    else:
        record("T10c: no id returned, cannot verify view", False, f"result={result}")
except Exception as e:
    record("T10: create_crew_certificate raised exception", False, str(e))


# ─── TEST 11: assign_certificate ─────────────────────────────────────────────
# Handler: certificate_handlers.py:1450 → _assign_certificate_adapter
# Wire: internal_dispatcher.py:4210 → _cert_assign
print("\nT11: assign_certificate")
cert_id = make_vessel_cert()
try:
    asyncio.run(handlers["assign_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        certificate_id=cert_id,
        assigned_to=USER_ID,
        assigned_to_name="Chief Engineer Test",
    ))
    row = get_vessel(cert_id)
    props = (row or {}).get("properties") or {}
    record("T11a: properties.assigned_to set to user_id",
           props.get("assigned_to") == USER_ID,
           f"assigned_to={props.get('assigned_to')}")
    record("T11b: properties.assigned_to_name set",
           props.get("assigned_to_name") == "Chief Engineer Test",
           f"assigned_to_name={props.get('assigned_to_name')}")
    audit = get_audit(cert_id)
    record("T11c: audit log written for assignment",
           any(a["action"] == "assign_certificate" for a in audit),
           f"audit_actions={[a['action'] for a in audit]}")
    cleanup(("pms_vessel_certificates", cert_id))
except Exception as e:
    record("T11: assign_certificate raised exception", False, str(e))
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 12: suspend blocked on terminal cert ──────────────────────────────
print("\nT12: suspend rejected on revoked cert (guard)")
cert_id = make_vessel_cert({"status": "revoked"})
try:
    asyncio.run(handlers["suspend_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        entity_id=cert_id,
        reason="Should not work",
    ))
    record("T12: suspend on revoked should have raised ValueError", False, "No exception")
except ValueError as e:
    record("T12: suspend correctly rejected on revoked cert", True, str(e))
except Exception as e:
    record("T12: wrong exception type", False, str(e))
finally:
    cleanup(("pms_vessel_certificates", cert_id))


# ─── TEST 13: revoke blocked on already-revoked cert ────────────────────────
print("\nT13: revoke rejected on already-revoked cert (guard)")
cert_id = make_crew_cert({"status": "revoked"})
try:
    asyncio.run(handlers["revoke_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context=USER_CTX,
        entity_id=cert_id,
        reason="Should not work",
    ))
    record("T13: revoke on revoked should have raised ValueError", False, "No exception")
except ValueError as e:
    record("T13: revoke correctly rejected on already-revoked cert", True, str(e))
except Exception as e:
    record("T13: wrong exception type", False, str(e))
finally:
    cleanup(("pms_crew_certificates", cert_id))


# ─── TEST 14: mutation gate — engineer blocked from crew cert ────────────────
print("\nT14: mutation gate — engineer cannot archive crew cert")
crew_id = make_crew_cert()
try:
    asyncio.run(handlers["archive_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context={"role": "engineer", "user_id": USER_ID},
        entity_id=crew_id,
    ))
    record("T14: engineer should be blocked from crew cert", False, "No exception")
except ValueError as e:
    record("T14: engineer correctly blocked from crew cert", True, str(e))
except Exception as e:
    record("T14: wrong exception type", False, str(e))
finally:
    cleanup(("pms_crew_certificates", crew_id))


# ─── TEST 15: mutation gate — purser blocked from vessel cert ────────────────
print("\nT15: mutation gate — purser cannot archive vessel cert")
cert_id = make_vessel_cert()
try:
    asyncio.run(handlers["archive_certificate"](
        yacht_id=YACHT_ID,
        user_id=USER_ID,
        user_context={"role": "purser", "user_id": USER_ID},
        entity_id=cert_id,
    ))
    record("T15: purser should be blocked from vessel cert", False, "No exception")
except ValueError as e:
    record("T15: purser correctly blocked from vessel cert", True, str(e))
except Exception as e:
    record("T15: wrong exception type", False, str(e))
finally:
    cleanup(("pms_vessel_certificates", cert_id))


# ─── T-META: ACTION_METADATA coverage (ledger safety net prerequisite) ──────
# This verifies that the Phase B safety net at p0_actions_routes.py:1137 WILL
# write a ledger_events row for every cert action when called through the API.
# It does NOT verify the row was actually written — that requires a live API call.
print("\nT-META: ACTION_METADATA coverage for all cert actions")
try:
    from action_router.ledger_metadata import ACTION_METADATA
    CERT_ACTIONS = [
        "add_certificate_note", "archive_certificate", "assign_certificate",
        "create_vessel_certificate", "create_crew_certificate",
        "link_document_to_certificate", "renew_certificate",
        "revoke_certificate", "supersede_certificate",
        "suspend_certificate", "update_certificate",
    ]
    missing = [a for a in CERT_ACTIONS if a not in ACTION_METADATA]
    record("T-META-a: all 11 cert actions have ACTION_METADATA entries",
           len(missing) == 0,
           f"missing={missing}")
    # Verify entity_type is always "certificate"
    wrong_type = [a for a in CERT_ACTIONS if a in ACTION_METADATA
                  and ACTION_METADATA[a].get("entity_type") != "certificate"]
    record("T-META-b: all entries have entity_type=certificate",
           len(wrong_type) == 0,
           f"wrong_type={wrong_type}")
except Exception as e:
    record("T-META: import failed", False, str(e))


# ─── T-ROLE: registry allowed_roles widened per MVP spec ─────────────────────
print("\nT-ROLE: allowed_roles widened per MVP spec")
try:
    from action_router.registry import ACTION_REGISTRY
    FULL_8_HOD = {"engineer", "eto", "chief_engineer", "chief_officer",
                  "purser", "chief_steward", "captain", "manager"}
    actions_to_check = [
        "create_vessel_certificate", "create_crew_certificate",
        "update_certificate", "assign_certificate",
        "link_document_to_certificate", "add_certificate_note",
        "archive_certificate", "renew_certificate",
    ]
    for action_id in actions_to_check:
        defn = ACTION_REGISTRY.get(action_id)
        if not defn:
            record(f"T-ROLE: {action_id} missing from registry", False, "not found")
            continue
        roles_set = set(defn.allowed_roles)
        # For create_vessel: engineering+deck+captain+manager (no purser/chief_steward)
        if action_id == "create_vessel_certificate":
            expected = {"engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"}
            ok = roles_set == expected
        elif action_id == "create_crew_certificate":
            expected = {"chief_engineer", "chief_officer", "purser", "chief_steward", "captain", "manager"}
            ok = roles_set == expected
        else:
            ok = roles_set == FULL_8_HOD
        record(f"T-ROLE: {action_id} roles correct",
               ok, f"expected={'subset' if not ok else 'match'}, got={sorted(roles_set)}")
except Exception as e:
    record("T-ROLE: registry import failed", False, str(e))


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
    print("NOTE: Ledger writes verified by architecture (T-META), not by")
    print("      direct DB assertion. Full ledger wire-walk requires live")
    print("      API call through p0_actions_routes.py (not handler-direct).")
