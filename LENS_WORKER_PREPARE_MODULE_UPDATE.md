# Lens Worker: Prepare Module Update Instructions

**Date**: 2026-01-30
**Purpose**: Update `apps/api/prepare/capability_composer.py` with your lens-specific database tables to enable comprehensive search

---

## Background

The **Prepare Module** (`capability_composer.py`) maps entity types to database search capabilities. During recent migrations, new lens tables were added but the prepare module was not updated accordingly. This causes search to rely on a **legacy small corpus**, missing results from newer lens tables.

**Your Task**: Add your lens's tables to the entity-to-table mapping so users can search across ALL your lens data.

---

## Step 1: Locate Your Lens Ground Truth

Find your lens's database schema specification:

```
docs/pipeline/entity_lenses/{YOUR_LENS_NAME}/v2/{YOUR_LENS_NAME}_v2_FINAL.md
```

**Examples**:
- Part Lens: `docs/pipeline/entity_lenses/part_lens/v2/part_lens_v2_FINAL.md`
- Certificate Lens: `docs/pipeline/entity_lenses/certificate_lens/v2/certificate_lens_v2_FINAL.md`
- Crew Lens: `docs/pipeline/entity_lenses/crew_lens/v2/crew_lens_v2_FINAL.md`
- Work Order Lens: `docs/pipeline/entity_lenses/work_order_lens/v2/work_order_lens_v2_FINAL.md`

---

## Step 2: Extract Database Schema

Open your `*_FINAL.md` file and navigate to **PART 1: DATABASE SCHEMA**.

Extract ALL tables defined in your lens. For each table, identify:
1. **Table name** (e.g., `pms_parts`, `pms_crew_members`, `pms_certificates`)
2. **Searchable columns** (text fields users would search: name, title, description, code, etc.)
3. **Entity types** (what users call these things: PART_NAME, CREW_NAME, CERTIFICATE_TYPE, etc.)

---

## Step 3: Map Entity Types to Capabilities

For each searchable entity type in your lens, create a mapping entry.

**Format**:
```python
"ENTITY_TYPE_NAME": ("capability_name", "column_name")
```

### 3.1 Define Capability Names

A **capability** is a searchable database function. Name it descriptively:

**Pattern**: `{entity}_by_{search_attribute}`

**Examples**:
- Part search by name → `part_by_part_number_or_name`
- Crew search by name → `crew_by_name`
- Certificate search by type → `certificate_by_type_or_holder`
- Work order search by ID → `work_order_by_id`

### 3.2 Identify Searchable Columns

List the primary searchable column for each capability.

**Example (Part Lens)**:

| Entity Type | Capability Name | Column | Table |
|-------------|-----------------|--------|-------|
| PART_NUMBER | part_by_part_number_or_name | part_number | pms_parts |
| PART_NAME | part_by_part_number_or_name | name | pms_parts |
| MANUFACTURER | part_by_part_number_or_name | manufacturer | pms_parts |
| LOCATION | inventory_by_location | location | pms_inventory_stock |

**Example (Certificate Lens)**:

| Entity Type | Capability Name | Column | Table |
|-------------|-----------------|--------|-------|
| CERTIFICATE_TYPE | certificate_by_type_or_holder | certificate_type | pms_certificates |
| CERTIFICATE_HOLDER | certificate_by_type_or_holder | holder_name | pms_certificates |
| CERTIFICATE_NUMBER | certificate_by_number | certificate_number | pms_certificates |

**Example (Crew Lens)**:

| Entity Type | Capability Name | Column | Table |
|-------------|-----------------|--------|-------|
| CREW_NAME | crew_by_name | full_name | pms_crew_members |
| CREW_ROLE | crew_by_role | role | pms_crew_members |
| CREW_RANK | crew_by_rank | rank | pms_crew_members |

---

## Step 4: Update `capability_composer.py`

Open `apps/api/prepare/capability_composer.py` and locate the `ENTITY_TO_SEARCH_COLUMN` dictionary (around line 113).

Add your mappings to the dictionary.

### 4.1 Current State (Outdated)

```python
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    "PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
    "PART_NAME": ("part_by_part_number_or_name", "name"),
    "MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),
    "LOCATION": ("inventory_by_location", "location"),
    "FAULT_CODE": ("fault_by_fault_code", "code"),
    "EQUIPMENT_TYPE": ("fault_by_fault_code", "equipment_type"),
    "DOCUMENT_QUERY": ("documents_search", "content"),
    "WORK_ORDER_ID": ("work_order_by_id", "wo_number"),
    "EQUIPMENT_NAME": ("equipment_by_name_or_model", "name"),
    "EMAIL_SUBJECT": ("email_threads_search", "latest_subject"),
}
```

