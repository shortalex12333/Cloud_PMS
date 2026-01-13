# IMPORT_DATA PRE-IMPLEMENTATION AUDIT
**Version:** 1.0
**Date:** 2026-01-12
**Status:** 🔴 DO NOT IMPLEMENT UNTIL THIS AUDIT IS APPROVED

---

## ⚠️ CRITICAL WARNING

**import_data** is the most dangerous operation in the system.

It can:
- Corrupt thousands of records in seconds
- Bypass normal validation flows
- Contaminate across yachts if isolation fails
- Create cascading referential integrity failures
- Silently mis-map fields causing data loss

**This operation MUST be designed before coding begins.**

---

## SCOPE: What "import_data" Is Allowed To Do

### Mode 1: "Ingest-Only" Import (SHIP FIRST)
**Safe Default - Recommended for V1**

✅ CAN:
- Create new entities only
- Skip duplicates (with warning)
- Validate against existing data
- Provide detailed error reports

❌ CANNOT:
- Update existing records
- Delete records
- Modify foreign key relationships
- Overwrite audit trails

**Rationale:** Ingest-only prevents accidental data destruction. Users can update via normal flows.

---

### Mode 2: "Upsert" Import (SHIP LATER - V2)
**Dangerous - Requires Reconciliation Rules**

✅ CAN:
- Update existing records (if natural key matches)
- Require explicit reconciliation strategy
- Show diff preview before applying

❌ CANNOT:
- Update without user confirmation
- Modify immutable fields
- Skip audit trail

**Rationale:** Upsert is needed for data migrations, but requires strict controls.

**DECISION:** Ship Mode 1 first. Add Mode 2 only after Mode 1 is battle-tested.

---

## THREAT MODEL: How This Breaks in Real Life

### Threat 1: Cross-Yacht Contamination
**Failure Mode:** Wrong yacht_id in imported data

**Attack Vector:**
- User exports data from Yacht A
- User switches to Yacht B
- User imports Yacht A's data into Yacht B
- Result: Data leakage across tenant boundary

**Mitigation (G0.1):**
- NEVER accept yacht_id from import file
- ALWAYS derive yacht_id from authenticated user's profile
- Reject any row that references foreign entities from different yacht
- Validate ALL foreign keys belong to user's yacht

---

### Threat 2: Duplicate Storms
**Failure Mode:** Retry causes thousands of duplicates

**Attack Vector:**
- User uploads 1000-row CSV
- Import succeeds, creates 1000 records
- User doesn't see confirmation (network issue)
- User clicks "Import" again
- Result: 2000 records, half duplicates

**Mitigation (G0.5):**
- Require idempotency_key for every import
- Compute stable hash: `hash(file_bytes + mapping_config + scope)`
- Store hash in `pms_import_jobs`
- If same hash seen → return existing job result, do not re-execute
- Provide "force re-import" option (HOD only) with different idempotency_key

---

### Threat 3: Partial Import Corruption
**Failure Mode:** Half the rows imported, then crash; re-run makes it worse

**Attack Vector:**
- Import 1000 rows
- Row 500 fails validation
- Rows 1-499 already committed
- User fixes row 500, re-imports
- Rows 1-499 now duplicated (or skipped with warnings, causing confusion)

**Mitigation (G0.4):**
- Use deterministic batch transactions
- Batch size: 100 rows
- Each batch is atomic: all 100 succeed or all 100 roll back
- Track which batches completed in `pms_import_jobs`
- On retry: resume from last successful batch
- Provide "undo last import" action (creates compensating deletes)

---

### Threat 4: Referential Mismatch
**Failure Mode:** Imported items reference missing parts/equipment/locations

**Attack Vector:**
- Import shopping list referencing part "ABC-123"
- Part "ABC-123" doesn't exist in database
- Import either:
  - Fails completely (bad UX)
  - Creates orphan reference (data corruption)

**Mitigation (G1.7):**
- Validate ALL foreign keys exist before importing
- For missing references, offer 3 strategies:
  1. **Reject row** (strict mode)
  2. **Create placeholder** (with flag `imported_placeholder = true`)
  3. **Map to existing** (fuzzy match + user confirmation)
- User chooses strategy during dry-run phase
- Log all placeholder creations for later cleanup

---

### Threat 5: Silent Schema Drift
**Failure Mode:** Vendor column names change; mis-mapping causes wrong data in wrong fields

