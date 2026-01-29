# doc_metadata.description Backfill Plan

**Feature:** V2 Show Related - Document Embedding Prerequisites
**Date:** 2026-01-28
**Priority:** P1 (Blocks document re-ranking)

---

## Problem Statement

The `doc_metadata.description` column was added in migration `20260128_1600_v1_related_text_columns.sql` but is currently **NULL for all existing documents**.

Without descriptions:
- Manual/document embeddings will be based solely on filename (low signal)
- Re-ranking of manuals in Show Related will be ineffective
- Equipment documentation won't surface relevant context

**Blocker:** Document embeddings cannot be enabled until descriptions are populated.

---

## Current State

### Schema
```sql
-- Added in V1 migration
ALTER TABLE doc_metadata ADD COLUMN description TEXT;

COMMENT ON COLUMN doc_metadata.description IS
'Human-readable description for manuals/documents.
Template: system | topics | key procedures.
Backfill manually or via OCR summary.';
```

### Data Inventory (TENANT_1)

Query to assess backfill scope:
```sql
SELECT
  doc_type,
  COUNT(*) AS total,
  COUNT(description) AS has_description,
  COUNT(*) - COUNT(description) AS missing_description
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
GROUP BY doc_type
ORDER BY total DESC;
```

**Expected Results (based on schema):**
- `manual`: ~50-100 docs, 0 descriptions (100% NULL)
- `handover`: 0 docs (handover_exports empty in TENANT_1)
- `attachment`: Unknown count, 0 descriptions

**Action:** Run inventory query to confirm counts before proceeding.

---

## Backfill Strategy

### Phase 1: Manual Curation (Week 2)

**Target:** Critical manuals (equipment with >5 work orders)

**Process:**
1. Export list of manuals linked to high-activity equipment
2. HOD/manager adds descriptions via UI (future feature)
3. Template: `{system_type} | {manufacturer} {model} | Key topics: {topics}`

**Example:**
```
Propulsion | Caterpillar C32 Marine Engine | Key topics: maintenance schedule, oil change, fuel system, troubleshooting codes
```

**Estimated Effort:** 2-3 hours for top 20 manuals

### Phase 2: Filename Parsing (Automated)

**Heuristic:** Extract description from filename patterns

```python
def extract_description_from_filename(filename: str, equipment_context: dict) -> str:
    """
    Parse filename to generate basic description.

    Examples:
      - "CAT_C32_Service_Manual.pdf" → "Caterpillar C32 service manual"
      - "Hydraulic_System_Diagram_2023.pdf" → "Hydraulic system diagram"
      - "MAN_B&W_ME_Maintenance.pdf" → "MAN B&W ME maintenance"
    """
    # Remove extension
    name = filename.replace('.pdf', '').replace('.PDF', '')

    # Replace underscores/hyphens with spaces
    name = name.replace('_', ' ').replace('-', ' ')

    # Add equipment context if available
    if equipment_context:
        eq_name = equipment_context.get('name', '')
        manufacturer = equipment_context.get('manufacturer', '')
        if eq_name and eq_name.lower() not in name.lower():
            return f"{manufacturer} {eq_name} - {name}"

    return name
```

**Backfill Script:**
```python
# apps/api/scripts/backfill_doc_descriptions.py

import os
from supabase import create_client

def backfill_doc_descriptions(yacht_id: str, dry_run: bool = True):
    """
    Backfill doc_metadata.description from filename + equipment context.

    Args:
        yacht_id: Target yacht
        dry_run: If True, only log proposed changes
    """
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))

    # Get docs missing descriptions with equipment context
    result = supabase.table('doc_metadata').select(
        'id, filename, doc_type, equipment_ids, description'
    ).eq('yacht_id', yacht_id).is_(
        'description', 'null'
    ).is_('deleted_at', 'null').limit(500).execute()

    docs = result.data or []
    print(f"Found {len(docs)} docs missing descriptions")

    for doc in docs:
        # Get equipment context
        equipment_context = {}
        if doc.get('equipment_ids') and len(doc['equipment_ids']) > 0:
            eq_result = supabase.table('pms_equipment').select(
                'name, manufacturer, model'
            ).eq('id', doc['equipment_ids'][0]).maybe_single().execute()
            if eq_result.data:
                equipment_context = eq_result.data

        # Generate description
        description = extract_description_from_filename(
            doc['filename'],
            equipment_context
        )

        print(f"  {doc['filename'][:40]} → {description[:60]}")

        if not dry_run:
            supabase.table('doc_metadata').update({
                'description': description
            }).eq('id', doc['id']).eq('yacht_id', yacht_id).execute()

    print(f"\nBackfill {'preview' if dry_run else 'complete'}: {len(docs)} docs")

if __name__ == '__main__':
    # Run in dry-run mode first
    backfill_doc_descriptions(
        yacht_id='85fe1119-b04c-41ac-80f1-829d23322598',
        dry_run=True
    )
```

