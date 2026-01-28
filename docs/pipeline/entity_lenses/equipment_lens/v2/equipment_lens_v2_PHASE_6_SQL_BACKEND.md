# Equipment Lens v2 - PHASE 6: SQL BACKEND

**Goal**: Document → Tests → Code → Verify — backend defines actions, signatures, and RLS; no UI authority.

**Lens**: Equipment

**Date**: 2026-01-27

---

## PURPOSE

Phase 6 defines exact SQL patterns for each action:
- Handler SQL with parameter binding
- Audit log inserts
- Notification triggers
- Transaction boundaries

---

## SQL CONVENTIONS

### Parameter Binding

All SQL uses named parameters (`:param_name`) that map to request payload:

```sql
-- :equipment_id from context
-- :status from payload
-- :attention_reason from payload (optional)
```

### Yacht Isolation

All queries include yacht isolation:

```sql
WHERE yacht_id = public.get_user_yacht_id()
```

### Audit Invariant

Every mutation ends with audit log insert:

```sql
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action,
    actor_user_id, actor_role,
    old_values, new_values, signature,
    payload_snapshot, created_at
) VALUES (...);
```

**Signature Rule**:
- Non-signed actions: `signature = '{}'::jsonb`
- Signed actions: `signature = :signature_payload::jsonb`

---

## ACTION 1: `update_equipment_status`

### Handler SQL

```sql
-- Step 1: Get current state for audit
SELECT id, status, attention_flag, attention_reason
INTO _old_record
FROM pms_equipment
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL;

-- Validation: Check terminal state
IF _old_record.status = 'decommissioned' THEN
    RAISE EXCEPTION 'invalid_state_transition: Cannot change status from decommissioned';
END IF;

-- Validation: Block direct decommission (must use decommission action)
IF :status = 'decommissioned' THEN
    RAISE EXCEPTION 'invalid_action: Use decommission_equipment action for decommissioning';
END IF;

-- Step 2: Update equipment
UPDATE pms_equipment
SET
    status = :status,
    attention_flag = CASE
        WHEN :status IN ('failed', 'degraded') THEN true
        WHEN :status = 'operational' AND :clear_attention = true THEN false
        ELSE attention_flag
    END,
    attention_reason = CASE
        WHEN :status IN ('failed', 'degraded') THEN COALESCE(:attention_reason, 'Status changed to ' || :status)
        WHEN :status = 'operational' AND :clear_attention = true THEN NULL
        ELSE attention_reason
    END,
    attention_updated_at = CASE
        WHEN :status IN ('failed', 'degraded', 'operational') THEN NOW()
        ELSE attention_updated_at
    END,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL
RETURNING id, status, attention_flag, attention_reason;

-- Step 3: Insert audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action,
    actor_user_id, actor_role,
    old_values, new_values, signature,
    payload_snapshot, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    'update_equipment_status',
    auth.uid(),
    public.get_user_role(),
    jsonb_build_object(
        'status', _old_record.status,
        'attention_flag', _old_record.attention_flag,
        'attention_reason', _old_record.attention_reason
    ),
    jsonb_build_object(
        'status', :status,
        'attention_flag', _new_attention_flag,
        'attention_reason', :attention_reason
    ),
    '{}'::jsonb,  -- Non-signed action
    jsonb_build_object(
        'source', 'equipment_lens',
        'session_id', :session_id
    ),
    NOW()
);

-- Step 4: Trigger notification if critical failure
IF :status = 'failed' THEN
    SELECT criticality INTO _criticality
    FROM pms_equipment WHERE id = :equipment_id;

    IF _criticality IN ('high', 'critical') THEN
        -- Insert notification (see notification SQL below)
        PERFORM notify_equipment_failure(:equipment_id, :status, _criticality);
    END IF;
END IF;
```

### Python Handler Skeleton