**Attack Vector:**
- User imports CSV where "Price" column actually contains "Weight"
- System imports weights into price field
- No validation catches it (both are numeric)
- Result: Corrupted financial data

**Mitigation (G1.3):**
- Require explicit column mapping (never auto-detect)
- Save mapping_config for reuse
- Show data preview (first 10 rows) with mapping applied
- Validate data types match target schema
- Validate enum values (e.g., status must be in allowed list)
- Validate ranges (e.g., quantity > 0, price > 0)

---

### Threat 6: Privilege Escalation
**Failure Mode:** User imports objects "owned by admin"

**Attack Vector:**
- User crafts CSV with `created_by = admin_user_id`
- Import blindly uses CSV values
- Result: Records appear to be created by admin, bypassing accountability

**Mitigation (G0.2, G0.3, G0.6):**
- NEVER accept accountability fields from import file
- ALWAYS set: `created_by = auth.uid()`
- ALWAYS set: `created_by_name`, `created_by_role` from user_profiles
- Create audit log entry for import job (who, when, how many rows)

---

## REQUIRED INPUTS: Contract

**import_data** MUST require these parameters:

```typescript
interface ImportDataRequest {
  // REQUIRED
  scope: ImportScope;              // What are we importing?
  file_id: string;                 // From file upload (storage)
  mapping_config: MappingConfig;   // Explicit column mapping
  idempotency_key: string;         // For replay safety
  dry_run: boolean;                // Default: true

  // DERIVED (never from client)
  user_id: string;                 // From auth.uid()
  yacht_id: string;                // From user_profiles

  // OPTIONAL
  duplicate_strategy: 'skip' | 'error' | 'update';  // Mode 2 only
  missing_reference_strategy: 'reject' | 'placeholder' | 'fuzzy_match';
  batch_size: number;              // Default: 100
}

enum ImportScope {
  PARTS = 'parts',
  SHOPPING_LIST = 'shopping_list',
  EQUIPMENT = 'equipment',
  PM_SCHEDULES = 'pm_schedules',
  WORK_ORDERS = 'work_orders',
  // NOT ALLOWED: receiving_sessions, audit_log, financial_transactions
}

interface MappingConfig {
  mapping_config_id?: string;      // Saved mapping (optional)
  column_mappings: {
    source_column: string;
    target_field: string;
    transform?: 'uppercase' | 'lowercase' | 'trim' | 'parse_date';
  }[];
  default_values?: {               // For fields not in CSV
    field: string;
    value: any;
  }[];
}
```

**Validation:**
- `scope` must be in allowed list (6 types, not all tables)
- `file_id` must exist in storage and belong to user's yacht
- `mapping_config` must map to valid table schema
- `idempotency_key` must be unique (or match existing job)
- `dry_run` must be `true` on first call

---

## G0 GUARD CHECKLIST FOR IMPORT_DATA

### G0.1: Yacht Isolation (CRITICAL)
```python
# NEVER accept yacht_id from import file
# ALWAYS derive from authenticated user
user = await self.db.table("user_profiles").select(
    "yacht_id, role"
).eq("id", user_id).single().execute()

yacht_id = user.data["yacht_id"]  # Single source of truth

# For EVERY row in import:
row["yacht_id"] = yacht_id  # Force correct yacht_id

# Validate ALL foreign keys belong to this yacht
for fk_field in ["part_id", "equipment_id", "location_id"]:
    if row.get(fk_field):
        fk_entity = await self.db.table(fk_table).select("yacht_id").eq(
            "id", row[fk_field]
        ).single().execute()

        if fk_entity.data["yacht_id"] != yacht_id:
            raise SecurityError(
                f"CRITICAL: Import references entity from different yacht. "
                f"Field: {fk_field}, Entity yacht: {fk_entity.data['yacht_id']}, "
                f"User yacht: {yacht_id}"
            )
```

---

### G0.2: Authentication Gate
```python
user_id = auth.uid()
if not user_id:
    raise Unauthorized("User not authenticated")

# Validate user has active profile
user = await self.db.table("user_profiles").select("*").eq(
    "id", user_id
).eq("active", True).single().execute()

if not user.data:
    raise Unauthorized("User profile not found or inactive")
```

---