**Usage:**
```bash
# Preview changes
python apps/api/scripts/backfill_doc_descriptions.py

# Apply to TENANT_1
YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598 \
  python apps/api/scripts/backfill_doc_descriptions.py --apply
```

### Phase 3: OCR Summary (Future - Week 3+)

**For PDFs with poor filenames**, use OCR + GPT-4 to extract summary.

**Process:**
1. Download PDF from storage bucket
2. Extract first 3 pages via OCR (PyPDF2 or pdfplumber)
3. Send to GPT-4 with prompt:
   ```
   Summarize this equipment manual in 1-2 sentences.
   Focus on: system type, manufacturer, model, key topics covered.
   ```
4. Store result in `description` column

**Cost Estimate:**
- 100 manuals × 3 pages × 2000 tokens × $0.01/1K = $6
- One-time cost, high ROI for embedding quality

**Defer:** Only pursue if filename heuristic insufficient.

---

## Validation

### Pre-Backfill Check
```sql
-- Count docs missing descriptions
SELECT COUNT(*)
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
  AND description IS NULL;
```

### Post-Backfill Verification
```sql
-- Verify backfill coverage
SELECT
  doc_type,
  COUNT(*) AS total,
  COUNT(description) AS has_description,
  ROUND(100.0 * COUNT(description) / COUNT(*), 1) AS pct_coverage
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND deleted_at IS NULL
GROUP BY doc_type;

-- Expected: 100% coverage for manual, attachment
```

### Quality Spot Check
```sql
-- Sample 10 descriptions for manual review
SELECT filename, description
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND doc_type = 'manual'
  AND deleted_at IS NULL
ORDER BY RANDOM()
LIMIT 10;
```

---

## Embedding Text Template (Post-Backfill)

Once descriptions are populated, use this template for document embeddings:

```python
def build_doc_embedding_text(doc: dict) -> str:
    """
    Build embedding text for doc_metadata.

    Template: filename | description | equipment context
    """
    parts = []

    if doc.get('filename'):
        parts.append(doc['filename'])

    if doc.get('description'):
        parts.append(doc['description'])

    # Add equipment context if available
    if doc.get('equipment_context'):
        eq = doc['equipment_context']
        eq_parts = []
        if eq.get('name'):
            eq_parts.append(eq['name'])
        if eq.get('manufacturer'):
            eq_parts.append(eq['manufacturer'])
        if eq.get('model'):
            eq_parts.append(eq['model'])
        if eq_parts:
            parts.append(f"Equipment: {' - '.join(eq_parts)}")

    return ' | '.join(parts)
```

**Example Output:**
```
CAT_C32_Service_Manual.pdf | Caterpillar C32 marine engine service manual - maintenance schedule, oil change, fuel system, troubleshooting codes | Equipment: Main Engine - Caterpillar - C32
```

---

## Timeline

| Phase | Task | Owner | ETA | Status |
|-------|------|-------|-----|--------|
| 1 | Run inventory query (TENANT_1) | Engineer | Day 1 | ⏳ Pending |
| 2 | Create backfill script | Engineer | Day 1 | ⏳ Pending |
| 3 | Dry-run filename heuristic | Engineer | Day 1 | ⏳ Pending |
| 4 | Review sample outputs | HOD | Day 2 | ⏳ Pending |
| 5 | Apply backfill to TENANT_1 | Engineer | Day 2 | ⏳ Pending |
| 6 | Validate coverage (>95%) | Engineer | Day 2 | ⏳ Pending |
| 7 | Manual curation (top 20) | HOD/Manager | Week 2 | ⏳ Pending |
| 8 | Enable doc embeddings in V2 | Engineer | Week 2 | ⏳ Pending |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Filename heuristic produces poor descriptions | Medium | Manual curation for top 20 manuals, OCR fallback |
| Large backfill (>1000 docs) impacts DB performance | Low | Batch in chunks of 100, run during off-hours |
| Equipment context missing (orphaned docs) | Low | Fallback to filename-only description |
| OCR cost exceeds budget | Low | Defer OCR to Week 3+, filename heuristic sufficient for MVP |

---

## Success Criteria

✅ **Definition of Done:**
1. `doc_metadata.description` >95% populated for `doc_type = 'manual'`
2. Sample review confirms descriptions are meaningful (not just filename repeats)
3. Equipment context included where available
4. No NULL descriptions for docs linked to high-activity equipment (>5 WOs)
5. Backfill script committed to repo with dry-run option

---

## Next Steps

1. **Immediate:** Run inventory query to assess scope
2. **Day 1:** Implement filename heuristic backfill script
3. **Day 2:** Apply backfill to TENANT_1 (dry-run → apply → validate)
4. **Week 2:** Enable document embeddings in V2 batch refresh worker

---

**Backfill Status:** 🔴 NOT STARTED (blocks V2 document re-ranking)