```python
async def update_equipment_status(
    equipment_id: UUID,
    status: str,
    attention_reason: Optional[str] = None,
    clear_attention: bool = False,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> EquipmentStatusResponse:
    # Validate status enum
    if status not in ['operational', 'degraded', 'failed', 'maintenance']:
        raise HTTPException(400, "Invalid status value")

    # Get current state
    old_equipment = await db.execute(
        select(Equipment)
        .where(Equipment.id == equipment_id)
        .where(Equipment.yacht_id == user.yacht_id)
        .where(Equipment.deleted_at.is_(None))
    )
    equipment = old_equipment.scalar_one_or_none()

    if not equipment:
        raise HTTPException(404, "Equipment not found")

    if equipment.status == 'decommissioned':
        raise HTTPException(400, "Cannot change status from 'decommissioned'. Terminal state.")

    # Update
    old_values = {
        "status": equipment.status,
        "attention_flag": equipment.attention_flag,
        "attention_reason": equipment.attention_reason
    }

    equipment.status = status
    if status in ('failed', 'degraded'):
        equipment.attention_flag = True
        equipment.attention_reason = attention_reason or f"Status changed to {status}"
        equipment.attention_updated_at = datetime.utcnow()
    elif status == 'operational' and clear_attention:
        equipment.attention_flag = False
        equipment.attention_reason = None
        equipment.attention_updated_at = datetime.utcnow()

    equipment.updated_at = datetime.utcnow()
    equipment.updated_by = user.id

    # Audit log
    audit = AuditLog(
        yacht_id=user.yacht_id,
        entity_type='equipment',
        entity_id=equipment_id,
        action='update_equipment_status',
        actor_user_id=user.id,
        actor_role=user.role,
        old_values=old_values,
        new_values={
            "status": status,
            "attention_flag": equipment.attention_flag,
            "attention_reason": equipment.attention_reason
        },
        signature={}  # Non-signed
    )
    db.add(audit)

    # Notification trigger
    if status == 'failed' and equipment.criticality in ('high', 'critical'):
        await trigger_equipment_failure_notification(db, equipment, user)

    await db.commit()

    return EquipmentStatusResponse(
        equipment_id=equipment_id,
        old_status=old_values["status"],
        new_status=status,
        attention_flag=equipment.attention_flag,
        audit_id=audit.id
    )
```

---

## ACTION 2: `add_equipment_note`

### Handler SQL

```sql
-- Step 1: Verify equipment exists
SELECT id, name INTO _equipment
FROM pms_equipment
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL;

IF NOT FOUND THEN
    RAISE EXCEPTION 'equipment_not_found';
END IF;

-- Step 2: Insert note
INSERT INTO pms_notes (
    id, yacht_id, equipment_id,
    text, note_type, requires_ack,
    attachments, metadata,
    created_by, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    :equipment_id,
    :text,
    COALESCE(:note_type, 'observation'),
    COALESCE(:requires_ack, false),
    COALESCE(:attachments, '[]'::jsonb),
    jsonb_build_object('source', 'equipment_lens', 'session_id', :session_id),
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id;

-- Step 3: Insert audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action,
    actor_user_id, actor_role,
    old_values, new_values, signature, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    'add_equipment_note',
    auth.uid(),
    public.get_user_role(),
    NULL,
    jsonb_build_object(
        'note_id', _new_note_id,
        'text_preview', LEFT(:text, 100),
        'note_type', COALESCE(:note_type, 'observation'),
        'requires_ack', COALESCE(:requires_ack, false)
    ),
    '{}'::jsonb,
    NOW()
);

-- Step 4: Trigger notification if requires_ack
IF :requires_ack = true THEN
    INSERT INTO pms_notifications (
        id, yacht_id, user_id,
        topic, source, source_id,
        title, body, level,
        cta_action_id, cta_payload,
        status, send_after
    )
    SELECT
        gen_random_uuid(),
        public.get_user_yacht_id(),
        aup.id,
        'equipment_note_requires_ack',
        'equipment',
        :equipment_id,
        'Equipment Note Requires Review',
        public.get_user_role() || ' added note to ' || _equipment.name || ': "' || LEFT(:text, 50) || '..."',
        'info',
        'view_equipment_note',
        jsonb_build_object('equipment_id', :equipment_id, 'note_id', _new_note_id),
        'pending',
        NOW()
    FROM auth_users_profiles aup
    WHERE aup.yacht_id = public.get_user_yacht_id()
      AND aup.role = 'chief_engineer'
      AND aup.is_active = true;
END IF;
```

