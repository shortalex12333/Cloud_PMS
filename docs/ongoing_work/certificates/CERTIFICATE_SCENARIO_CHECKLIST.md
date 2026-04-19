# Certificate Domain — Scenario Checklist (v3, 2026-04-19)

> **Supersedes v2 (2026-04-18).** Updated for PR #641 (10 overnight fixes) + PR #646 (P0 hotfix).
> Main branch: `63eeeb0f`. Live at `app.celeste7.ai` (Vercel) + `backend.celeste7.ai` (Render).

---

## What changed in v3 (vs v2)

| Area | Old (v2) | New (v3) | Fix |
|------|----------|----------|-----|
| S4 dropdown | Lists Assign Officer + Supersede as present | Both **ABSENT** — removed from surface | PR #641 `certificate_handlers.py` + `CertificateContent.tsx:240` |
| S6 / S9 signature | "PIN digit boxes — SigL3" | **Name-attestation (SigL2)** — type full name | PR #641 `CertificateContent.tsx:140-141` |
| S7 renew flow | Upload button → ActionPopup directly | **Two-step:** Upload → AttachmentUploadModal → Escape/dismiss → renew ActionPopup | PR #641 `CertificateContent.tsx:349,473-489` |
| S8 | "Assign Responsible Officer" as live action | **Regression guard** — assert action is ABSENT | PR #641 |
| Crew cert RLS | 404 on any crew cert action | Fixed — `v_certificates_enriched` UNION view | PR #641 `rls_entity_validator.py:28` |
| Sort dropdown | Showed "Priority" option on cert list | **Removed** — Newest / Oldest / Alphabetical only | PR #641 `FilteredEntityList.tsx:389-391` |
| P0 actions routes | ALL `/v1/actions/execute` calls broken on Render startup | Fixed — `optional_fields=[]` kwarg removed | PR #646 `registry.py:1643` |

---

## How to test

### Option A — Production (Vercel + Render)
```bash
cd /Users/celeste7/Documents/Cloud_PMS-cert04
python3 tests/e2e/certificate_runner.py           # all 17 scenarios
python3 tests/e2e/certificate_runner.py --scenario 6   # single scenario
python3 tests/e2e/certificate_runner.py --headed  # watch browser
```
Targets `https://app.celeste7.ai` by default.

### Option B — Docker local stack (ports 8020 API / 3030 web)
```bash
cd /Users/celeste7/Documents/Cloud_PMS-cert04
COMPOSE_PROJECT_NAME=cloud_pms_cert04 \
  docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
curl http://localhost:8020/health

CERT_BASE_URL=http://localhost:3030 \
CERT_API_URL=http://localhost:8020 \
  python3 tests/e2e/certificate_runner.py --headed
```

### Option C — Manual MCP browser
Open MCP browser to `https://app.celeste7.ai`. Log in as captain. Step through this checklist.

---

## Test credentials

| Role | Email | Password | DB role |
|------|-------|----------|---------|
| Captain | captain.tenant@alex-short.com | Password2! | captain |
| Crew (read-only gate test) | engineer.test@alex-short.com | Password2! | **crew** ← role is `crew` not `engineer` |
| HOD | hod.test@alex-short.com | Password2! | hod (not in cert mutation frozensets) |

> `engineer.test` has DB role `crew`. `crew` is not in `_VESSEL_CERT_ROLES` — backend rejects all mutations with 400.

---

## Browser console intercept (paste once per session)

```javascript
const _orig = window.fetch;
window.fetch = async (...args) => {
  const r = await _orig(...args);
  if (args[0]?.includes?.('/actions/execute') || args[0]?.includes?.('/v1/')) {
    r.clone().json()
      .then(d => console.log('[API]', args[0], JSON.stringify(d)))
      .catch(() => {});
  }
  return r;
};
```

---

## S1 — Captain views certificate list

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 1.1 | Navigate to `/certificates` | List loads ≥1 result | |
| 1.2 | Check cert names in rows | Real names — no raw UUIDs | |
| 1.3 | Status pills render | Coloured pills visible (valid=teal, expired=red, suspended=amber) | |
| 1.4 | Sort dropdown options | **Newest / Oldest / Alphabetical only** — no "Priority" option | |
| 1.5 | "New Certificate" button visible | Button present in header | |
| 1.6 | Click any cert row | Lens opens, cert name in heading (not UUID) | |