### 4.2 Add Your Lens Entries

**Example: Part Lens Worker**

```python
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    # Existing entries...
    "PART_NUMBER": ("part_by_part_number_or_name", "part_number"),
    "PART_NAME": ("part_by_part_number_or_name", "name"),
    "MANUFACTURER": ("part_by_part_number_or_name", "manufacturer"),
    "LOCATION": ("inventory_by_location", "location"),

    # NEW: Part Lens additions
    "PART_CATEGORY": ("part_by_category", "category"),
    "PART_SUBCATEGORY": ("part_by_category", "subcategory"),
    "STOCK_LOCATION": ("inventory_by_stock_location", "storage_location"),
    "SHOPPING_LIST_ITEM": ("shopping_list_by_part", "part_name"),
    "TRANSACTION_TYPE": ("inventory_transaction_by_type", "transaction_type"),

    # ... other lenses ...
}
```

**Example: Certificate Lens Worker**

```python
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    # ... existing entries ...

    # NEW: Certificate Lens additions
    "CERTIFICATE_TYPE": ("certificate_by_type_or_holder", "certificate_type"),
    "CERTIFICATE_HOLDER": ("certificate_by_type_or_holder", "holder_name"),
    "CERTIFICATE_NUMBER": ("certificate_by_number", "certificate_number"),
    "CERTIFICATE_ISSUER": ("certificate_by_issuer", "issuing_authority"),
    "CERTIFICATE_STATUS": ("certificate_by_status", "status"),

    # ... other lenses ...
}
```

**Example: Crew Lens Worker**

```python
ENTITY_TO_SEARCH_COLUMN: Dict[str, Tuple[str, str]] = {
    # ... existing entries ...

    # NEW: Crew Lens additions
    "CREW_NAME": ("crew_by_name", "full_name"),
    "CREW_ROLE": ("crew_by_role", "role"),
    "CREW_RANK": ("crew_by_rank", "rank"),
    "CREW_DEPARTMENT": ("crew_by_department", "department"),
    "CREW_STATUS": ("crew_by_status", "employment_status"),

    # ... other lenses ...
}
```

---

## Step 5: Define Capability Implementations

For each new capability name you added, you MUST implement the corresponding database query function.

Locate the `CapabilityComposer` class in `capability_composer.py` and add methods for your capabilities.

### 5.1 Capability Method Template

```python
async def {capability_name}(
    self,
    yacht_id: str,
    search_term: str,
    column_name: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search {ENTITY} by {ATTRIBUTE}.

    Args:
        yacht_id: Tenant isolation key
        search_term: User's search query
        column_name: Column to search (e.g., 'name', 'part_number')
        limit: Max results to return

    Returns:
        List of matching records with id, type, title, score
    """
    query = f"""
        SELECT
            id,
            '{entity_type}' as type,
            {title_column} as title,
            {additional_fields},
            similarity({column_name}, %s) as score
        FROM {table_name}
        WHERE yacht_id = %s
          AND {column_name} ILIKE %s
        ORDER BY score DESC, {title_column} ASC
        LIMIT %s
    """

    params = [search_term, yacht_id, f"%{search_term}%", limit]
    results = await self.db.fetch_all(query, params)

    return [dict(row) for row in results]
```

### 5.2 Example: Part Lens Capability

```python
async def inventory_by_stock_location(
    self,
    yacht_id: str,
    search_term: str,
    column_name: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search inventory stock by storage location."""
    query = """
        SELECT
            s.id,
            'inventory_stock' as type,
            CONCAT(p.name, ' @ ', s.storage_location) as title,
            s.on_hand,
            s.storage_location,
            similarity(s.storage_location, %s) as score
        FROM pms_inventory_stock s
        JOIN pms_parts p ON s.part_id = p.id
        WHERE s.yacht_id = %s
          AND s.storage_location ILIKE %s
        ORDER BY score DESC, p.name ASC
        LIMIT %s
    """

    params = [search_term, yacht_id, f"%{search_term}%", limit]
    results = await self.db.fetch_all(query, params)

    return [dict(row) for row in results]
```