---

## ACTION 3: `attach_file_to_equipment`

### Handler SQL

```sql
-- Step 1: Verify equipment exists
SELECT id FROM pms_equipment
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL;

IF NOT FOUND THEN
    RAISE EXCEPTION 'equipment_not_found';
END IF;

-- Step 2: Generate storage path
-- Path: {yacht_id}/equipment/{equipment_id}/{uuid}.{extension}
_storage_path := public.get_user_yacht_id()::text || '/equipment/' || :equipment_id::text || '/' || :generated_filename;

-- Step 3: Insert attachment metadata
INSERT INTO pms_attachments (
    id, yacht_id, entity_type, entity_id,
    filename, original_filename, mime_type, file_size,
    storage_path, description, tags,
    metadata, uploaded_by, uploaded_at, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    :generated_filename,
    :original_filename,
    :mime_type,
    :file_size,
    _storage_path,
    :description,
    :tags,
    jsonb_build_object('source', 'equipment_lens', 'session_id', :session_id),
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id, storage_path;

-- Step 4: Insert audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action,
    actor_user_id, actor_role,
    old_values, new_values, signature, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    'attach_file_to_equipment',
    auth.uid(),
    public.get_user_role(),
    NULL,
    jsonb_build_object(
        'attachment_id', _new_attachment_id,
        'filename', :original_filename,
        'mime_type', :mime_type,
        'storage_path', _storage_path
    ),
    '{}'::jsonb,
    NOW()
);
```

### File Upload Flow

```python
async def attach_file_to_equipment(
    equipment_id: UUID,
    file: UploadFile,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageClient = Depends(get_storage)
) -> AttachmentResponse:
    # Validate file size
    MAX_SIZE = 25 * 1024 * 1024  # 25MB
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "File exceeds maximum size of 25MB")

    # Validate MIME type
    ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'application/pdf']
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type {file.content_type} not allowed")

    # Verify equipment exists
    equipment = await get_equipment_or_404(db, equipment_id, user.yacht_id)

    # Generate filename
    ext = Path(file.filename).suffix
    generated_filename = f"{uuid4()}{ext}"
    storage_path = f"{user.yacht_id}/equipment/{equipment_id}/{generated_filename}"

    # Upload to storage bucket
    await storage.upload(
        bucket="documents",
        path=storage_path,
        content=content,
        content_type=file.content_type
    )

    # Insert attachment record
    attachment = Attachment(
        yacht_id=user.yacht_id,
        entity_type='equipment',
        entity_id=equipment_id,
        filename=generated_filename,
        original_filename=file.filename,
        mime_type=file.content_type,
        file_size=len(content),
        storage_path=storage_path,
        description=description,
        tags=tags,
        uploaded_by=user.id
    )
    db.add(attachment)

    # Audit log
    audit = AuditLog(...)
    db.add(audit)

    await db.commit()

    return AttachmentResponse(
        attachment_id=attachment.id,
        storage_path=storage_path
    )
```

---

## ACTION 4: `create_work_order_for_equipment`

### Handler SQL

