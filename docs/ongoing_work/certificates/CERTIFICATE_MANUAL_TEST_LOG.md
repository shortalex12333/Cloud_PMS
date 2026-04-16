# Certificate — Manual Test Log

**Tester:** ___________________  
**Date:** 2026-04-16  
**App URL:** https://app.celeste7.ai  
**Backend:** https://pipeline-core.int.celeste7.ai  
**Render commit:** `cb599501` (PRs #564 + #566 merged — role widening, mutation gate, notifications, gap fixes)

Fill in Y / N / ERR for each check. Paste console errors directly into the ERR cells or the notes section at the bottom of each scenario.

---

## Test credentials

| Role | Email | Password |
|------|-------|----------|
| Crew (engineer) | engineer.test@alex-short.com | Password2! |
| HOD (ETO) | eto.test@alex-short.com | Password2! |
| HOD (chief_engineer) | hod.test@alex-short.com | Password2! |
| Captain | captain.tenant@alex-short.com | Password2! |
| Captain (alt) | x@alex-short.com | Password2! |

**Frontend**: https://app.celeste7.ai  
**API**: https://pipeline-core.int.celeste7.ai

---

## Browser console setup

Open DevTools → Console before every scenario. Paste this to intercept API calls:

```javascript
const _origFetch = window.fetch;
window.fetch = async (...args) => {
  const r = await _origFetch(...args);
  if (args[0]?.includes?.('/actions/execute') || args[0]?.includes?.('/v1/')) {
    const clone = r.clone();
    clone.json().then(d => console.log('[API]', args[0], JSON.stringify(d)));
  }
  return r;
};
```

---

## Pre-flight

| # | Check | Result | Console / Notes |
|---|-------|--------|-----------------|
| P1 | App loads at `app.celeste7.ai` — no blank screen | | |
| P2 | Log in as **captain** (`captain.tenant@alex-short.com` / `Password2!`) — lands on dashboard | | |
| P3 | Sidebar shows **Certificates** link | | |
| P4 | Open DevTools → Console tab. No red errors on load | | |

---

## Scenario 1 — Captain views certificate list (happy path)

**Login:** `captain.tenant@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 1.1 | Click **Certificates** in sidebar | Sidebar nav | Certificate list loads, existing certs visible | | |
| 1.2 | Check list has both vessel and crew certs | List table/grid | At least one vessel cert AND one crew cert visible. Crew certs show "Crew" badge | | |
| 1.3 | Check cert names are readable | List rows | Real names like "Lloyd's Register Class Certificate" — NOT UUIDs | | |
| 1.4 | Check status pills render | Each row | Status pills (Valid/Expired/etc.) visible with correct colour | | |
| 1.5 | "Add Certificate" button visible | Top-right area | Button present and clickable | | |
| 1.6 | Click a certificate row | Any cert row | Navigates to cert lens detail page (`/certificates/{uuid}`) | | |

**Notes / errors for Scenario 1:**
```
[paste here]
```

---

## Scenario 2 — Captain creates a vessel certificate

**Login:** `captain.tenant@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 2.1 | Click **Add Certificate** | Top-right button | ActionPopup opens OR dropdown with "Add Vessel Certificate" / "Add Crew Certificate" options | | |
| 2.2 | Select vessel cert type | Popup or dropdown | Form shows Certificate Type dropdown, Certificate Name, Issuing Authority fields | | |
| 2.3 | Certificate Type dropdown options | Dropdown in popup | Should list: ISM, ISPS, SOLAS, MLC, CLASS, FLAG, SEC, SRC, SCC, LOAD_LINE, TONNAGE, MARPOL, IOPP | | |
| 2.4 | Fill form | Popup fields | Type: CLASS, Name: "Test Class Certificate", Authority: "Lloyd's Register", Number: "TEST-001", Expiry: 2027-06-01 | | |
| 2.5 | Submit | **Create** / **Submit** button | Popup closes, new cert appears in list | | |
| 2.6 | Verify new cert in list | Certificate list | Row shows "Test Class Certificate", status = Valid | | |
| 2.7 | API response check | Console `[API]` log | `success: true`, `certificate_id` present | | |

**Notes / errors for Scenario 2:**
```
[paste here]
```

---

## Scenario 3 — Captain creates a crew certificate

**Stay logged in as captain.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 3.1 | Click **Add Certificate** → select crew cert | Popup or dropdown | Form shows Person Name, Certificate Type (STCW/ENG1/COC/GMDSS/BST/PSC/AFF), Issuing Authority | | |
| 3.2 | Fill form | Popup fields | Person: "Test Seafarer", Type: STCW, Authority: "UK MCA", Number: "STCW-E2E", Expiry: 2031-01-01 | | |
| 3.3 | Submit | **Create** / **Submit** button | Popup closes, cert appears in list with "Crew" badge | | |
| 3.4 | Open the new crew cert | Click row | Lens loads with person name in title, domain = crew | | |

**Notes / errors for Scenario 3:**
```
[paste here]
```

---

## Scenario 4 — Captain opens cert lens and verifies all dropdown actions

**Stay on any valid vessel certificate.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 4.1 | Open a **valid** vessel cert | Click row in list | Lens loads — Identity Strip with cert name, status pill, details | | |
| 4.2 | Certificate name in title | Identity Strip header | Real name visible, not UUID | | |
| 4.3 | Status pill colour | Identity Strip | Valid = green, Expired = red, Suspended = amber | | |
| 4.4 | Detail rows visible | Identity Strip details | Issuing Authority, Certificate No, Issue Date, Expiry Date shown | | |
| 4.5 | Primary button visible | Top-right split button | "Upload Renewed" or "Renew Certificate" label | | |
| 4.6 | Click dropdown arrow | Chevron next to primary button | Dropdown menu opens with action items | | |
| 4.7 | **Renew** action present | Dropdown | "Upload Renewed" or "Renew" | | |
| 4.8 | **Update** action present | Dropdown | "Update" | | |
| 4.9 | **Assign Officer** action present | Dropdown | "Assign Officer" | | |
| 4.10 | **Add Note** action present | Dropdown | "Add Note" | | |
| 4.11 | **Link Document** action present | Dropdown | "Link Document" | | |
| 4.12 | **Supersede** action present | Dropdown | "Supersede" | | |
| 4.13 | **View History** action present | Dropdown | "View History" | | |
| 4.14 | **Suspend Certificate** present (danger) | Dropdown | "Suspend Certificate" with red/danger styling | | |
| 4.15 | **Revoke Certificate** present (danger) | Dropdown | "Revoke Certificate" with red/danger styling | | |
| 4.16 | **Archive** present (danger) | Dropdown | "Archive" with red/danger styling | | |

**Notes / errors for Scenario 4:**
```
Missing actions (list which ones don't appear):

```

---

## Scenario 5 — Captain adds a note to a certificate

**Stay on same cert lens.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 5.1 | Click **Add Note** from dropdown | Dropdown menu | AddNoteModal opens with text area | | |
| 5.2 | Type a note | Text area | "Manual test note — captain verification 2026-04-16" | | |
| 5.3 | Submit note | **Save** / **Submit** in modal | Modal closes | | |
| 5.4 | Note visible in Notes section | Scroll down to Notes | Note text appears with author and timestamp | | |
| 5.5 | API response | Console `[API]` log | `add_certificate_note` — `success: true`, `note_id` present | | |

**Notes / errors for Scenario 5:**
```
[paste here]
```

---

## Scenario 6 — Captain suspends a certificate (SIGNED action)

**Open a different valid vessel cert (don't re-use the one from Scenario 5).**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 6.1 | Open a **valid** vessel cert | Click row | Lens loads, status = Valid | | |
| 6.2 | Click dropdown → **Suspend Certificate** | Dropdown (danger item) | ActionPopup opens with "Reason" text field | | |
| 6.3 | Signature capture visible | Popup | Requires signature (name, timestamp, or signature pad) | | |
| 6.4 | Fill reason | Reason field | "Manual test suspension — verifying signed action flow" | | |
| 6.5 | Submit | **Confirm** / **Submit** in popup | Popup closes, status updates | | |
| 6.6 | Status pill changes | Identity Strip | Pill reads "Suspended" — amber/warning colour | | |
| 6.7 | Dropdown re-check | Open dropdown again | Suspend/Revoke/Update should now be hidden (terminal-adjacent state) | | |
| 6.8 | API response | Console `[API]` log | `suspend_certificate` — `success: true`, `new_status: suspended` | | |

**Notes / errors for Scenario 6:**
```
[paste here]
```

---

## Scenario 7 — Captain renews a certificate

**Open another valid vessel cert.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 7.1 | Click primary button **Upload Renewed** | Split button (left side) | ActionPopup opens with date fields | | |
| 7.2 | "New Issue Date" field visible | Popup | Date picker | | |
| 7.3 | "New Expiry Date" field visible | Popup | Date picker | | |
| 7.4 | Optional fields visible | Popup | "New Certificate Number", "New Issuing Authority" (optional) | | |
| 7.5 | Fill dates | Date fields | Issue: 2026-04-16, Expiry: 2027-04-16 | | |
| 7.6 | Submit | **Confirm** / **Submit** | Popup closes, status changes | | |
| 7.7 | Old cert status = Superseded | Lens or list | Old cert now shows "Superseded" pill | | |
| 7.8 | New cert appears | Certificate list | New cert with status "Valid" and expiry 2027-04-16 | | |

**Notes / errors for Scenario 7:**
```
[paste here]
```

---

## Scenario 8 — Captain assigns responsible officer

**Open any cert.**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 8.1 | Click dropdown → **Assign Officer** | Dropdown menu | ActionPopup opens with "Responsible Officer" field | | |
| 8.2 | Select or type an officer | Lookup field | Crew search or text input | | |
| 8.3 | Submit | **Confirm** / **Submit** | Popup closes | | |
| 8.4 | "Responsible Officer" row visible | Detail section | Shows assigned officer name | | |

**Notes / errors for Scenario 8:**
```
[paste here]
```

---

## Scenario 9 — Captain archives a certificate (SIGNED action)

**Open any cert (ideally the suspended cert from Scenario 6).**

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 9.1 | Click dropdown → **Archive** | Dropdown (danger item) | Confirmation popup with signature requirement | | |
| 9.2 | Confirmation message visible | Popup | "This will archive this certificate record." | | |
| 9.3 | Submit with signature | Popup | Popup closes | | |
| 9.4 | Cert removed from list | Navigate back to list | Archived cert no longer visible | | |
| 9.5 | Register page excludes it | `/certificates/register` | Archived cert absent from printable register | | |

**Notes / errors for Scenario 9:**
```
[paste here]
```

---

## Scenario 10 — Certificate Register (print view)

**Login:** `captain.tenant@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 10.1 | Navigate to `/certificates/register` | URL or link from cert list | Register page loads | | |
| 10.2 | Vessel name in header | Page header | Shows yacht name, not UUID | | |
| 10.3 | Urgency groups visible | Page body | At least one of: Expired / Expiring 30d / Expiring 90d / Valid / Terminal | | |
| 10.4 | Certs show real names | Table rows | Certificate names, not UUIDs | | |
| 10.5 | Crew certs included | Table rows | Crew certs visible with "Crew" tag | | |
| 10.6 | "Print Register" button | Top-right | Opens browser print dialog | | |
| 10.7 | Print layout renders correctly | Print preview | A4 format, no screen-only elements | | |

**Notes / errors for Scenario 10:**
```
[paste here]
```

---

## Scenario 11 — Role gating: Engineer on crew certs

**Login:** `engineer.test@alex-short.com` / `Password2!`

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 11.1 | Navigate to Certificates | Sidebar | List loads | | |
| 11.2 | Open a **vessel** cert | Click row | Lens loads, dropdown has Update/Add Note/etc. (engineer IS allowed) | | |
| 11.3 | Open a **crew** cert | Click row | Lens loads | | |
| 11.4 | Check dropdown on crew cert | Open dropdown | Update / Suspend / Revoke / Archive should NOT appear (engineer excluded from crew cert mutations) | | |
| 11.5 | "Add Note" still visible on crew cert | Dropdown | Add Note should appear (8-HOD union) | | |

**Notes / errors for Scenario 11:**
```
Actions visible on vessel cert dropdown:

Actions visible on crew cert dropdown:

```

---

## Scenario 12 — Dashboard widget shows certs

**Login:** any role

| # | Step | Button / Location | Expected | Y / N / ERR | Console errors |
|---|------|-------------------|----------|-------------|----------------|
| 12.1 | Navigate to dashboard | `/` or sidebar home | Dashboard loads | | |
| 12.2 | Certificate expiry widget visible | Dashboard cards/widgets | Widget shows upcoming expirations | | |
| 12.3 | Cert names readable | Widget rows | Real names, not UUIDs | | |
| 12.4 | Already-expired certs included | Widget | Past-due certs shown (not filtered out) | | |
| 12.5 | Click a cert in widget | Widget row | Navigates to cert lens page | | |

**Notes / errors for Scenario 12:**
```
[paste here]
```

---

## Scenario 13 — Notifications pushed on cert events

**Login:** Captain creates a cert, then check HOD's notifications.

| # | Step | Expected | Y / N / ERR | Console errors |
|---|------|----------|-------------|----------------|
| 13.1 | Captain creates a vessel cert (Scenario 2) | `pms_notifications` row inserted for HODs | | |
| 13.2 | Log in as HOD (`hod.test@alex-short.com`) | Dashboard loads | | |
| 13.3 | Check notification bell/panel | Notification with cert name visible | | |
| 13.4 | Notification title includes cert name | e.g. "Certificate Created: Test Class Certificate" | | |
| 13.5 | Click notification | Navigates to the certificate lens page | | |

**Notes / errors for Scenario 13:**
```
[paste here]
```

---

## DB / Ledger spot check (after completing Scenarios 2–9)

Replace `$CERT_ID` with a certificate UUID from the URL bar or API response.

```bash
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
CERT_ID="<paste certificate UUID>"

# Check cert row exists
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT id, certificate_name, status, created_by, deleted_at FROM pms_vessel_certificates WHERE id='$CERT_ID';"

# Check ledger_events for all cert actions
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT event_type, action, user_role, change_summary, created_at FROM ledger_events WHERE entity_type='certificate' AND entity_id='$CERT_ID' ORDER BY created_at;"

# Check audit log
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT action, old_values, new_values, created_at FROM pms_audit_log WHERE entity_id='$CERT_ID' ORDER BY created_at;"

# Check notifications pushed
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT notification_type, title, priority, created_at FROM pms_notifications WHERE entity_type='certificate' AND entity_id='$CERT_ID' ORDER BY created_at;"

# Check notes
PGPASSWORD='@-Ei-9Pa.uENn6g' psql "postgresql://postgres@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres?sslmode=require" \
  -c "SELECT text, created_by, created_at FROM pms_notes WHERE certificate_id='$CERT_ID';"
```

| # | DB check | Expected | Y / N / ERR |
|---|----------|----------|-------------|
| DB1 | `pms_vessel_certificates` row exists with `created_by` set | Row present | |
| DB2 | `ledger_events` has `create` event (from Scenario 2) | Row present | |
| DB3 | `ledger_events` has `status_change` event (from Scenario 6 suspend) | Row present | |
| DB4 | `pms_audit_log` has `suspended_certificate` action | Row with old/new values | |
| DB5 | `pms_notifications` rows for created/suspended events | Notification rows present | |
| DB6 | `pms_notes` row with test note text (from Scenario 5) | Row present with certificate_id FK | |

---

## Role matrix (quick reference)

| Role | Create vessel | Create crew | Update | Suspend | Revoke | Archive | Add Note | Assign | Link Doc | Renew |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| captain | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| manager | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| chief_engineer | Y | Y | Y | N | N | Y | Y | Y | Y | Y |
| chief_officer | Y | Y | Y | N | N | Y | Y | Y | Y | Y |
| purser | N | Y | Y* | N | N | Y* | Y | Y* | Y* | Y* |
| chief_steward | N | Y | Y* | N | N | Y* | Y | Y* | Y* | Y* |
| engineer | Y | N | Y* | N | N | Y* | Y | Y* | Y* | Y* |
| eto | Y | N | Y* | N | N | Y* | Y | Y* | Y* | Y* |
| crew | N | N | N | N | N | N | N | N | N | N |

`Y*` = Allowed by registry but **mutation gate narrows by domain**: purser/chief_steward blocked from vessel certs, engineer/eto blocked from crew certs.

---

## Known gaps (honest)

| Gap | Impact | Notes |
|-----|--------|-------|
| No `_cert_mutation_gate` on `add_certificate_note` | Any HOD can add a note to any cert regardless of domain | Deliberate: notes are documentation, not mutations |
| `person_node_id` not `person_id` | Column naming inconsistency on `pms_crew_certificates` | Historical — FK to `search_graph_nodes.id` |
| No document versioning for certs | One document per cert (FK), no revision history | Phase 2 |
| Projection worker for crew certs | Just added — may need first poll cycle to appear in F1 search | Wait for worker to poll |

---

## HMAC01 notes (receipt-layer integration)

| # | What HMAC01 needs to know |
|---|--------------------------|
| H1 | Ledger `entity_type` = `certificate`, `entity_id` = cert UUID |
| H2 | Actions: create_vessel/crew, update, suspend, revoke, archive, renew, supersede, assign, add_note, link_document |
| H3 | `proof_hash` via safety net → `build_ledger_event` in `ledger_utils.py` |
| H4 | Source tables: `pms_vessel_certificates` + `pms_crew_certificates`, unified via `v_certificates_enriched` |
| H5 | Signed actions: suspend, revoke, archive, supersede require signature payload |
| H6 | Receipt shape: **single** (one cert), **scope** (all vessel certs for compliance), **period** (expiry audit window) |
| H7 | Adapter queries: `v_certificates_enriched` for records, `ledger_events WHERE entity_type='certificate'` for trail |
| H8 | Nightly expiry: `refresh_certificate_expiry()` DB function writes ledger directly (source_context=system) |
| H9 | Full integration notes: `docs/explanations/LENS_DOMAINS/certificates_hmac_integration.md` |

---

*Edit freely — paste console logs, API responses, mark pass/fail inline.*