### G0.3: Role-Based Access Control
```python
# Only HOD and admin can import
allowed_roles = ["chief_engineer", "chief_officer", "captain", "admin"]

if user.data["role"] not in allowed_roles:
    raise Forbidden(
        f"Role '{user.data['role']}' cannot import data. "
        f"Required: {', '.join(allowed_roles)}"
    )

# Crew can NEVER import (prevents accidental mass changes)
if user.data["role"] in ["crew", "engineer", "deck_officer"]:
    logger.critical(
        f"Import attempt blocked: crew member {user_id} tried to import {scope}"
    )
    raise Forbidden("Import requires Head of Department approval")
```

---

### G0.4: Atomic Batch Transactions
```python
# CANNOT do one huge transaction (timeout risk)
# MUST use deterministic batches

BATCH_SIZE = 100  # Configurable, default 100

batches = [rows[i:i + BATCH_SIZE] for i in range(0, len(rows), BATCH_SIZE)]

for batch_index, batch in enumerate(batches):
    try:
        # BEGIN transaction for this batch
        async with self.db.transaction():
            for row in batch:
                await self.db.table(target_table).insert(row).execute()

        # COMMIT transaction
        # Mark batch as complete
        await self.db.table("pms_import_jobs").update({
            "batches_completed": batch_index + 1,
            "rows_imported": (batch_index + 1) * BATCH_SIZE
        }).eq("id", job_id).execute()

    except Exception as e:
        # ROLLBACK transaction (automatic)
        logger.error(f"Batch {batch_index} failed: {e}")

        # Store error details
        await self.db.table("pms_import_jobs").update({
            "status": "failed",
            "error_batch": batch_index,
            "error_message": str(e)
        }).eq("id", job_id).execute()

        raise  # Stop processing remaining batches
```

---

### G0.5: Idempotency
```python
import hashlib

# Compute stable hash of import operation
idempotency_key = params.get("idempotency_key")
if not idempotency_key:
    # Auto-generate from file content + mapping
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    mapping_hash = hashlib.sha256(
        json.dumps(mapping_config, sort_keys=True).encode()
    ).hexdigest()
    idempotency_key = f"{scope}_{file_hash}_{mapping_hash}"

# Check if already processed
existing_job = await self.db.table("pms_import_jobs").select("*").eq(
    "idempotency_key", idempotency_key
).eq("yacht_id", yacht_id).single().execute()

if existing_job.data:
    # Return existing result, DO NOT re-execute
    logger.info(f"Import already processed: {idempotency_key}")
    return {
        "status": "duplicate",
        "message": "This import was already processed",
        "original_job": existing_job.data
    }

# Store idempotency key with job
await self.db.table("pms_import_jobs").insert({
    "id": job_id,
    "idempotency_key": idempotency_key,
    "yacht_id": yacht_id,
    ...
}).execute()
```

---

### G0.6: Immutable Audit Trail
```python
# Create import job record (audit trail)
job_id = str(uuid.uuid4())

await self.db.table("pms_import_jobs").insert({
    "id": job_id,
    "yacht_id": yacht_id,
    "scope": scope,
    "file_id": file_id,
    "file_name": file_name,
    "mapping_config": mapping_config,  # JSONB
    "idempotency_key": idempotency_key,
    "total_rows": len(rows),
    "valid_rows": len(valid_rows),
    "invalid_rows": len(invalid_rows),
    "imported_rows": 0,  # Updated during processing
    "status": "pending",
    "created_by": user_id,
    "created_by_name": user.data["full_name"],
    "created_by_role": user.data["role"],
    "created_at": datetime.now(timezone.utc).isoformat()
}).execute()

# EVERY imported row gets back-reference
for row in rows:
    row["import_job_id"] = job_id  # Link to import for traceability

# Create audit log for import operation
await self.db.table("pms_audit_log").insert({
    "id": str(uuid.uuid4()),
    "yacht_id": yacht_id,
    "action": "import_data",
    "entity_type": "import_job",
    "entity_id": job_id,
    "user_id": user_id,
    "user_name": user.data["full_name"],
    "user_role": user.data["role"],
    "new_values": {
        "scope": scope,
        "total_rows": len(rows),
        "file_name": file_name
    },
    "changes_summary": (
        f"{user.data['full_name']} imported {len(rows)} {scope} rows "
        f"from {file_name}"
    ),
    "risk_level": "high",
    "created_at": datetime.now(timezone.utc).isoformat()
}).execute()
```

---

### G0.7: State Machine (N/A for import)
Import doesn't have state transitions (it's a one-shot operation), but the **import job** does:

