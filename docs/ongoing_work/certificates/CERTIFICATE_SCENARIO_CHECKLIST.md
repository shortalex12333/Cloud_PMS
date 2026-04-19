# Certificate Domain — Scenario Checklist (v2, 2026-04-18)

Updated to reflect all 18 PRs merged and all bugs A–M fixed.  
Primary test mechanism: automated runner `tests/e2e/certificate_runner.py` (17/17 PASS).  
Use this sheet for **manual MCP-browser spot checks** or **regression runs after a deploy**.

---

## How to test

### Option A — Against production (fastest)
```bash
cd /Users/celeste7/Documents/Cloud_PMS-cert04
python3 tests/e2e/certificate_runner.py           # all 17
python3 tests/e2e/certificate_runner.py --scenario 6   # single
python3 tests/e2e/certificate_runner.py --headed  # watch browser
```
Targets `https://app.celeste7.ai` by default.

### Option B — Against Docker (local Render + Vercel equivalent)
```bash
# 1. Start the cert04 stack (ports 8020 API / 3030 web)
cd /Users/celeste7/Documents/Cloud_PMS-cert04
COMPOSE_PROJECT_NAME=cloud_pms_cert04 \
  docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# 2. Wait for health
curl http://localhost:8020/health

# 3. Run runner against local stack
CERT_BASE_URL=http://localhost:3030 \
CERT_API_URL=http://localhost:8020 \
  python3 tests/e2e/certificate_runner.py --headed
```

### Option C — Live MCP browser session
Open MCP browser to `http://localhost:3030` (Docker) or `https://app.celeste7.ai` (prod).  
Log in as captain (see credentials below).  
Use this checklist as your step-by-step guide.

---

## Test credentials

| Role | Email | Password | DB role |
|------|-------|----------|---------|
| Captain | captain.tenant@alex-short.com | Password2! | captain |
| Crew (read-only) | engineer.test@alex-short.com | Password2! | **crew** ← NOT engineer |
| HOD | hod.test@alex-short.com | Password2! | hod (cannot mutate certs) |

> **Note (confirmed 2026-04-18):** `engineer.test` has role `crew` in the DB — not `engineer`.  
> The `crew` role is NOT in `_VESSEL_CERT_ROLES` so the backend rejects all mutations with 400.

---

## Browser console intercept (for manual runs)

Paste once per session in DevTools → Console:

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
| 1.1 | Navigate to /certificates | List loads ≥1 result | |
| 1.2 | Check cert names | Real names — no raw UUIDs in row titles | |
| 1.3 | Status pills render | Coloured pills visible (valid=teal, expired=red, suspended=amber) | |
| 1.4 | "New Certificate" button visible | Button present in header area | |
| 1.5 | Click any cert row | Lens opens, cert name in heading (not UUID) | |

---