```sql
-- Step 1: Verify equipment exists
SELECT id, name, criticality INTO _equipment
FROM pms_equipment
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL;

IF NOT FOUND THEN
    RAISE EXCEPTION 'equipment_not_found';
END IF;

-- Step 2: Generate WO number
SELECT COALESCE(MAX(CAST(SUBSTRING(wo_number FROM 'WO-[0-9]{4}-([0-9]+)') AS INTEGER)), 0) + 1
INTO _next_wo_number
FROM pms_work_orders
WHERE yacht_id = public.get_user_yacht_id();

_wo_number := 'WO-' || EXTRACT(YEAR FROM NOW())::text || '-' || LPAD(_next_wo_number::text, 4, '0');

-- Step 3: Insert work order
INSERT INTO pms_work_orders (
    id, yacht_id, wo_number,
    equipment_id, title, description,
    type, priority, status,
    assigned_to, due_date,
    created_by, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    _wo_number,
    :equipment_id,
    :title,
    :description,
    :type,
    :priority,
    'draft',
    :assigned_to,
    :due_date,
    auth.uid(),
    NOW(),
    NOW()
)
RETURNING id, wo_number;

-- Step 4: If corrective/breakdown, create fault
IF :type IN ('corrective', 'breakdown') THEN
    -- Generate fault code
    SELECT COALESCE(MAX(CAST(SUBSTRING(fault_code FROM 'FLT-[0-9]{4}-([0-9]+)') AS INTEGER)), 0) + 1
    INTO _next_fault_number
    FROM pms_faults
    WHERE yacht_id = public.get_user_yacht_id();

    _fault_code := 'FLT-' || EXTRACT(YEAR FROM NOW())::text || '-' || LPAD(_next_fault_number::text, 4, '0');

    INSERT INTO pms_faults (
        id, yacht_id, fault_code,
        equipment_id, work_order_id,
        title, severity, status,
        detected_at, detected_by,
        created_at
    ) VALUES (
        gen_random_uuid(),
        public.get_user_yacht_id(),
        _fault_code,
        :equipment_id,
        _new_wo_id,
        :title,
        COALESCE(:fault_severity, 'medium'),
        'open',
        NOW(),
        auth.uid(),
        NOW()
    )
    RETURNING id, fault_code;
END IF;

-- Step 5: Insert audit log (equipment entity)
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action,
    actor_user_id, actor_role,
    old_values, new_values, signature, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    'create_work_order_for_equipment',
    auth.uid(),
    public.get_user_role(),
    NULL,
    jsonb_build_object(
        'work_order_id', _new_wo_id,
        'wo_number', _wo_number,
        'type', :type,
        'priority', :priority,
        'fault_id', _new_fault_id,
        'fault_code', _fault_code
    ),
    '{}'::jsonb,
    NOW()
);
```

---

## ACTION 7: `decommission_equipment` (SIGNED)

### Handler SQL

```sql
-- Step 1: Get current state
SELECT id, status, name INTO _equipment
FROM pms_equipment
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
  AND deleted_at IS NULL;

IF NOT FOUND THEN
    RAISE EXCEPTION 'equipment_not_found';
END IF;

-- Step 2: Validate not already decommissioned
IF _equipment.status = 'decommissioned' THEN
    RAISE EXCEPTION 'already_decommissioned: Equipment is already decommissioned';
END IF;

-- Step 3: Validate signature present
IF :signature IS NULL OR :signature = '{}'::jsonb THEN
    RAISE EXCEPTION 'signature_required: Decommission requires signature';
END IF;

-- Step 4: Validate signature structure
IF NOT (
    :signature ? 'user_id' AND
    :signature ? 'role_at_signing' AND
    :signature ? 'signature_type' AND
    :signature ? 'signed_at' AND
    :signature ? 'signature_hash'
) THEN
    RAISE EXCEPTION 'invalid_signature: Signature payload is invalid';
END IF;

-- Step 5: Update equipment to decommissioned
UPDATE pms_equipment
SET
    status = 'decommissioned',
    deleted_at = NOW(),
    deleted_by = auth.uid(),
    deletion_reason = :reason,
    attention_flag = false,
    attention_reason = NULL,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = :equipment_id
  AND yacht_id = public.get_user_yacht_id()
RETURNING id;

-- Step 6: Insert SIGNED audit log
INSERT INTO pms_audit_log (
    id, yacht_id, entity_type, entity_id, action,
    actor_user_id, actor_role,
    old_values, new_values,
    signature,  -- FULL SIGNATURE JSON, NOT EMPTY
    payload_snapshot, created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    'equipment',
    :equipment_id,
    'decommission_equipment',
    auth.uid(),
    public.get_user_role(),
    jsonb_build_object('status', _equipment.status),
    jsonb_build_object(
        'status', 'decommissioned',
        'reason', :reason,
        'replacement_equipment_id', :replacement_equipment_id
    ),
    :signature::jsonb,  -- FULL SIGNATURE PAYLOAD
    jsonb_build_object(
        'equipment_name', _equipment.name,
        'source', 'equipment_lens'
    ),
    NOW()
);

-- Step 7: Notify stakeholders
INSERT INTO pms_notifications (
    id, yacht_id, user_id,
    topic, source, source_id,
    title, body, level,
    cta_action_id, status, send_after
)
SELECT
    gen_random_uuid(),
    public.get_user_yacht_id(),
    aup.id,
    'equipment_decommissioned',
    'equipment',
    :equipment_id,
    'Equipment Decommissioned: ' || _equipment.name,
    _equipment.name || ' has been decommissioned by ' || public.get_user_role() || '. Reason: ' || :reason,
    'info',
    'view_audit_log',
    'pending',
    NOW()
FROM auth_users_profiles aup
WHERE aup.yacht_id = public.get_user_yacht_id()
  AND aup.role IN ('captain', 'manager', 'chief_engineer')
  AND aup.id != auth.uid()
  AND aup.is_active = true;
```