> **Bug fixed (PR #641):** `FilteredEntityList.tsx:389-391` — Priority sort option removed from cert list.

---

## S2 — Captain creates a vessel certificate

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 2.1 | Click "New Certificate" | ActionPopup opens with Certificate Type field | |
| 2.2 | Check Certificate Type dropdown | ISM, ISPS, SOLAS, MLC, CLASS, FLAG, SEC, SRC, SCC, LOAD_LINE, TONNAGE, MARPOL, IOPP | |
| 2.3 | Fill: Type, Name, Authority, Number, Issue Date, Expiry Date | All 8 fields present | |
| 2.4 | Submit | API 200, certificate_id in response, popup closes | |
| 2.5 | Cert row appears in list | Status=Valid, name correct | |
| 2.6 | Open lens | Detail rows populated (Authority, Number, Issue Date, Expiry Date) | |

---

## S3 — Captain creates a crew certificate

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 3.1 | Click "New Certificate" → Crew Certificate | Form shows Person Name, Type, Authority, Number, Issue Date, Expiry Date | |
| 3.2 | Fill all 6 fields | Fields accept input | |
| 3.3 | Submit | API 200 with certificate_id | |
| 3.4 | Crew cert in list | Row shows person name (not UUID), status=Valid | |
| 3.5 | Open crew cert lens | Lens loads, no 404 | |
| 3.6 | Click dropdown on crew cert lens | Actions available (not 404'd by RLS) | |

> **Bug fixed (PR #641):** `rls_entity_validator.py:28` — `certificate_id` now resolves via `v_certificates_enriched` (UNION view covering both tables). Crew cert actions no longer 404.

---

## S4 — Cert lens dropdown — correct action set

**Login:** captain. Open any valid **vessel** cert lens.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 4.1 | Lens loads | Cert name in heading, status pill, detail rows | |
| 4.2 | Primary button shows "Upload Renewed" or "Renew" | Split-button with chevron | |
| 4.3 | Click chevron → dropdown opens | Action list visible | |
| 4.4 | Actions **present** | Update, Note, Archive, Suspend, Revoke, Renew, Link Document (vessel only, when no doc attached) | |
| 4.5 | Actions **ABSENT** | `create_vessel_certificate`, `create_crew_certificate`, `assign_certificate`, `supersede_certificate` — none of these should appear | |
| 4.6 | Danger actions styled | Archive, Suspend, Revoke in red/danger colour | |
| 4.7 | Click Update → ActionPopup | Form opens with prefilled fields | |
| 4.8 | Cancel Update | Popup closes, no change | |

> **Bug fixed (PR #641):** `CertificateContent.tsx:240` — filter removes create/assign/supersede. `certificate_handlers.py` — assign + supersede removed from `_get_certificate_actions()` entirely.

---

## S5 — Add note to a certificate

**Login:** captain. Open any certificate lens.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 5.1 | Click "Add Note" from dropdown | AddNoteModal opens | |
| 5.2 | Type note text | Textarea accepts input | |
| 5.3 | Click "Add Note" submit | API 200, modal closes | |
| 5.4 | Note visible in Notes section | Author name, timestamp, note text | |
| 5.5 | DB: `pms_notes` row with `certificate_id` set | `SELECT * FROM pms_notes WHERE certificate_id = '<id>' ORDER BY created_at DESC LIMIT 1` | |

---

## S6 — Suspend a certificate (SigL2 — name-attestation)

**Login:** captain. Open a cert with status=Valid.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 6.1 | Click chevron → "Suspend Certificate" | ActionPopup opens | |
| 6.2 | Popup shows: Reason field + **"Type your full name to confirm"** input | **Name-attestation (SigL2)** — NOT PIN digit boxes | |
| 6.3 | Enter Reason text | Field accepts input | |
| 6.4 | Type full name in name field | Confirm button becomes **enabled** | |
| 6.5 | Click Confirm | API 200 with `new_status: suspended` | |
| 6.6 | Status pill → "Suspended" | Amber pill visible after reload | |
| 6.7 | "Suspend Certificate" in dropdown is **disabled or absent** | Cannot re-suspend | |
| 6.8 | DB: `pms_vessel_certificates.status = 'suspended'` | `SELECT status FROM pms_vessel_certificates WHERE id = '<id>'` | |
| 6.9 | DB: `pms_audit_log` row with `action = 'suspend_certificate'` | `SELECT action FROM pms_audit_log WHERE entity_id = '<id>' ORDER BY created_at DESC LIMIT 1` | |
| 6.10 | DB: `pms_notifications` rows fanned out | `SELECT COUNT(*) FROM pms_notifications WHERE entity_id = '<id>'` | |

> **Bug fixed (PR #641):** `CertificateContent.tsx:140-141` — `sigLevel === 3` clamped to `2`. Cert domain uses name-attestation (SigL2), not PIN (SigL3). PIN was ceremony-only with no server-side validation.

---

## S7 — Renew a certificate (two-step upload flow)

**Login:** captain. Open any Valid vessel cert **without an attached document**.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 7.1 | Primary button shows "Upload Renewed" | Split-button visible | |
| 7.2 | Click "Upload Renewed" | **AttachmentUploadModal opens** (file picker — NOT the renew form yet) | |
| 7.3 | Upload a file (or press Escape to dismiss without uploading) | Modal closes | |
| 7.4 | After modal closes → renew ActionPopup opens automatically | Renew form appears (`pendingRenew` trigger) | |
| 7.5 | Fill: New Issue Date, New Expiry Date | Date fields accept ISO input | |
| 7.6 | Fill: New Certificate Number (optional) | If blank, backend auto-generates suffix | |
| 7.7 | Submit | API 200 with `renewed_certificate_id` + `superseded_certificate_id` | |
| 7.8 | Original cert pill → "Superseded" | Reload old cert, pill shows Superseded | |
| 7.9 | New cert in list with status=Valid | Fresh row visible | |
| 7.10 | DB: old cert `status='superseded'`, new cert `status='valid'` | `SELECT id, status FROM pms_vessel_certificates WHERE certificate_name LIKE 'CERT04-RUN-%'` | |

> **Bug fixed (PR #641):** `CertificateContent.tsx:349,473-489` — `pendingRenew` state added. Upload modal closes → sets flag → `onClose` triggers renew ActionPopup. Previously the renew popup never appeared after upload.

---

## S8 — Assign responsible officer (REGRESSION GUARD — action must be ABSENT)

**Login:** captain. Open any certificate lens.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 8.1 | Click chevron → open dropdown | Dropdown action list visible | |
| 8.2 | Scan for "Assign Responsible Officer" or `assign_certificate` | **Must NOT be present** | |
| 8.3 | No assign action in dropdown | PASS if absent; FAIL if present | |

> **Bug fixed (PR #641):** `assign_certificate` removed from `_get_certificate_actions()` in `certificate_handlers.py` and filtered in `CertificateContent.tsx:240`. Was incorrectly surfaced in the dropdown.

---

## S9 — Archive a certificate (SigL2 — name-attestation)

**Login:** captain. Open any non-critical cert.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 9.1 | Click chevron → "Archive Certificate" | ActionPopup opens with confirmation text | |
| 9.2 | Popup shows subtitle: "This will archive this certificate record" | Confirmation message visible | |
| 9.3 | Popup shows **"Type your full name to confirm"** input | **Name-attestation (SigL2)** — NOT PIN digit boxes | |
| 9.4 | Type full name in name field | Confirm button becomes enabled | |
| 9.5 | Click Confirm | API 200 with `deleted_at` in response | |
| 9.6 | Cert disappears from active list | No longer visible in default /certificates view | |
| 9.7 | DB: `deleted_at IS NOT NULL` | `SELECT deleted_at FROM pms_vessel_certificates WHERE id = '<id>'` — column is `deleted_at` NOT `archived_at` | |
| 9.8 | DB: `pms_audit_log` row with `action = 'archive_certificate'` | Audit row exists | |

> **Bug fixed (PR #641):** `CertificateContent.tsx:140-141` — SigL2 cap (same as S6). PIN attestation removed.

---

## S10 — Certificate register page

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 10.1 | Navigate to `/certificates/register` | Page loads, no 422 error | |
| 10.2 | Vessel name in header | Shows yacht name, not UUID | |
| 10.3 | Urgency grouping visible | Sections: Expired, Expiring Soon, Valid | |
| 10.4 | Cert rows show names and numbers | Not blank dashes | |
| 10.5 | Print/Export button visible | Button renders | |

---

## S11 — Role gate: crew cannot mutate

**Login:** crew (`engineer.test@alex-short.com`)

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 11.1 | Navigate to `/certificates` | List loads (crew has read access) | |
| 11.2 | Open any cert lens | Lens loads | |
| 11.3 | Open dropdown | Actions visible in UI | |
| 11.4 | **API test:** POST `create_vessel_certificate` with crew JWT | Must return **400** — NOT 2xx | |
| 11.5 | **API test:** POST `suspend_certificate` with crew JWT | Must return **400** | |

> Role `crew` is not in `_VESSEL_CERT_ROLES = {engineer, eto, chief_engineer, chief_officer, captain, manager}`. Gate fires on execution, not display.

---

## S12 — Dashboard certificate widget

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 12.1 | Navigate to `/` (dashboard) | Dashboard loads | |
| 12.2 | Certificate widget visible | Widget with cert summary present | |
| 12.3 | Cert names in widget are NOT UUIDs | Real names in widget list | |
| 12.4 | Click cert in widget | Navigates to `/certificates?id=<cert_id>` | |

---

## S13 — Notification bell receives certificate events

**Login:** captain → create cert → switch to HOD

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 13.1 | As captain: create a new vessel cert | Cert created (reuse S2 flow) | |
| 13.2 | Switch login to HOD (`hod.test@alex-short.com`) | Dashboard loads | |
| 13.3 | Bell icon `data-testid="notification-bell"` has unread badge | Numeric badge > 0 | |
| 13.4 | Click bell | `data-testid="notification-dropdown"` opens | |
| 13.5 | Notification for the new cert visible | `certificate_created` event in dropdown | |
| 13.6 | Click notification | Navigates to `/certificates?id=<cert_id>` | |

> **Known gap (Bug L):** `pms_notifications` has no frontend bell consumer — platform-wide gap, not cert-specific regression. Bell ships data; consumer pending.

---

## Edge cases (regression guards)

| # | Test | Expected | Code reference | Pass? |
|---|------|----------|----------------|-------|
| E1 | Renew cert with blank cert number | API returns non-500 (auto-suffix applied) | `certificate_handlers.py` | |
| E2 | Suspend already-suspended cert | "Suspend Certificate" disabled or absent in dropdown | `certificate_handlers.py:56` (state transitions) | |
| E3 | HOD opens dropdown on any cert | "Suspend Certificate" **not present** | `certificate_handlers.py` role gate | |
| E4 | Crew POST `create_vessel_certificate` with auth token | Returns 400/403 — never 2xx | `certificate_handlers.py` `_cert_mutation_gate` | |

---

## DB verification queries

```bash
PGPASSWORD="@-Ei-9Pa.uENn6g" psql \
  "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require"
```

```sql
-- Recent vessel certs created by runner
SELECT id, certificate_name, status, created_at
FROM pms_vessel_certificates
WHERE certificate_name LIKE 'CERT04-RUN-%'
ORDER BY created_at DESC LIMIT 10;

-- Verify archive: deleted_at set (NOT archived_at)
SELECT id, deleted_at FROM pms_vessel_certificates WHERE id = '<cert_id>';

-- Audit log
SELECT action, user_id, created_at FROM pms_audit_log
WHERE entity_id = '<cert_id>' ORDER BY created_at DESC;

-- Notifications fanned out
SELECT notification_type, title, created_at FROM pms_notifications
WHERE entity_id = '<cert_id>' ORDER BY created_at DESC;

-- Crew cert via enriched view (confirm both tables covered)
SELECT id, certificate_name, 'vessel' AS src FROM pms_vessel_certificates WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
UNION ALL
SELECT id, person_name AS certificate_name, 'crew' AS src FROM pms_crew_certificates WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY src, certificate_name LIMIT 20;

-- Role check for test users
SELECT u.email, r.role FROM auth_users_roles r
JOIN auth.users u ON u.id = r.user_id
WHERE r.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

---

## Role matrix

`_VESSEL_CERT_ROLES = {engineer, eto, chief_engineer, chief_officer, captain, manager}`
`_CREW_CERT_ROLES = {chief_engineer, chief_officer, purser, chief_steward, captain, manager}`

| Action | crew | engineer | chief_engineer | captain/manager |
|--------|------|----------|----------------|-----------------|
| View list/lens | Y | Y | Y | Y |
| Create vessel cert | **N** | Y | Y | Y |
| Create crew cert | **N** | **N** | Y | Y |
| Update, Renew, Link doc | **N** | Y | Y | Y |
| Add note | Y | Y | Y | Y |
| Suspend / Revoke / Archive | **N** | **N** | **N** | Y |
| Supersede (backend-only, not in dropdown) | **N** | Y | Y | Y |

> `assign_certificate` is removed from the dropdown surface — not user-invocable via UI.

---

## All fixed bugs — complete reference

| Bug | What | PR |
|-----|------|----|
| A | ActionPopup SigL0 auto-submitted (Confirm always disabled) | #577 |
| B | Cert entity endpoint omitted notes/audit_trail sections | #579 |
| C | UI "Action failed" on string-only `status:success` response | #583 |
| D | Suspend/Revoke/Archive not hidden when cert already in that state | #589 |
| E | Ledger safety net used wrong entity_id | #583 |
| F | Renew with blank cert_number returned 500 | #589 |
| G | Register page 422 on limit=500 | #585 |
| H | Archive response returned `archived_at` but DB column is `deleted_at` | #606 |
| I | "132 results" chip vs DB total 445 — paginator clamp, low priority | — |
| J | `+ Upload` attachment button leaked to crew role | #606 |
| K | Register columns rendered `—` for all rows | #592 |
| L | No notification bell component existed | #595 |
| M | Bell component didn't bind API data | #598 |
| S2.4/S3.1 | Vessel/crew create forms showed 3 of 8 / 3 of 6 fields | #608 |
| S9.2 | Archive confirmation text missing from modal | #611 |
| **Overnight** | Crew cert RLS 404 — `rls_entity_validator.py:28` → `v_certificates_enriched` | #641 |
| **Overnight** | SigL3 PIN on cert actions → SigL2 name-attestation — `CertificateContent.tsx:140-141` | #641 |
| **Overnight** | pendingRenew two-step upload flow — `CertificateContent.tsx:349,473-489` | #641 |
| **Overnight** | Priority sort on cert list — `FilteredEntityList.tsx:389-391` | #641 |
| **Overnight** | Create/Assign/Supersede in dropdown — `CertificateContent.tsx:240` | #641 |
| **Overnight** | Link document shown for crew certs — `certificate_handlers.py:670` | #641 |
| **Overnight** | 3 stale registry endpoints + `field_metadata` — `registry.py:1583,1631,1671` | #641 |
| **Overnight** | Assign surface in dropdown — `certificate_handlers.py` | #641 |
| **Overnight** | Supersede surface in dropdown — `certificate_handlers.py` | #641 |
| **Overnight** | Crew cert IdentityStrip empty span — `IdentityStrip.tsx:56` | #641 |
| **P0 Hotfix** | ALL actions broken — `optional_fields=[]` kwarg in `registry.py:1643` | #646 |

---

## Cleanup after testing

```sql
UPDATE pms_vessel_certificates
SET deleted_at = NOW()
WHERE certificate_name LIKE 'CERT04-RUN-%' AND deleted_at IS NULL;

UPDATE pms_crew_certificates
SET deleted_at = NOW()
WHERE person_name LIKE 'CERT04-RUN-%' AND deleted_at IS NULL;
```

> Runner also runs cleanup unconditionally at exit: `python3 tests/e2e/certificate_runner.py`