## S2 — Captain creates a vessel certificate

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 2.1 | Click "New Certificate" | ActionPopup opens with Certificate Type field | |
| 2.2 | Check Certificate Type dropdown | ISM, ISPS, SOLAS, MLC, CLASS, FLAG, SEC, SRC, SCC, LOAD_LINE, TONNAGE, MARPOL, IOPP | |
| 2.3 | Fill: Type=CLASS, Name, Authority, Number, Issue Date, Expiry Date | All 8 fields present (Bug S2.4 fixed, PR #608) | |
| 2.4 | Submit | API 200, certificate_id in response, popup closes | |
| 2.5 | Cert row appears in list | Status=Valid, name correct | |
| 2.6 | Open lens | All detail rows populated (Authority, Number, Issue Date, Expiry Date) | |

> **Bug S2.4 (fixed PR #608):** Form previously showed only 3 of 8 fields. `mapActionFields.ts` now iterates `field_schema` entries.

---

## S3 — Captain creates a crew certificate

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 3.1 | Click "New Certificate" → Crew Certificate | Form shows Person Name, Type, Authority, Number, Issue Date, Expiry Date | |
| 3.2 | Fill all 6 fields | Fields accept input (no survey dates — crew table has no survey columns) | |
| 3.3 | Submit | API 200 with certificate_id | |
| 3.4 | Crew cert in list | Row shows person name (not UUID), status=Valid | |

> **Bug S3.1 (fixed PR #608):** Crew form previously showed 3 of 6 fields.

---

## S4 — Cert lens dropdown — all 11 actions

**Login:** captain. Open any valid vessel cert lens.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 4.1 | Lens loads | Cert name (not UUID) in heading, status pill, detail rows | |
| 4.2 | Primary button shows "Upload Renewed" / "Renew" | Split-button with chevron | |
| 4.3 | Click chevron → dropdown | Opens with action list | |
| 4.4 | All 11 actions present | Update, Assign Officer, Link Document, Supersede, Add Note, Archive, Suspend, Revoke (8 visible; create/renew/add_note_note are extras) | |
| 4.5 | Danger actions styled | Archive, Suspend, Revoke in red/danger colour | |
| 4.6 | Click Update → ActionPopup | Form opens with prefilled fields | |
| 4.7 | Cancel Update | Popup closes, no change | |
| 4.8 | History / Audit Trail section | Visible below detail rows — distinct from Related and Notes sections | |

---

## S5 — Add note to a certificate

**Login:** captain. Open any certificate lens.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 5.1 | Click "Add Note" from dropdown | **AddNoteModal** opens (separate custom modal, NOT ActionPopup) | |
| 5.2 | Type note text | Textarea accepts input (`id="note-text"`) | |
| 5.3 | Click "Add Note" submit button | API 200, modal closes | |
| 5.4 | Note visible in Notes section | Author name (not UUID), timestamp, note text | |
| 5.5 | DB: `pms_notes` row with `certificate_id` set | `SELECT * FROM pms_notes WHERE certificate_id = '<id>' ORDER BY created_at DESC LIMIT 1` | |

---

## S6 — Suspend a certificate (SigL3 — PIN required)

**Login:** captain. Open a cert with status=Valid.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 6.1 | Click chevron → "Suspend Certificate" | ActionPopup opens | |
| 6.2 | Popup shows: Reason field + PIN digit boxes | SigL3 component visible | |
| 6.3 | Enter Reason text | Field accepts input | |
| 6.4 | Enter 4-digit PIN in digit boxes | PIN box fills, Confirm button becomes **enabled** (Bug A: previously always disabled, fixed PR #577) | |
| 6.5 | Click Confirm | API 200 with `new_status: suspended` | |
| 6.6 | Status pill → "Suspended" | Amber pill visible after reload | |
| 6.7 | "Suspend Certificate" in dropdown is **disabled or absent** | Cannot re-suspend (Bug D fixed, PR #589) | |
| 6.8 | DB: `pms_vessel_certificates.status = 'suspended'` | `SELECT status FROM pms_vessel_certificates WHERE id = '<id>'` | |
| 6.9 | DB: `pms_audit_log` row with `action = 'suspend_certificate'` | `SELECT action FROM pms_audit_log WHERE entity_id = '<id>' ORDER BY created_at DESC LIMIT 1` | |
| 6.10 | DB: `pms_notifications` rows fanned out | `SELECT COUNT(*) FROM pms_notifications WHERE entity_id = '<id>'` | |

> **Bug A (fixed PR #577):** ActionPopup SigL0 was auto-submitting before user filled fields.  
> **Bug D (fixed PR #589):** Dropdown did not hide Suspend when cert already suspended.  
> **SigL3 note:** PIN is ceremony-only (no server-side PIN value validation). Any 4 digits unlocks Confirm.

---

## S7 — Renew a certificate

**Login:** captain. Open any Valid vessel cert.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 7.1 | Click "Upload Renewed" primary button | ActionPopup opens with renewal form | |
| 7.2 | Fill: New Issue Date, New Expiry Date | Date fields accept ISO input | |
| 7.3 | Fill: New Certificate Number (optional) | If blank, backend auto-generates suffix (Bug F fixed, PR #589) | |
| 7.4 | Submit | API 200 with `renewed_certificate_id` + `superseded_certificate_id` | |
| 7.5 | Original cert pill → "Superseded" | Reload old cert, pill shows Superseded | |
| 7.6 | New cert in list with status=Valid | Fresh row visible | |
| 7.7 | DB: old cert `status='superseded'`, new cert `status='valid'` | Both rows verified | |

> **Bug F (fixed PR #589):** Renew with blank cert number returned 500. Backend now auto-suffixes.

---

## S8 — Assign responsible officer

**Login:** captain. Open any certificate lens.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 8.1 | Click chevron → "Assign Responsible Officer" | ActionPopup opens with user-search field | |
| 8.2 | Select officer (or type name) | Dropdown shows crew names (not UUIDs) | |
| 8.3 | Submit | API 200 | |
| 8.4 | Lens detail shows "Responsible Officer: [name]" | Name visible in detail section | |
| 8.5 | DB: `pms_vessel_certificates.properties` has `assigned_to` key | `SELECT properties FROM pms_vessel_certificates WHERE id = '<id>'` | |

---

## S9 — Archive a certificate (SigL3 — PIN required)

**Login:** captain. Open any non-critical cert.

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 9.1 | Click chevron → "Archive Certificate" | ActionPopup opens with confirmation text + PIN | |
| 9.2 | Popup shows "Archive Certificate / This will archive this certificate record" | Confirmation message visible (Bug S9.2 fixed, PR #611) | |
| 9.3 | Enter 4-digit PIN | Confirm button becomes enabled | |
| 9.4 | Click Confirm | API 200 with `deleted_at` in response | |
| 9.5 | Cert disappears from active list | No longer visible in default /certificates view | |
| 9.6 | DB: `deleted_at IS NOT NULL` | `SELECT deleted_at FROM pms_vessel_certificates WHERE id = '<id>'` (column is `deleted_at` NOT `archived_at`) | |
| 9.7 | DB: `pms_audit_log` row with `action = 'archive_certificate'` | Audit row exists | |

> **Bug H (fixed PR #606):** Response previously returned `archived_at` but DB column is `deleted_at`. Fixed in handler.  
> **Bug S9.2 (fixed PR #611):** Archive modal lacked confirmation text. Fixed: `confirmation_message` now passed as `subtitle` prop.

---

## S10 — Certificate register page

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 10.1 | Navigate to /certificates/register | Page loads, no 422 error (Bug G fixed, PR #585) | |
| 10.2 | Vessel name in header | Shows yacht name, not UUID | |
| 10.3 | Urgency grouping visible | Sections: Expired, Expiring Soon, Valid | |
| 10.4 | Cert rows show names and numbers | Not blank dashes (Bug K fixed, PR #592) | |
| 10.5 | Print/Export button visible | Button renders | |

> **Bug G (fixed PR #585):** Register 422 on `limit=500` — now uses paginated fetch.  
> **Bug K (fixed PR #592):** Register columns rendered `—` for all rows. Fixed select query.

---

## S11 — Role gate: crew cannot mutate

**Login:** crew (engineer.test@alex-short.com)

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 11.1 | Navigate to /certificates | List loads (crew has read access) | |
| 11.2 | Note: "New Certificate" button may be visible | **By design** — action list returns all items; gate fires on execution | |
| 11.3 | Open any cert lens | Lens loads (read access confirmed) | |
| 11.4 | Open dropdown | Actions visible in UI | |
| 11.5 | **API test:** POST create_vessel_certificate with crew JWT | Must return **400** (ValueError from `_cert_mutation_gate`) — NOT 2xx | |
| 11.6 | **API test:** POST suspend_certificate with crew JWT | Must return **400** | |

> Role `crew` is **not** in `_VESSEL_CERT_ROLES = {engineer, eto, chief_engineer, chief_officer, captain, manager}`.  
> The UI shows buttons because the action list endpoint returns all actions for display. The execution gate (`_cert_mutation_gate`) enforces roles.  
> Test crew API gate via DevTools Console: POST to `/api/v1/actions/execute` with `Authorization: Bearer <token>`.

---

## S12 — Dashboard certificate widget

**Login:** captain

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 12.1 | Navigate to / (dashboard) | Dashboard loads | |
| 12.2 | Certificate widget visible | Widget with cert summary present | |
| 12.3 | Cert names in widget are NOT UUIDs | Real names in widget list | |
| 12.4 | Click cert in widget | Navigates to /certificates?id=<cert_id> | |

---

## S13 — Notification bell

**Login:** captain → create cert → switch to HOD

| # | Step | Expected | Pass? |
|---|------|----------|-------|
| 13.1 | As captain: create a new vessel cert | Cert created (reuse S2 flow) | |
| 13.2 | Switch login to HOD (hod.test@alex-short.com) | Dashboard loads | |
| 13.3 | Bell icon `data-testid="notification-bell"` has unread badge | Numeric badge > 0 (Bug L/M fixed, PRs #595 + #598) | |
| 13.4 | Click bell | `data-testid="notification-dropdown"` opens | |
| 13.5 | Notification for the new cert visible | "certificate_created" event in dropdown | |
| 13.6 | Click notification | Navigates to /certificates?id=<cert_id> | |

> **Bug L (fixed PR #595):** Bell component didn't exist — added.  
> **Bug M (fixed PR #598):** Bell component didn't bind API data — fixed.

---

## Edge cases (regression guards)

| # | Test | Expected | Pass? |
|---|------|----------|-------|
| E1 | Renew with blank cert number | API returns non-500 (auto-suffix applied) — Bug F guard | |
| E2 | Suspend already-suspended cert | "Suspend Certificate" disabled or absent in dropdown — Bug D guard | |
| E3 | HOD opens More Actions dropdown on any cert | "Suspend Certificate" **not present** in dropdown | |
| E4 | Crew POST create_vessel_certificate with auth token | Returns 400/403 (role gate) — never 2xx | |

---

## DB verification queries

Connect to tenant DB:
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
SELECT id, deleted_at FROM pms_vessel_certificates
WHERE id = '<cert_id>';

-- Audit log for any cert
SELECT action, user_id, created_at FROM pms_audit_log
WHERE entity_id = '<cert_id>' ORDER BY created_at DESC;

-- Ledger events
SELECT event_type, action, entity_id, created_at FROM ledger_events
WHERE entity_id = '<cert_id>' ORDER BY created_at DESC;

-- Notifications fanned out
SELECT notification_type, title, created_at FROM pms_notifications
WHERE entity_id = '<cert_id>' ORDER BY created_at DESC;

-- Role check for test users
SELECT u.email, r.role FROM auth_users_roles r
JOIN auth.users u ON u.id = r.user_id
WHERE r.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

---

## Role matrix (actual backend rules)

`_VESSEL_CERT_ROLES = {engineer, eto, chief_engineer, chief_officer, captain, manager}`  
`_CREW_CERT_ROLES = {chief_engineer, chief_officer, purser, chief_steward, captain, manager}`

| Action | crew | engineer | chief_engineer | captain/manager |
|--------|------|----------|----------------|-----------------|
| View list/lens | Y | Y | Y | Y |
| Create vessel cert | **N** | Y | Y | Y |
| Create crew cert | **N** | **N** | Y | Y |
| Update, Renew, Link doc | **N** | Y | Y | Y |
| Add note | Y | Y | Y | Y |
| Assign officer | **N** | **N** | **N** | Y |
| Suspend / Revoke | **N** | **N** | **N** | Y |
| Archive | **N** | **N** | **N** | Y |
| Supersede | **N** | Y | Y | Y |

> `hod.test@alex-short.com` has role `hod` which is **not** in either frozenset → cannot mutate anything.

---

## Cleanup after testing

```sql
-- Soft-delete all CERT04-RUN- test certs
UPDATE pms_vessel_certificates
SET deleted_at = NOW()
WHERE certificate_name LIKE 'CERT04-RUN-%' AND deleted_at IS NULL;

UPDATE pms_crew_certificates
SET deleted_at = NOW()
WHERE person_name LIKE 'CERT04-RUN-%' AND deleted_at IS NULL;

-- Or use the runner's built-in cleanup (runs automatically at exit)
-- python3 tests/e2e/certificate_runner.py  ← cleanup fires unconditionally
```

> **IMPORTANT:** Cleanup SQL uses `deleted_at` (the actual column name).  
> Old references to `archived_at` or `status='archived'` are wrong — Bug H (PR #606) fixed the column.

---

## All fixed bugs quick reference

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
| I | "132 results" chip vs DB total 445 — NOT A BUG (view + seed filter + test data) | — |
| J | `+ Upload` attachment button leaked to crew role | #606 |
| K | Register columns rendered `—` for all rows | #592 |
| L | No notification bell component existed | #595 |
| M | Bell component didn't bind API data | #598 |
| S2.4/S3.1 | Vessel/crew create forms showed 3 of 8 / 3 of 6 fields | #608 |
| S9.2 | Archive confirmation text missing from modal | #611 |