---

## NOTIFICATION HELPER FUNCTION

```sql
CREATE OR REPLACE FUNCTION notify_equipment_failure(
    p_equipment_id UUID,
    p_status TEXT,
    p_criticality TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    _equipment_name TEXT;
    _notification_level TEXT;
    _topic TEXT;
BEGIN
    SELECT name INTO _equipment_name
    FROM pms_equipment WHERE id = p_equipment_id;

    -- Determine notification level
    _notification_level := CASE
        WHEN p_criticality = 'critical' THEN 'critical'
        ELSE 'warning'
    END;

    _topic := CASE
        WHEN p_criticality = 'critical' THEN 'equipment_critical_failure'
        ELSE 'equipment_failure'
    END;

    -- Notify chief_engineer always
    INSERT INTO pms_notifications (
        id, yacht_id, user_id,
        topic, source, source_id,
        title, body, level,
        cta_action_id, cta_payload,
        status, send_after
    )
    SELECT
        gen_random_uuid(),
        public.get_user_yacht_id(),
        aup.id,
        _topic,
        'equipment',
        p_equipment_id,
        CASE WHEN p_criticality = 'critical'
            THEN 'CRITICAL: ' || _equipment_name || ' Failed'
            ELSE _equipment_name || ' Status: ' || p_status
        END,
        _equipment_name || ' marked as ' || UPPER(p_status),
        _notification_level,
        'focus_equipment',
        jsonb_build_object('equipment_id', p_equipment_id),
        'pending',
        NOW()
    FROM auth_users_profiles aup
    WHERE aup.yacht_id = public.get_user_yacht_id()
      AND aup.role IN ('chief_engineer', 'captain')
      AND aup.is_active = true;
END;
$$;
```

---

## TRANSACTION BOUNDARIES

All Equipment Lens actions are **single-transaction**:

```python
async with db.begin():
    # 1. Validate inputs
    # 2. Verify equipment exists
    # 3. Perform mutation
    # 4. Insert audit log
    # 5. Insert notifications (if triggered)
    # Commit on success, rollback on any error
```

**Atomicity Guarantee**: Either all operations succeed (equipment update + audit + notification) or none do.

---

## ERROR HANDLING

```python
ERROR_MAP = {
    "equipment_not_found": (404, "Equipment not found"),
    "invalid_state_transition": (400, "Cannot change status from 'decommissioned'. Terminal state."),
    "already_decommissioned": (409, "Equipment is already decommissioned"),
    "signature_required": (400, "This action requires a signature"),
    "invalid_signature": (400, "Signature payload is invalid"),
    "invalid_status": (400, "Invalid status value"),
    "file_too_large": (400, "File exceeds maximum size of 25MB"),
    "invalid_file_type": (400, "File type not allowed"),
    "part_already_linked": (409, "Part already linked to this equipment"),
}

# Handler pattern
try:
    result = await execute_action(...)
except Exception as e:
    error_key = extract_error_key(e)
    if error_key in ERROR_MAP:
        status, message = ERROR_MAP[error_key]
        raise HTTPException(status, message)
    else:
        # Unexpected error - log and return 500
        logger.exception("Unexpected error in equipment action")
        raise HTTPException(500, "Internal server error")
```

---

## NEXT PHASE

Proceed to **PHASE 7: RLS MATRIX** to:
- Document all RLS policies
- Map roles to policy enforcement
- Define verification queries

---

**END OF PHASE 6**
