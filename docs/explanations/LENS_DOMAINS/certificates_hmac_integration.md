# Certificate Domain — HMAC01 Integration Notes

> For: HMAC01 (Receipt Layer architect)
> From: CERTIFICATE01
> Date: 2026-04-16
> Status: MVP wiring complete, ready for adapter contract

---

## 1. Evidence trail — what the certificate domain writes today

### 1.1 Ledger events (tamper-evident chain)

**Writer**: Phase B safety net at `apps/api/routes/p0_actions_routes.py:1137`
**NOT** written by handlers directly. Handlers return a dict, and if `_ledger_written` is not set, the safety net fires using ACTION_METADATA.

**ACTION_METADATA entries** (`apps/api/action_router/ledger_metadata.py:67-78`):

| action_id | event_type | entity_type | entity_id_field |
|-----------|-----------|-------------|-----------------|
| `add_certificate_note` | update | certificate | certificate_id |
| `archive_certificate` | update | certificate | entity_id |
| `assign_certificate` | assignment | certificate | certificate_id |
| `create_vessel_certificate` | create | certificate | certificate_id |
| `create_crew_certificate` | create | certificate | certificate_id |
| `link_document_to_certificate` | update | certificate | certificate_id |
| `renew_certificate` | create | certificate | certificate_id |
| `revoke_certificate` | status_change | certificate | entity_id |
| `supersede_certificate` | status_change | certificate | certificate_id |
| `suspend_certificate` | status_change | certificate | entity_id |
| `update_certificate` | update | certificate | certificate_id |

**Note**: `entity_id_field` varies between `certificate_id` and `entity_id`. The safety net resolves the value from `payload[field] → result[field] → result.id → yacht_id` (see `p0_actions_routes.py:1154-1159`).

**Proof hash**: Written by `build_ledger_event()` in `routes/handlers/ledger_utils.py`. Chain: SHA-256 of `previous_proof_hash + event_type + entity_type + entity_id + timestamp`. Owned by RECEIPT01.

### 1.2 Audit log (domain-specific trail)

**Writer**: Each handler writes to `pms_audit_log` directly.

| Handler | Action column value | Where |
|---------|-------------------|-------|
| `_change_certificate_status_adapter("suspended")` | `"suspended_certificate"` | `certificate_handlers.py:1383` |
| `_change_certificate_status_adapter("revoked")` | `"revoked_certificate"` | same adapter |
| `_archive_certificate_adapter` | `"archive_certificate"` | `certificate_handlers.py:1440` |
| `_renew_certificate_adapter` | `"renew_certificate"` | `certificate_handlers.py:1304` |
| `_assign_certificate_adapter` | `"assign_certificate"` | `certificate_handlers.py:1502` |
| `_create_vessel_certificate_adapter` | `"create_vessel_certificate"` | `certificate_handlers.py:810` |
| `_create_crew_certificate_adapter` | `"create_crew_certificate"` | `certificate_handlers.py:1057` |

**Schema**: `{yacht_id, entity_type="certificate", entity_id, action, user_id, old_values, new_values, signature, metadata, created_at}`

### 1.3 Attachments

**Storage bucket**: `pms-certificate-documents` (Supabase Storage)
**Attachment table**: `pms_attachments` with `entity_type='certificate'` and `entity_id=cert_uuid`
**Single-doc FK**: `pms_vessel_certificates.document_id` → `doc_metadata.id` (for the primary linked document)
**Frontend upload**: `AttachmentUploadModal` in `CertificateContent.tsx:335` with `bucket="pms-certificate-documents"`, `category="certificate"`

### 1.4 Notifications

**Writer**: `_notify_cert_stakeholders()` at `certificate_handlers.py:1583`
**Table**: `pms_notifications`
**Events that trigger**: create (vessel/crew), suspend, revoke, archive
**Recipients**: Department HODs based on cert domain + captain + manager (actor excluded)
**Idempotency**: `cert_{event_type}:{cert_id}:{user_id}` key with upsert

---

## 2. Tables (what records exist)

### 2.1 Source tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `pms_vessel_certificates` | Vessel/machinery/flag certs | id, yacht_id, certificate_name, certificate_type, certificate_number, issuing_authority, issue_date, expiry_date, status, properties, document_id, deleted_at |
| `pms_crew_certificates` | Seafarer/crew certs | id, yacht_id, person_name, person_node_id, certificate_type, certificate_number, issuing_authority, issue_date, expiry_date, status, properties, deleted_at |

> **Note**: The crew member FK column is `person_node_id` (FK to `search_graph_nodes.id`), not `person_id`. Historical naming — functionally correct.