```python
# Import job states
VALID_JOB_TRANSITIONS = {
    'pending': ['validating', 'cancelled'],
    'validating': ['ready', 'validation_failed'],
    'ready': ['processing', 'cancelled'],
    'processing': ['completed', 'failed'],
    'completed': [],  # Terminal
    'failed': ['pending'],  # Allow retry
    'cancelled': []  # Terminal
}

# Enforce state transitions
current_status = job.data["status"]
new_status = "processing"

if new_status not in VALID_JOB_TRANSITIONS.get(current_status, []):
    raise InvalidState(
        f"Cannot transition import job from {current_status} to {new_status}"
    )
```

---

### G0.8: Signature (Required for large imports)
```python
# Require signature for imports over threshold
SIGNATURE_THRESHOLD_ROWS = 100

if len(rows) > SIGNATURE_THRESHOLD_ROWS and not dry_run:
    signature_data = params.get("signature_data")

    if not signature_data:
        raise SignatureRequired(
            f"Signature required for importing {len(rows)} rows "
            f"(threshold: {SIGNATURE_THRESHOLD_ROWS})"
        )

    # Store signature with job
    await self.db.table("pms_import_jobs").update({
        "signature_data": signature_data,
        "signature_timestamp": datetime.now(timezone.utc).isoformat()
    }).eq("id", job_id).execute()
```

---

## EXECUTION FLOW (Engineer-Proof)

### PHASE 1: Create Import Job (Dry-Run Default)

**Endpoint:** `POST /api/import/initialize`

```python
async def initialize_import(params):
    # 1. Validate auth & role (G0.2, G0.3)
    user = await validate_user_and_role(params["user_id"])

    # 2. Compute idempotency key (G0.5)
    idempotency_key = compute_idempotency_key(
        params["file_id"],
        params["mapping_config"],
        params["scope"]
    )

    # 3. Check for duplicate
    existing = await check_existing_import(idempotency_key, user["yacht_id"])
    if existing:
        return {"status": "duplicate", "job": existing}

    # 4. Create import job record (G0.6)
    job_id = str(uuid.uuid4())
    await create_import_job(job_id, params, user, idempotency_key)

    return {
        "status": "created",
        "job_id": job_id,
        "next_step": "parse"
    }
```

---

### PHASE 2: Parse into Staging

**Endpoint:** `POST /api/import/{job_id}/parse`

```python
async def parse_import_file(job_id, yacht_id):
    # 1. Fetch job
    job = await fetch_import_job(job_id, yacht_id)

    # 2. Download file from storage (yacht-scoped)
    file_bytes = await download_file(job["file_id"], yacht_id)

    # 3. Parse CSV/Excel server-side (NEVER trust client)
    rows = parse_file(file_bytes, job["file_format"])

    # 4. Apply column mapping
    mapped_rows = apply_mapping(rows, job["mapping_config"])

    # 5. Write to staging table
    for row_num, row in enumerate(mapped_rows):
        await self.db.table("pms_import_staging_rows").insert({
            "id": str(uuid.uuid4()),
            "import_job_id": job_id,
            "yacht_id": yacht_id,
            "row_number": row_num + 1,
            "raw_json": row,  # Original CSV row
            "normalized_json": None,  # Filled in validation phase
            "validation_errors": [],
            "status": "pending"
        }).execute()

    # 6. Update job status
    await update_job_status(job_id, "validating", {
        "total_rows": len(rows)
    })

    return {
        "status": "parsed",
        "total_rows": len(rows),
        "next_step": "validate"
    }
```

---

### PHASE 3: Validate

**Endpoint:** `POST /api/import/{job_id}/validate`

