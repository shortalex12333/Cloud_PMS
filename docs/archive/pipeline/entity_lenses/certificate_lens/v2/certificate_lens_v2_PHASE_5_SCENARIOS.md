# Certificate Lens v2 - Phase 5: UX Flows & Scenarios
**Status**: SCENARIOS COMPLETE
**Date**: 2026-01-25

---

## PURPOSE

This phase documents 10 real-world scenarios showing how Certificate Lens operates under the single search bar paradigm. Each scenario includes Traditional (dashboard) vs Celeste (search-first) comparison with step counts.

---

# SCENARIO 1: Create New Class Certificate

**User**: Chief Engineer
**Goal**: Record the yacht's new Class Certificate from Lloyds

## Traditional Approach (Dashboard)
1. Navigate to main menu
2. Click "Compliance" or "Certificates"
3. Click "Vessel Certificates" tab
4. Click "Add New Certificate" button
5. Fill form: type=class, name, authority, dates
6. Click "Upload Document"
7. Select file from device
8. Click "Save"
9. Navigate back to list to verify

**Steps**: 9

## Celeste Approach (Search-First)
1. Type "new class certificate" in search bar
2. Entity extraction shows "Create Vessel Certificate" action
3. Fill minimal fields: name, authority, expiry
4. Upload document (inline)
5. Confirm

**Steps**: 5

## Step Reduction: 44%

## SQL Query (Focus Resolution)
```sql
-- No query needed - action is context-aware from search intent
-- Certificate creation proceeds directly
```

## Ledger Output
```json
{
  "event": "certificate_created",
  "message": "Class Certificate 'Lloyds Class A' created",
  "entity_type": "certificate",
  "entity_id": "abc-123-uuid",
  "user_name": "Chief Engineer",
  "timestamp": "2026-01-25T09:00:00Z"
}
```

---

# SCENARIO 2: Find Expiring Certificates

**User**: Captain
**Goal**: See which certificates expire in the next 90 days

## Traditional Approach (Dashboard)
1. Navigate to Compliance module
2. Click "Vessel Certificates"
3. Look for "Expiring Soon" filter or tab
4. If no filter, manually sort by expiry date
5. Scroll through list counting days
6. Click each certificate to see details
7. Repeat for "Crew Certificates" section
8. Cross-reference manually

**Steps**: 8+

## Celeste Approach (Search-First)
1. Type "certificates expiring next 90 days"
2. System shows unified list (vessel + crew)
3. Focus any certificate for actions

**Steps**: 3

## Step Reduction: 62%

## SQL Query
```sql
-- Unified expiring certificates query
SELECT
    'vessel' AS cert_category,
    c.id,
    c.certificate_type,
    c.certificate_name AS name,
    NULL AS person_name,
    c.expiry_date,
    c.status,
    (c.expiry_date - current_date) AS days_until_expiry
FROM pms_vessel_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.expiry_date IS NOT NULL
  AND c.expiry_date <= current_date + INTERVAL '90 days'
  AND c.expiry_date >= current_date
  AND c.status != 'superseded'

UNION ALL

SELECT
    'crew' AS cert_category,
    c.id,
    c.certificate_type,
    c.certificate_type AS name,
    c.person_name,
    c.expiry_date,
    'valid' AS status,
    (c.expiry_date - current_date) AS days_until_expiry
FROM pms_crew_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.expiry_date IS NOT NULL
  AND c.expiry_date <= current_date + INTERVAL '90 days'
  AND c.expiry_date >= current_date

ORDER BY days_until_expiry ASC;
```

---

# SCENARIO 3: Supersede Expiring ISM Certificate

**User**: Captain
**Goal**: Renew the ISM DOC certificate (requires signature)

## Traditional Approach (Dashboard)
1. Navigate to Compliance module
2. Click "Vessel Certificates"
3. Search or scroll to find ISM DOC
4. Click to open details
5. Click "Renew" or "Supersede" button
6. Fill new certificate details
7. Upload new document
8. Look for signature area (may be separate workflow)
9. Sign document
10. Submit
11. Verify old cert marked superseded
12. Navigate to new cert to confirm