### 2.2 Unified view

`v_certificates_enriched` — `UNION ALL` of both tables with `'vessel'::text AS domain` / `'crew'::text AS domain`. Filters: `deleted_at IS NULL` and `is_seed = false` (vessel only).

### 2.3 Status values

- **Vessel**: `valid`, `expired`, `superseded`, `suspended`, `revoked` (no formal check constraint)
- **Crew**: `valid`, `expired`, `revoked`, `suspended` (check constraint `pms_crew_certificates_status_check` — does NOT include `superseded`)

---

## 3. Lifecycle events (what Receipt Layer adapters need to answer)

### 3.1 "What records?" — per shape

| Shape | Records to include |
|-------|-------------------|
| **Single** | One certificate: all fields from `pms_vessel_certificates` or `pms_crew_certificates` by cert_id |
| **Scope** | All active certs for a vessel: query `v_certificates_enriched` WHERE yacht_id AND status NOT IN ('superseded') |
| **Period** | Cert status changes within a date range: query `ledger_events` WHERE entity_type='certificate' AND event_type='status_change' AND created_at BETWEEN |
| **Incident** | Certificates involved in an incident: join by entity_id from ledger_events |

### 3.2 "Which ledger events?" — per shape

For **single** shape on a certificate:
```sql
SELECT * FROM ledger_events
WHERE entity_type = 'certificate' AND entity_id = :cert_id
ORDER BY created_at ASC
```

For **scope** shape (all certs on a vessel):
```sql
SELECT * FROM ledger_events
WHERE entity_type = 'certificate' AND yacht_id = :yacht_id
ORDER BY created_at ASC
```

---

## 4. DB function: refresh_certificate_expiry

`refresh_certificate_expiry(p_yacht_id uuid)` — SQL function called by nightly cron (`workers/nightly_certificate_expiry.py`, render.yaml at 02:15 UTC).

Flips `status='valid'` → `status='expired'` where `expiry_date < CURRENT_DATE`. Writes its own `ledger_events` row with `event_type='status_change'`, `source_context='system'`. This is the ONLY place in the cert domain that writes ledger events directly (not via safety net).

---

## 5. File reference (exact locations)

| Component | File | Key lines |
|-----------|------|-----------|
| Handler class | `apps/api/handlers/certificate_handlers.py` | Class at ~30, get_certificate_handlers at 711 |
| Registry entries (11 actions) | `apps/api/action_router/registry.py` | 1497-1655 (Phase 1), 2613 (note alias), 3517-3561 (archive/suspend/revoke), 3703-3721 (renew) |
| ACTION_METADATA | `apps/api/action_router/ledger_metadata.py` | 67-78 |
| Entity endpoint | `apps/api/routes/entity_routes.py` | 99-197 |
| Action discovery | `apps/api/action_router/entity_actions.py` | 54-123 |
| Phase 4 handler | `apps/api/routes/handlers/certificate_phase4_handler.py` | 37-105 |
| Internal dispatcher wrappers | `apps/api/action_router/dispatchers/internal_dispatcher.py` | 368-459, 4206-4208 |
| Internal adapter bridge | `apps/api/routes/handlers/internal_adapter.py` | 24-26, 84-153 |
| Nightly expiry worker | `apps/api/workers/nightly_certificate_expiry.py` | Full file (153 lines) |
| Frontend lens | `apps/web/src/components/lens-v2/entity/CertificateContent.tsx` | Full file |
| Certificate register | `apps/web/src/app/certificates/register/page.tsx` | Full file |
| Binary verification tests | `apps/api/tests/cert_binary_tests.py` | 45/45 PASS against live DB |
| Domain guide | `docs/explanations/LENS_DOMAINS/certificates.md` | 902 lines |

---

## 6. Adapter contract — what HMAC01 needs from CERTIFICATE01

When you're ready to build the certificate adapter:

1. **I own**: `certificate_handlers.py`, `certificate_phase4_handler.py`, the registry entries, and the binary tests. I will implement `CertificateAdapter.get_records()` and `CertificateAdapter.get_ledger_events()` per your adapter contract.

2. **You own**: `apps/api/receipts/`, the sealing pipeline, HMAC masking, PDF generation, storage, and the `export.sealed` ledger event.

3. **Lane boundary**: I don't touch `receipts/`, `ledger_utils.py`, or `evidence/sealing.py`. You don't touch `certificate_handlers.py` or registry cert entries.

4. **When to start**: After PR-0 lands (proof_hash determinism fix). My domain is ready — all 11 actions write ledger events, 45/45 binary tests pass, notifications fire.