```python
async def validate_import_rows(job_id, yacht_id):
    # 1. Fetch all staging rows
    staging_rows = await self.db.table("pms_import_staging_rows").select("*").eq(
        "import_job_id", job_id
    ).eq("yacht_id", yacht_id).execute()

    valid_count = 0
    invalid_count = 0
    validation_errors = []

    # 2. Validate each row
    for staging_row in staging_rows.data:
        row = staging_row["raw_json"]
        errors = []

        # G1.3: Input validation
        errors.extend(validate_required_fields(row, scope))
        errors.extend(validate_data_types(row, scope))
        errors.extend(validate_ranges(row, scope))
        errors.extend(validate_enums(row, scope))

        # G1.7: Foreign key validation (CRITICAL)
        fk_errors = await validate_foreign_keys(row, yacht_id, scope)
        errors.extend(fk_errors)

        # G1.2: Duplicate check (within import)
        dup_errors = check_duplicates_within_import(row, staging_rows.data)
        errors.extend(dup_errors)

        # G1.2: Duplicate check (against existing data)
        existing_dup = await check_duplicate_in_database(row, yacht_id, scope)
        if existing_dup:
            errors.append({
                "type": "duplicate",
                "message": f"Duplicate found: {existing_dup['id']}",
                "severity": "warning"  # May be intentional (skip row)
            })

        # Update staging row
        if errors:
            invalid_count += 1
            await self.db.table("pms_import_staging_rows").update({
                "validation_errors": errors,
                "status": "invalid"
            }).eq("id", staging_row["id"]).execute()

            validation_errors.append({
                "row_number": staging_row["row_number"],
                "errors": errors
            })
        else:
            valid_count += 1
            # Normalize row for import
            normalized = normalize_row_for_import(row, scope, yacht_id)
            await self.db.table("pms_import_staging_rows").update({
                "normalized_json": normalized,
                "status": "valid"
            }).eq("id", staging_row["id"]).execute()

    # 3. Check validation thresholds
    invalid_percent = (invalid_count / len(staging_rows.data)) * 100

    if invalid_percent > 20:
        # Too many errors - fail validation
        await update_job_status(job_id, "validation_failed", {
            "valid_rows": valid_count,
            "invalid_rows": invalid_count,
            "invalid_percent": invalid_percent
        })

        return {
            "status": "validation_failed",
            "message": f"{invalid_percent:.1f}% of rows invalid (threshold: 20%)",
            "errors": validation_errors
        }

    # 4. Validation passed
    await update_job_status(job_id, "ready", {
        "valid_rows": valid_count,
        "invalid_rows": invalid_count
    })

    return {
        "status": "ready",
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "errors": validation_errors,
        "next_step": "commit"
    }
```

---

### PHASE 4: Dry-Run Preview

**Endpoint:** `GET /api/import/{job_id}/preview`

```python
async def preview_import(job_id, yacht_id):
    # Show user what WILL be created (before committing)

    valid_rows = await self.db.table("pms_import_staging_rows").select(
        "normalized_json"
    ).eq("import_job_id", job_id).eq(
        "status", "valid"
    ).limit(10).execute()  # First 10 rows

    return {
        "status": "preview",
        "sample_rows": [r["normalized_json"] for r in valid_rows.data],
        "total_valid": await count_valid_rows(job_id),
        "what_will_happen": {
            "new_entities_created": await count_valid_rows(job_id),
            "existing_entities_skipped": await count_duplicates(job_id),
            "placeholders_created": await count_missing_references(job_id)
        },
        "next_step": "User must call commit with confirm=true"
    }
```

---

### PHASE 5: Commit (Explicit Confirmation Required)

**Endpoint:** `POST /api/import/{job_id}/commit`