**Steps**: 12

## Celeste Approach (Search-First)
1. Type "ISM certificate" in search bar
2. Focus the current ISM DOC certificate
3. Select "Supersede Certificate" action
4. Fill new details (name, number, dates)
5. Upload new document
6. Sign (inline signature capture)
7. Confirm

**Steps**: 7

## Step Reduction: 42%

## SQL Query (Focus)
```sql
SELECT
    c.id,
    c.certificate_type,
    c.certificate_name,
    c.certificate_number,
    c.issuing_authority,
    c.expiry_date,
    c.status,
    d.filename AS document_filename
FROM pms_vessel_certificates c
LEFT JOIN doc_metadata d ON c.document_id = d.id
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.certificate_type ILIKE '%ism%'
  AND c.status = 'valid'
ORDER BY c.created_at DESC
LIMIT 1;
```

## Signature Requirements
- Signature payload captured inline
- Stored in audit_log.signature (NOT NULL)
- Old certificate status → 'superseded'
- New certificate status = 'valid'

---

# SCENARIO 4: Add STCW Certificate for New Crew

**User**: Purser
**Goal**: Record STCW II/1 certificate for new deckhand

## Traditional Approach (Dashboard)
1. Navigate to Crew module
2. Find crew member profile
3. Click "Certifications" tab
4. Click "Add Certification"
5. Select certificate type
6. Fill details
7. Upload scan
8. Save
9. Navigate back to verify

**Steps**: 9

## Celeste Approach (Search-First)
1. Type "John Smith STCW" or focus crew member
2. Select "Add Certificate" action
3. Fill: type=STCW II/1, authority, dates
4. Upload scan (inline)
5. Confirm

**Steps**: 5

## Step Reduction: 44%

## SQL Query (Crew Focus Resolution)
```sql
-- If searching by person name
SELECT
    c.id,
    c.person_name,
    c.certificate_type,
    c.certificate_number,
    c.issuing_authority,
    c.expiry_date,
    d.filename AS document_filename
FROM pms_crew_certificates c
LEFT JOIN doc_metadata d ON c.document_id = d.id
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.person_name ILIKE '%' || :search_term || '%'
ORDER BY c.created_at DESC;
```

---

# SCENARIO 5: View Certificate Document

**User**: Deckhand (read-only)
**Goal**: View the Safety Equipment Certificate PDF

## Traditional Approach (Dashboard)
1. Navigate to Compliance
2. Click Vessel Certificates
3. Search for Safety Equipment
4. Click certificate row
5. Look for "View Document" or paperclip icon
6. Click to download/view

**Steps**: 6

## Celeste Approach (Search-First)
1. Type "safety equipment certificate"
2. Focus certificate from results
3. Click document link (escape hatch to Document Lens)

**Steps**: 3

## Step Reduction: 50%

## SQL Query
```sql
SELECT
    c.id AS certificate_id,
    c.certificate_name,
    d.id AS document_id,
    d.filename,
    d.storage_path,
    d.content_type
FROM pms_vessel_certificates c
JOIN doc_metadata d ON c.document_id = d.id
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.certificate_type ILIKE '%safety%equipment%'
  AND c.status = 'valid';
```

## Escape Hatch
- From Certificate Lens → Document Lens
- Trigger: Click on document_id/filename
- Document Lens provides: view, download, signed URL

---

# SCENARIO 6: Audit Trail for Certificate Change

**User**: Manager (Shore-based)
**Goal**: Who changed the Radio License and when?

## Traditional Approach (Dashboard)
1. Navigate to Compliance
2. Find Radio License certificate
3. Look for "History" or "Audit Log" tab
4. If exists, click to view
5. If not, check separate Audit module
6. Filter by entity type
7. Find relevant entries

**Steps**: 7+

## Celeste Approach (Search-First)
1. Type "radio license history"
2. Focus the certificate
3. "View History" action shows inline audit trail

**Steps**: 3

## Step Reduction: 57%