### 5.3 Example: Certificate Lens Capability

```python
async def certificate_by_type_or_holder(
    self,
    yacht_id: str,
    search_term: str,
    column_name: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Search certificates by type or holder name."""
    query = """
        SELECT
            id,
            'certificate' as type,
            CONCAT(certificate_type, ' - ', holder_name) as title,
            certificate_number,
            expiry_date,
            status,
            GREATEST(
                similarity(certificate_type, %s),
                similarity(holder_name, %s)
            ) as score
        FROM pms_certificates
        WHERE yacht_id = %s
          AND (certificate_type ILIKE %s OR holder_name ILIKE %s)
        ORDER BY score DESC, certificate_type ASC
        LIMIT %s
    """

    params = [
        search_term, search_term,  # for similarity()
        yacht_id,
        f"%{search_term}%", f"%{search_term}%",  # for ILIKE
        limit
    ]
    results = await self.db.fetch_all(query, params)

    return [dict(row) for row in results]
```

---

## Step 6: Test Your Changes

### 6.1 Unit Test

Create a test for your capability in `tests/unit/prepare/test_capability_composer.py`:

```python
@pytest.mark.asyncio
async def test_your_capability_name():
    composer = CapabilityComposer(db_client)

    results = await composer.your_capability_name(
        yacht_id="test-yacht-id",
        search_term="test query",
        column_name="your_column",
        limit=10
    )

    assert len(results) > 0
    assert results[0]["type"] == "expected_type"
    assert "title" in results[0]
    assert "score" in results[0]
```

### 6.2 Integration Test

Test search with your new entity types:

```bash
# Search for entity in your lens
curl -X POST https://app.celeste7.ai/webhook/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test query with your entity type",
    "yacht_id": "your-yacht-id"
  }'
```

Verify your lens entities appear in results.

---

## Step 7: Submit Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/prepare-module-{YOUR_LENS_NAME}
   ```

2. Commit your changes:
   ```bash
   git add apps/api/prepare/capability_composer.py
   git add tests/unit/prepare/test_capability_composer.py
   git commit -m "Add {YOUR_LENS_NAME} tables to prepare module

   - Added entity-to-table mappings for {LENS_NAME}
   - Implemented capabilities: {list_capabilities}
   - Enables search across {LENS_NAME} tables
   - Ref: PART_LENS_ARCHITECTURE_GAP.md"
   ```

3. Push and create PR:
   ```bash
   git push origin feature/prepare-module-{YOUR_LENS_NAME}
   ```

4. Tag reviewers familiar with search infrastructure

---

## Reference: All Lens Tables

Extract from your lens spec, but here's a general guide:

### Part Lens Tables
- `pms_parts` (core part data)
- `pms_inventory_stock` (stock levels by location)
- `pms_inventory_transactions` (receive, consume, transfer, adjust)
- `pms_part_usage` (equipment-part relationships)
- `pms_shopping_list_items` (procurement requests)

### Certificate Lens Tables
- `pms_certificates` (all certificates)
- `pms_certificate_holders` (crew/vendor associations)
- `pms_certificate_renewals` (renewal history)

### Crew Lens Tables
- `pms_crew_members` (personnel records)
- `pms_crew_qualifications` (certifications, training)
- `pms_crew_assignments` (role assignments)

### Work Order Lens Tables
- `pms_work_orders` (maintenance tasks)
- `pms_work_order_parts` (parts used in WOs)
- `pms_work_order_labor` (labor tracking)

### Document Lens Tables
- `pms_documents` (all documents)
- `pms_document_chunks` (RAG embeddings)
- `pms_document_versions` (version control)

---

## Questions?

If you're unsure about:
- **Entity type names**: Check `docs/entity_extraction/entity_types.md`
- **Table schemas**: Your lens's `*_FINAL.md` PART 1: DATABASE SCHEMA
- **Capability naming**: Follow the pattern `{entity}_by_{attribute}`
- **SQL queries**: Review existing capabilities in `capability_composer.py` lines 200-500

**Contact**: Claude Code team or your lens lead

---

## Expected Outcome

After all lens workers complete this task:

✅ Comprehensive search across ALL lens tables
✅ Entity extraction maps to correct database capabilities
✅ No more "legacy small corpus" limitation
✅ Users find results regardless of query phrasing
✅ Search supports all entity types defined in lens specs

**Timeline**: Complete within 1 week to unblock E2E test suite and user-facing search improvements.