```python
async def commit_import(job_id, yacht_id, params):
    # 1. Require explicit confirmation
    if not params.get("confirm"):
        raise ValidationError("Must confirm import with confirm=true")

    # 2. Fetch job
    job = await fetch_import_job(job_id, yacht_id)

    # 3. Validate job is in 'ready' state
    if job["status"] != "ready":
        raise InvalidState(f"Job must be in 'ready' state (current: {job['status']})")

    # 4. Check signature requirement (G0.8)
    if job["valid_rows"] > SIGNATURE_THRESHOLD_ROWS:
        if not params.get("signature_data"):
            raise SignatureRequired(f"Signature required for {job['valid_rows']} rows")

    # 5. Fetch valid staging rows
    valid_rows = await self.db.table("pms_import_staging_rows").select(
        "normalized_json"
    ).eq("import_job_id", job_id).eq("status", "valid").execute()

    # 6. Process in batches (G0.4)
    BATCH_SIZE = 100
    batches = [
        valid_rows.data[i:i + BATCH_SIZE]
        for i in range(0, len(valid_rows.data), BATCH_SIZE)
    ]

    imported_count = 0
    target_table = get_target_table(job["scope"])

    for batch_index, batch in enumerate(batches):
        try:
            # BEGIN transaction for this batch
            async with self.db.transaction():
                for staging_row in batch:
                    row = staging_row["normalized_json"]

                    # Force yacht_id (G0.1 - CRITICAL)
                    row["yacht_id"] = yacht_id

                    # Force accountability fields (G0.6)
                    row["created_by"] = job["created_by"]
                    row["created_by_name"] = job["created_by_name"]
                    row["created_by_role"] = job["created_by_role"]
                    row["import_job_id"] = job_id  # Traceability

                    # Insert row
                    await self.db.table(target_table).insert(row).execute()

                    imported_count += 1

            # COMMIT transaction (implicit on success)

            # Update job progress
            await self.db.table("pms_import_jobs").update({
                "batches_completed": batch_index + 1,
                "imported_rows": imported_count
            }).eq("id", job_id).execute()

        except Exception as e:
            # ROLLBACK transaction (automatic)
            logger.error(f"Import batch {batch_index} failed: {e}")

            # Mark job as failed
            await self.db.table("pms_import_jobs").update({
                "status": "failed",
                "error_batch": batch_index,
                "error_message": str(e),
                "imported_rows": imported_count  # Partial success count
            }).eq("id", job_id).execute()

            raise  # Re-raise to return error to user

    # 7. Mark job as complete
    await self.db.table("pms_import_jobs").update({
        "status": "completed",
        "imported_rows": imported_count,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", job_id).execute()

    # 8. Create final audit log
    await self.db.table("pms_audit_log").insert({
        "id": str(uuid.uuid4()),
        "yacht_id": yacht_id,
        "action": "import_data_commit",
        "entity_type": "import_job",
        "entity_id": job_id,
        "user_id": job["created_by"],
        "user_name": job["created_by_name"],
        "user_role": job["created_by_role"],
        "new_values": {
            "scope": job["scope"],
            "imported_rows": imported_count
        },
        "changes_summary": (
            f"Successfully imported {imported_count} {job['scope']} rows"
        ),
        "risk_level": "high",
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    return {
        "status": "completed",
        "imported_rows": imported_count,
        "job_id": job_id
    }
```

---

## DATA STRUCTURES TO ADD

### Table: pms_import_jobs

```sql
CREATE TABLE IF NOT EXISTS public.pms_import_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Import metadata
    scope TEXT NOT NULL CHECK (scope IN (
        'parts', 'shopping_list', 'equipment',
        'pm_schedules', 'work_orders'
    )),
    file_id TEXT NOT NULL,  -- Reference to storage
    file_name TEXT NOT NULL,
    file_format TEXT NOT NULL CHECK (file_format IN ('csv', 'xlsx', 'json')),

    -- Mapping
    mapping_config JSONB NOT NULL,  -- Column mappings
    mapping_config_id UUID,  -- Optional saved mapping

    -- Idempotency
    idempotency_key TEXT NOT NULL,

    -- Counts
    total_rows INTEGER NOT NULL DEFAULT 0,
    valid_rows INTEGER NOT NULL DEFAULT 0,
    invalid_rows INTEGER NOT NULL DEFAULT 0,
    imported_rows INTEGER NOT NULL DEFAULT 0,
    skipped_rows INTEGER NOT NULL DEFAULT 0,

    -- Batch tracking
    batches_completed INTEGER NOT NULL DEFAULT 0,
    error_batch INTEGER,  -- Which batch failed
    error_message TEXT,

    -- Status
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'validating', 'validation_failed',
        'ready', 'processing', 'completed', 'failed', 'cancelled'
    )) DEFAULT 'pending',

    -- Accountability
    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_by_name TEXT NOT NULL,
    created_by_role TEXT NOT NULL,

    -- Signature (for large imports)
    signature_data JSONB,
    signature_timestamp TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_import_jobs_yacht ON public.pms_import_jobs(yacht_id);
CREATE INDEX idx_import_jobs_idempotency ON public.pms_import_jobs(yacht_id, idempotency_key);
CREATE INDEX idx_import_jobs_status ON public.pms_import_jobs(status);
CREATE INDEX idx_import_jobs_created ON public.pms_import_jobs(created_at DESC);

-- RLS
ALTER TABLE public.pms_import_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own yacht imports" ON public.pms_import_jobs
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "HOD can create imports" ON public.pms_import_jobs
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND auth.uid() IN (
            SELECT id FROM public.user_profiles
            WHERE role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
        )
    );
```

---

### Table: pms_import_staging_rows