## SQL Query
```sql
SELECT
    a.action,
    a.old_values,
    a.new_values,
    CASE WHEN a.signature != '{}'::jsonb THEN 'Signed' ELSE 'Unsigned' END AS signature_status,
    a.created_at,
    (SELECT name FROM auth_users_profiles WHERE id = a.user_id) AS user_name,
    a.metadata
FROM pms_audit_log a
WHERE a.entity_type = 'certificate'
  AND a.entity_id = :certificate_id
  AND a.yacht_id = public.get_user_yacht_id()
ORDER BY a.created_at DESC;
```

---

# SCENARIO 7: Bulk Expiration Check Before Charter

**User**: Captain
**Goal**: Verify all certificates are valid before guest arrival

## Traditional Approach (Dashboard)
1. Navigate to Compliance
2. View Vessel Certificates list
3. Check each certificate status manually
4. Navigate to Crew Certificates
5. Check each crew member's certs
6. Make list of issues
7. Create reminders/tasks for each

**Steps**: 7+

## Celeste Approach (Search-First)
1. Type "certificates status check"
2. System shows grouped results:
   - ✅ Valid (not expiring soon)
   - ⚠️ Due Soon (30 days)
   - ❌ Expired
3. Focus any problematic cert for action

**Steps**: 3

## Step Reduction: 57%

## SQL Query
```sql
-- Status summary query
SELECT
    CASE
        WHEN c.expiry_date IS NULL THEN 'no_expiry'
        WHEN c.expiry_date < current_date THEN 'expired'
        WHEN c.expiry_date <= current_date + INTERVAL '30 days' THEN 'due_soon'
        ELSE 'valid'
    END AS status_category,
    COUNT(*) AS count,
    array_agg(jsonb_build_object(
        'id', c.id,
        'type', c.certificate_type,
        'name', c.certificate_name,
        'expiry_date', c.expiry_date
    )) AS certificates
FROM pms_vessel_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.status != 'superseded'
GROUP BY status_category

UNION ALL

SELECT
    CASE
        WHEN c.expiry_date IS NULL THEN 'no_expiry'
        WHEN c.expiry_date < current_date THEN 'expired'
        WHEN c.expiry_date <= current_date + INTERVAL '30 days' THEN 'due_soon'
        ELSE 'valid'
    END AS status_category,
    COUNT(*) AS count,
    array_agg(jsonb_build_object(
        'id', c.id,
        'type', c.certificate_type,
        'person', c.person_name,
        'expiry_date', c.expiry_date
    )) AS certificates
FROM pms_crew_certificates c
WHERE c.yacht_id = public.get_user_yacht_id()
GROUP BY status_category;
```

---

# SCENARIO 8: Link Document to Existing Certificate

**User**: Chief Engineer
**Goal**: Attach newly scanned certificate PDF to existing record

## Traditional Approach (Dashboard)
1. Navigate to Compliance
2. Find the certificate
3. Open details
4. Look for "Attach Document" option
5. If none, navigate to Documents module
6. Upload file with manual tagging
7. Return to certificate
8. Try to link (may not be possible)
9. Alternatively: delete and recreate certificate with document

**Steps**: 9+

## Celeste Approach (Search-First)
1. Type "load line certificate"
2. Focus the certificate
3. Select "Link Document" action
4. Upload or select from recent
5. Confirm

**Steps**: 5

## Step Reduction: 44%

## SQL Query
```sql
-- After upload to doc_metadata, link to certificate
UPDATE pms_vessel_certificates
SET document_id = :document_id
WHERE id = :certificate_id
  AND yacht_id = public.get_user_yacht_id();
```

---

# SCENARIO 9: Find All Certificates for Specific Crew Member

**User**: Purser
**Goal**: Compile certificate list for crew immigration paperwork

## Traditional Approach (Dashboard)
1. Navigate to Crew module
2. Find crew member
3. Open profile
4. Find Certifications section
5. Export or screenshot each
6. Compile into document

**Steps**: 6

## Celeste Approach (Search-First)
1. Type "John Smith certificates"
2. System shows all certificates for that person
3. Export/print action available