```sql
CREATE TABLE IF NOT EXISTS public.pms_import_staging_rows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    import_job_id UUID NOT NULL REFERENCES public.pms_import_jobs(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Row tracking
    row_number INTEGER NOT NULL,  -- Original row number in file

    -- Data
    raw_json JSONB NOT NULL,  -- Original parsed row
    normalized_json JSONB,  -- After mapping & normalization (ready to insert)

    -- Validation
    validation_errors JSONB DEFAULT '[]'::jsonb,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'valid', 'invalid', 'skipped', 'imported'
    )) DEFAULT 'pending',

    -- Optional: Suggested matches (for fuzzy matching)
    suggested_match_ids UUID[],

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    imported_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_staging_rows_job ON public.pms_import_staging_rows(import_job_id);
CREATE INDEX idx_staging_rows_status ON public.pms_import_staging_rows(import_job_id, status);

-- RLS
ALTER TABLE public.pms_import_staging_rows ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own yacht staging rows" ON public.pms_import_staging_rows
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

---

### Table: pms_mapping_configs (Optional - For Reusable Mappings)

```sql
CREATE TABLE IF NOT EXISTS public.pms_mapping_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    name TEXT NOT NULL,  -- "Parts from Supplier X"
    scope TEXT NOT NULL CHECK (scope IN (
        'parts', 'shopping_list', 'equipment',
        'pm_schedules', 'work_orders'
    )),

    mapping_config JSONB NOT NULL,  -- Same structure as in import_jobs

    created_by UUID NOT NULL REFERENCES auth.users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_mapping_configs_yacht ON public.pms_mapping_configs(yacht_id);
CREATE INDEX idx_mapping_configs_scope ON public.pms_mapping_configs(yacht_id, scope);

-- RLS
ALTER TABLE public.pms_mapping_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own yacht mappings" ON public.pms_mapping_configs
    FOR ALL TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

---

## "DON'T WRITE THIS HANDLER UNTIL THESE ARE DEFINED"

### 1. Natural Keys for Each Import Scope ✅ REQUIRED

**Define unique identifiers to detect duplicates:**

```python
NATURAL_KEYS = {
    'parts': ['manufacturer_part_number', 'manufacturer'],
    'equipment': ['equipment_number', 'location'],  # Or just equipment_number if globally unique
    'shopping_list': ['part_id', 'requested_by', 'created_at'],  # Likely no natural key
    'pm_schedules': ['equipment_id', 'maintenance_type'],
    'work_orders': ['work_order_number']  # If using external WO numbers
}

# During validation:
def check_duplicate_in_database(row, yacht_id, scope):
    natural_key_fields = NATURAL_KEYS[scope]
    query = self.db.table(get_target_table(scope)).select("id")

    for field in natural_key_fields:
        query = query.eq(field, row[field])

    query = query.eq("yacht_id", yacht_id)

    result = await query.single().execute()
    return result.data  # Returns existing entity if found
```

**DECISION REQUIRED:** Approve natural keys for each scope.

---

### 2. Unit Normalization List ✅ REQUIRED

**Define canonical units and conversion rules:**

```python
UNIT_NORMALIZATION = {
    'length': {
        'canonical': 'meters',
        'conversions': {
            'meters': 1.0,
            'm': 1.0,
            'feet': 0.3048,
            'ft': 0.3048,
            'inches': 0.0254,
            'in': 0.0254
        }
    },
    'weight': {
        'canonical': 'kilograms',
        'conversions': {
            'kilograms': 1.0,
            'kg': 1.0,
            'pounds': 0.453592,
            'lbs': 0.453592,
            'ounces': 0.0283495
        }
    },
    'volume': {
        'canonical': 'liters',
        'conversions': {
            'liters': 1.0,
            'L': 1.0,
            'gallons': 3.78541,
            'gal': 3.78541,
            'quarts': 0.946353
        }
    }
}

def normalize_unit(value, unit, unit_type):
    """Convert value to canonical unit"""
    if unit_type not in UNIT_NORMALIZATION:
        raise ValueError(f"Unknown unit type: {unit_type}")

    conversions = UNIT_NORMALIZATION[unit_type]['conversions']
    if unit not in conversions:
        raise ValueError(f"Unknown unit '{unit}' for type '{unit_type}'")

    return value * conversions[unit]
```

**DECISION REQUIRED:** Approve unit list and conversions.

---

### 3. Ownership Rules ✅ REQUIRED

**Who becomes the owner of imported entities?**

```python
OWNERSHIP_RULES = {
    'parts': 'importing_user',  # User who imported becomes owner
    'equipment': 'importing_user',
    'shopping_list': 'importing_user',  # User who imported = requester
    'pm_schedules': 'system',  # No individual owner
    'work_orders': 'importing_user'  # Or: 'assigned_to' from CSV
}

def set_ownership_fields(row, scope, user_id, user_name, user_role):
    rule = OWNERSHIP_RULES[scope]

    if rule == 'importing_user':
        row['created_by'] = user_id
        row['created_by_name'] = user_name
        row['created_by_role'] = user_role
    elif rule == 'system':
        row['created_by'] = None  # Or system user ID
    elif rule == 'assigned_to':
        # Use assigned_to from CSV, but validate it exists
        if not row.get('assigned_to'):
            row['assigned_to'] = user_id  # Fallback

    return row
```

**DECISION REQUIRED:** Approve ownership rules.

---

### 4. Missing Reference Handling ✅ REQUIRED

**What happens when imported row references non-existent entity?**

```python
MISSING_REFERENCE_STRATEGIES = {
    'reject': {
        'description': 'Fail row validation',
        'action': lambda row, field, value: raise_validation_error(
            f"{field} not found: {value}"
        )
    },
    'placeholder': {
        'description': 'Create placeholder entity with flag',
        'action': lambda row, field, value: create_placeholder_entity(
            field, value, imported_placeholder=True
        )
    },
    'fuzzy_match': {
        'description': 'Suggest similar entities, require user confirmation',
        'action': lambda row, field, value: suggest_fuzzy_matches(field, value)
    }
}

async def handle_missing_reference(row, field, value, strategy):
    if strategy == 'reject':
        return {'valid': False, 'error': f"{field} not found: {value}"}

    elif strategy == 'placeholder':
        # Create placeholder
        placeholder_id = await create_placeholder_part({
            'name': value,
            'yacht_id': row['yacht_id'],
            'imported_placeholder': True,
            'created_by': row['created_by']
        })
        row[field] = placeholder_id
        return {'valid': True, 'placeholder_created': True}

    elif strategy == 'fuzzy_match':
        # Find similar entities
        matches = await fuzzy_search_parts(value, row['yacht_id'])
        return {
            'valid': False,
            'suggested_matches': matches,
            'requires_user_decision': True
        }
```

**DECISION REQUIRED:** Choose default strategy per scope.

---

### 5. Schema Validation Rules ✅ REQUIRED

**Explicit validation for each scope:**

```python
VALIDATION_RULES = {
    'parts': {
        'required': ['name', 'manufacturer_part_number', 'manufacturer'],
        'optional': ['description', 'unit_cost_usd', 'reorder_point', 'location'],
        'data_types': {
            'name': 'string',
            'manufacturer_part_number': 'string',
            'unit_cost_usd': 'number',
            'current_quantity_onboard': 'integer',
            'reorder_point': 'integer'
        },
        'ranges': {
            'unit_cost_usd': {'min': 0, 'max': 1000000},
            'current_quantity_onboard': {'min': 0},
            'reorder_point': {'min': 0}
        },
        'enums': {
            'criticality': ['low', 'medium', 'high', 'critical']
        },
        'max_lengths': {
            'name': 500,
            'description': 5000,
            'manufacturer_part_number': 200
        }
    },
    # ... define for each scope
}
```

**DECISION REQUIRED:** Complete validation rules for all 5 scopes.

---

## FINAL DECISION CHECKLIST

**DO NOT IMPLEMENT import_data UNTIL ALL ITEMS ARE ✅:**

- [ ] Natural keys approved for all 5 scopes
- [ ] Unit normalization list approved
- [ ] Ownership rules approved
- [ ] Missing reference strategy chosen (default: reject for V1)
- [ ] Schema validation rules defined for all 5 scopes
- [ ] Database tables created (pms_import_jobs, pms_import_staging_rows)
- [ ] Idempotency key generation approved
- [ ] Batch size chosen (default: 100, configurable?)
- [ ] Signature threshold chosen (default: 100 rows)
- [ ] Error threshold chosen (default: 20% invalid = fail)
- [ ] "Undo import" compensating action designed
- [ ] File upload size limit set (e.g., 10MB, 10,000 rows)

---

## APPROVED BY:

**Product Owner:** ___________________  Date: _______

**Engineering Lead:** ___________________  Date: _______

**Security Review:** ___________________  Date: _______

---

**STATUS:** 🔴 **NOT APPROVED - DO NOT IMPLEMENT**

**Last Updated:** 2026-01-12
**Version:** 1.0 - Pre-Audit