**Steps**: 3

## Step Reduction: 50%

## SQL Query
```sql
SELECT
    c.id,
    c.certificate_type,
    c.certificate_number,
    c.issuing_authority,
    c.issue_date,
    c.expiry_date,
    CASE
        WHEN c.expiry_date IS NULL THEN 'No Expiry'
        WHEN c.expiry_date < current_date THEN 'EXPIRED'
        WHEN c.expiry_date <= current_date + INTERVAL '30 days' THEN 'Due Soon'
        ELSE 'Valid'
    END AS validity_status,
    d.filename AS document_filename
FROM pms_crew_certificates c
LEFT JOIN doc_metadata d ON c.document_id = d.id
WHERE c.yacht_id = public.get_user_yacht_id()
  AND c.person_name ILIKE '%' || :person_name || '%'
ORDER BY c.expiry_date NULLS LAST;
```

---

# SCENARIO 10: Update Certificate After Survey

**User**: Chief Engineer
**Goal**: Update last_survey_date and next_survey_due after annual survey

## Traditional Approach (Dashboard)
1. Navigate to Compliance
2. Find the certificate
3. Click "Edit"
4. Update survey fields
5. Save
6. Optionally attach survey report
7. Navigate to documents to upload if separate
8. Return and link

**Steps**: 8

## Celeste Approach (Search-First)
1. Type "class certificate"
2. Focus certificate
3. Select "Update" action
4. Edit survey dates
5. Attach survey report (inline)
6. Confirm

**Steps**: 6

## Step Reduction: 25%

## SQL Query
```sql
UPDATE pms_vessel_certificates
SET
    last_survey_date = :last_survey_date,
    next_survey_due = :next_survey_due,
    document_id = COALESCE(:new_survey_report_doc_id, document_id)
WHERE id = :certificate_id
  AND yacht_id = public.get_user_yacht_id();
```

---

# SCENARIO SUMMARY

| # | Scenario | Traditional | Celeste | Reduction |
|---|----------|-------------|---------|-----------|
| 1 | Create Class Certificate | 9 | 5 | 44% |
| 2 | Find Expiring Certificates | 8+ | 3 | 62% |
| 3 | Supersede ISM Certificate | 12 | 7 | 42% |
| 4 | Add Crew STCW | 9 | 5 | 44% |
| 5 | View Certificate Document | 6 | 3 | 50% |
| 6 | Audit Trail | 7+ | 3 | 57% |
| 7 | Bulk Status Check | 7+ | 3 | 57% |
| 8 | Link Document | 9+ | 5 | 44% |
| 9 | Crew Certificate List | 6 | 3 | 50% |
| 10 | Update After Survey | 8 | 6 | 25% |

**Average Step Reduction**: 47.5%

---

# ESCAPE HATCHES

| From Certificate | To Lens | Trigger |
|------------------|---------|---------|
| View attached document | Document Lens | Click document_id link |
| View crew member | Crew Lens | Click person_name or person_node_id |
| Create related WO | Work Order Lens | "Create maintenance task" if equipment-linked |

---

# EDGE CASES

## 1. Certificate Without Expiry
- Some certificates (e.g., permanent registrations) have no expiry_date
- System shows "No Expiry" instead of date
- Excluded from expiration warnings

## 2. Multiple Certificates Same Type
- Yacht may have multiple class certificates (hull, machinery)
- Query returns all; user focuses specific one
- Unique constraint on (yacht_id, cert_type, cert_number) prevents true duplicates

## 3. Crew Member Leaves Yacht
- Certificates remain for historical record
- Person-linked certificates can be filtered by employment status
- `person_node_id` may reference inactive crew

## 4. Document Upload Fails
- Certificate created without document_id
- User can link document later via Action 5
- No data loss from upload failure

## 5. Signature Capture Fails
- Supersede action cannot complete without signature
- Action remains available; user retries
- No partial state (transaction rollback)

---

**SCENARIOS STATUS**: ✅ COMPLETE - Proceed to Phase 6

---

**END OF PHASE 5**
