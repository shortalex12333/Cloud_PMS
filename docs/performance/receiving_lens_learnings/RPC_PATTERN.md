# RPC Pattern for Multi-Tenancy - Implementation Guide

**Date**: 2026-01-30
**Impact**: Lens-specific (pattern reusable)
**Use Case**: Fixes INSERT_FAILED errors when TENANT DB cannot verify MASTER JWTs

---

## What is the RPC Pattern?

**Problem**: TENANT Supabase cannot verify MASTER Supabase JWTs, causing `auth.uid()` to return NULL in RLS policies.

**Solution**: Use PostgreSQL RPC functions with `SECURITY DEFINER` to bypass JWT verification and do manual auth checks.

**Analogy**: Like having a trusted bouncer (RPC function) check IDs instead of relying on an electronic scanner (JWT verification) that doesn't work.

---

## When to Use RPC Pattern

### ✅ Use RPC When:

1. **Multi-Tenancy with Separate Supabase Instances**
   - MASTER Supabase for authentication
   - TENANT Supabase for data storage
   - TENANT cannot verify MASTER's JWTs

2. **RLS Policies Depend on `auth.uid()`**
   - Policies check `created_by = auth.uid()`
   - `auth.uid()` returns NULL with MASTER JWT
   - Result: INSERT_FAILED or permission errors

3. **Complex Authorization Logic**
   - Multi-step checks (role + tenant + status)
   - Better to centralize in RPC function
   - Avoids multiple round trips

### ❌ Don't Use RPC When:

1. **Single Supabase Instance**
   - RLS with JWTs works fine
   - No JWT verification issue

2. **Simple Queries**
   - SELECT with RLS is fine
   - Only INSERTs/UPDATEs need RPC

3. **No RLS Policies**
   - Tables don't use RLS
   - Service role can insert directly

---

## How It Works

### Architecture Overview

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   CLIENT    │         │  MASTER DB  │         │  TENANT DB  │
│  (Browser)  │         │ (Auth only) │         │   (Data)    │
└─────────────┘         └─────────────┘         └─────────────┘
       │                       │                       │
       │ 1. Login              │                       │
       ├──────────────────────>│                       │
       │                       │                       │
       │ 2. JWT (MASTER)       │                       │
       │<──────────────────────┤                       │
       │                       │                       │
       │ 3. API Request        │                       │
       │   + MASTER JWT        │                       │
       ├───────────────────────┼──────────────────────>│
       │                       │                       │
       │                       │   ❌ Cannot verify    │
       │                       │      MASTER JWT       │
       │                       │                       │
       │   4. Call RPC         │                       │
       │      (service role)   │                       │
       ├───────────────────────┼──────────────────────>│
       │                       │                       │
       │                       │   ✅ RPC checks       │
       │                       │      auth manually    │
       │                       │      in DB            │
       │                       │                       │
       │   5. Success          │                       │
       │<──────────────────────┼───────────────────────┤
       │                       │                       │
```

### Before: Direct INSERT with User JWT (Fails)

```python
# Handler (receiving_handlers.py)
def create_receiving(user_context, request):
    user_jwt = user_context["jwt"]  # MASTER JWT
    yacht_id = user_context["yacht_id"]

    # Create client with MASTER JWT
    db = get_user_db(user_jwt, yacht_id)

    # Try to INSERT
    result = db.table("pms_receiving").insert({
        "yacht_id": yacht_id,
        "vendor_name": "ABC Corp",
        "created_by": user_context["user_id"],
        ...
    }).execute()  # ❌ FAILS: INSERT_FAILED

    # Why it fails:
    # - TENANT DB cannot verify MASTER JWT
    # - auth.uid() returns NULL
    # - RLS policy: created_by = auth.uid() fails
```

### After: RPC Function with Service Role (Works)

```sql
-- Migration: Create RPC function in TENANT DB
CREATE FUNCTION rpc_insert_receiving(
    p_user_id UUID,
    p_yacht_id UUID,
    p_vendor_name TEXT,
    p_vendor_reference TEXT,
    p_received_date DATE,
    p_notes TEXT
) RETURNS TABLE (
    receiving_id UUID,
    vendor_name TEXT,
    status TEXT
) AS $$
BEGIN
    -- Manual auth check against auth_users_roles
    IF NOT EXISTS (
        SELECT 1 FROM auth_users_roles r
        WHERE r.user_id = p_user_id
          AND r.yacht_id = p_yacht_id
          AND r.is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Permission denied: User not authorized for this yacht';
    END IF;

    -- INSERT with manual values (bypasses RLS)
    INSERT INTO pms_receiving (
        yacht_id,
        vendor_name,
        vendor_reference,
        received_date,
        notes,
        status,
        created_by
    ) VALUES (
        p_yacht_id,
        p_vendor_name,
        p_vendor_reference,
        p_received_date,
        p_notes,
        'draft',
        p_user_id  -- Manual auth, not auth.uid()
    ) RETURNING id, vendor_name, status
    INTO receiving_id, vendor_name, status;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

```python
# Handler (receiving_handlers.py)
def create_receiving(user_context, request):
    user_id = user_context["user_id"]
    yacht_id = user_context["yacht_id"]

    # Use service role (bypasses RLS)
    db = get_service_db(yacht_id)

    # Call RPC function
    result = db.rpc("rpc_insert_receiving", {
        "p_user_id": user_id,
        "p_yacht_id": yacht_id,
        "p_vendor_name": request["vendor_name"],
        "p_vendor_reference": request["vendor_reference"],
        "p_received_date": request["received_date"],
        "p_notes": request.get("notes")
    }).execute()  # ✅ WORKS

    return result.data[0]
```

---

## Implementation Guide

### Step 1: Create RPC Function Migration

**File**: `supabase/migrations/20260130_XXX_rpc_insert_receiving.sql`

```sql
-- RPC function to insert receiving record with manual auth
CREATE OR REPLACE FUNCTION rpc_insert_receiving(
    p_user_id UUID,
    p_yacht_id UUID,
    p_vendor_name TEXT,
    p_vendor_reference TEXT,
    p_received_date DATE,
    p_notes TEXT DEFAULT NULL
) RETURNS TABLE (
    receiving_id UUID,
    vendor_name TEXT,
    vendor_reference TEXT,
    status TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    v_receiving_id UUID;
BEGIN
    -- Step 1: Verify user authorization
    -- Check if user has active role for this yacht
    IF NOT EXISTS (
        SELECT 1
        FROM auth_users_roles r
        WHERE r.user_id = p_user_id
          AND r.yacht_id = p_yacht_id
          AND r.is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Permission denied: User % not authorized for yacht %',
            p_user_id, p_yacht_id;
    END IF;

    -- Step 2: Generate UUID for new record
    v_receiving_id := gen_random_uuid();

    -- Step 3: Insert receiving record
    INSERT INTO pms_receiving (
        id,
        yacht_id,
        vendor_name,
        vendor_reference,
        received_date,
        notes,
        status,
        received_by,
        created_by,
        created_at
    ) VALUES (
        v_receiving_id,
        p_yacht_id,
        p_vendor_name,
        p_vendor_reference,
        p_received_date,
        p_notes,
        'draft',  -- Default status
        p_user_id,
        p_user_id,
        NOW()
    );

    -- Step 4: Return created record
    RETURN QUERY
    SELECT
        r.id AS receiving_id,
        r.vendor_name,
        r.vendor_reference,
        r.status,
        r.created_at
    FROM pms_receiving r
    WHERE r.id = v_receiving_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION rpc_insert_receiving TO service_role;

-- Add comment for documentation
COMMENT ON FUNCTION rpc_insert_receiving IS
'Insert receiving record with manual auth check. Used to bypass JWT verification issues in multi-tenancy setup.';
```

### Step 2: Update Handler to Call RPC

**File**: `apps/api/handlers/receiving_handlers.py`

```python
from handlers.db_client import get_service_db
from utils.audit_logger import write_audit_log_async

def create_receiving(user_context: Dict, request: Dict) -> Dict:
    """
    Create a new receiving record using RPC function.

    Uses service role + RPC instead of user JWT + direct INSERT
    to work around multi-tenancy JWT verification issue.
    """
    user_id = user_context["user_id"]
    yacht_id = user_context["yacht_id"]

    # Validate request
    if not request.get("vendor_name"):
        raise ValueError("vendor_name is required")
    if not request.get("vendor_reference"):
        raise ValueError("vendor_reference is required")
    if not request.get("received_date"):
        raise ValueError("received_date is required")

    # Use service role (RPC does auth internally)
    db = get_service_db(yacht_id)

    try:
        # Call RPC function
        result = db.rpc("rpc_insert_receiving", {
            "p_user_id": user_id,
            "p_yacht_id": yacht_id,
            "p_vendor_name": request["vendor_name"],
            "p_vendor_reference": request["vendor_reference"],
            "p_received_date": request["received_date"],
            "p_notes": request.get("notes")
        }).execute()

        if not result.data:
            raise Exception("RPC function returned no data")

        receiving = result.data[0]
        receiving_id = receiving["receiving_id"]

        # Write audit log (async)
        write_audit_log_async(db, {
            "yacht_id": yacht_id,
            "entity_type": "receiving",
            "action": "create_receiving",
            "entity_id": receiving_id,
            "user_id": user_id
        })

        return {
            "receiving_id": receiving_id,
            "vendor_name": receiving["vendor_name"],
            "status": receiving["status"]
        }

    except Exception as e:
        # Check if permission denied (from RPC)
        if "Permission denied" in str(e):
            raise PermissionError(f"Not authorized to create receiving: {e}")
        raise
```

### Step 3: Test RPC Function

```python
def test_rpc_insert_receiving():
    """Test RPC function with valid user."""
    db = get_service_db("yTEST_YACHT_001")

    result = db.rpc("rpc_insert_receiving", {
        "p_user_id": "89b1262c-ff59-4591-b954-757cdf3d609d",
        "p_yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
        "p_vendor_name": "Test Vendor",
        "p_vendor_reference": "TEST-001",
        "p_received_date": "2026-01-30",
        "p_notes": "Test receiving"
    }).execute()

    assert result.data
    assert result.data[0]["vendor_name"] == "Test Vendor"
    assert result.data[0]["status"] == "draft"

def test_rpc_permission_denied():
    """Test RPC function with unauthorized user."""
    db = get_service_db("yTEST_YACHT_001")

    with pytest.raises(Exception) as exc_info:
        db.rpc("rpc_insert_receiving", {
            "p_user_id": "00000000-0000-0000-0000-000000000000",  # Invalid user
            "p_yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
            "p_vendor_name": "Test Vendor",
            "p_vendor_reference": "TEST-001",
            "p_received_date": "2026-01-30"
        }).execute()

    assert "Permission denied" in str(exc_info.value)
```

---

## Security Considerations

### 1. SECURITY DEFINER

**What it means**: Function runs with permissions of the function creator (service role), not the caller.

**Security implications**:
- ✅ Can bypass RLS policies
- ⚠️ MUST do manual auth checks
- ⚠️ Vulnerable if auth check is wrong

**Best practice**:
```sql
-- ALWAYS check authorization first
IF NOT EXISTS (
    SELECT 1 FROM auth_users_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = TRUE
) THEN
    RAISE EXCEPTION 'Permission denied';
END IF;

-- Then do the operation
INSERT INTO ...
```

### 2. Input Validation

**Validate all inputs** in RPC function:

```sql
-- Check for NULL values
IF p_user_id IS NULL THEN
    RAISE EXCEPTION 'user_id cannot be NULL';
END IF;

IF p_yacht_id IS NULL THEN
    RAISE EXCEPTION 'yacht_id cannot be NULL';
END IF;

-- Check for invalid values
IF LENGTH(p_vendor_name) < 1 THEN
    RAISE EXCEPTION 'vendor_name cannot be empty';
END IF;

-- Check for SQL injection attempts (PostgreSQL handles this automatically with prepared statements)
```

### 3. Rate Limiting

RPC functions can be abused. Consider rate limiting:

```sql
-- Check if user is creating too many records
DECLARE
    v_recent_count INT;
BEGIN
    SELECT COUNT(*) INTO v_recent_count
    FROM pms_receiving
    WHERE created_by = p_user_id
      AND created_at > NOW() - INTERVAL '1 minute';

    IF v_recent_count > 10 THEN
        RAISE EXCEPTION 'Rate limit exceeded: Too many receiving records created';
    END IF;

    -- Continue with INSERT...
END;
```

### 4. Audit Logging

Log all RPC calls for security auditing:

```sql
-- Add audit log entry within RPC
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    entity_type,
    action,
    entity_id,
    created_by,
    created_at
) VALUES (
    gen_random_uuid(),
    p_yacht_id,
    'receiving',
    'create_receiving',
    v_receiving_id,
    p_user_id,
    NOW()
);
```

---

## Pattern Template

Use this template for creating RPC functions in other lenses:

```sql
-- Template: RPC Insert Function
CREATE OR REPLACE FUNCTION rpc_insert_<entity>(
    p_user_id UUID,
    p_yacht_id UUID,
    -- Add entity-specific parameters
    p_field1 TEXT,
    p_field2 INTEGER,
    ...
) RETURNS TABLE (
    <entity>_id UUID,
    -- Add fields to return
    field1 TEXT,
    status TEXT
) AS $$
DECLARE
    v_entity_id UUID;
BEGIN
    -- 1. Authorization Check (REQUIRED)
    IF NOT EXISTS (
        SELECT 1 FROM auth_users_roles r
        WHERE r.user_id = p_user_id
          AND r.yacht_id = p_yacht_id
          AND r.is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Permission denied: User not authorized';
    END IF;

    -- 2. Input Validation (RECOMMENDED)
    IF p_field1 IS NULL OR LENGTH(p_field1) < 1 THEN
        RAISE EXCEPTION 'field1 is required';
    END IF;

    -- 3. Business Logic Validation (OPTIONAL)
    -- e.g., check if related entities exist

    -- 4. Generate ID
    v_entity_id := gen_random_uuid();

    -- 5. INSERT
    INSERT INTO pms_<entity> (
        id,
        yacht_id,
        field1,
        field2,
        created_by,
        created_at
    ) VALUES (
        v_entity_id,
        p_yacht_id,
        p_field1,
        p_field2,
        p_user_id,
        NOW()
    );

    -- 6. Return Result
    RETURN QUERY
    SELECT
        e.id AS <entity>_id,
        e.field1,
        e.status
    FROM pms_<entity> e
    WHERE e.id = v_entity_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permission
GRANT EXECUTE ON FUNCTION rpc_insert_<entity> TO service_role;

-- Add documentation
COMMENT ON FUNCTION rpc_insert_<entity> IS
'Insert <entity> record with manual auth check for multi-tenancy.';
```

---

## FAQ

**Q: Should all INSERT operations use RPC?**
A: No. Only use RPC if you have multi-tenancy JWT issues. If RLS works fine, use direct INSERT.

**Q: Can RPC functions call other RPC functions?**
A: Yes, but be careful of circular dependencies and performance impact.

**Q: How do I test RPC functions locally?**
A: Use `psql` or Supabase Studio's SQL editor to call the function directly.

**Q: Can I use RPC for SELECT queries?**
A: You can, but not recommended. Use RLS for SELECTs (it works fine). RPC is mainly for INSERT/UPDATE/DELETE.

**Q: What about UPDATE and DELETE?**
A: Same pattern applies. Create `rpc_update_<entity>` and `rpc_delete_<entity>` functions.

---

## Next Steps

1. ✅ Identify if your lens has JWT verification issues
2. ✅ Create RPC function using template above
3. ✅ Update handler to call RPC instead of direct INSERT
4. ✅ Test with stress test script
5. ✅ Document RPC function in your lens README

---

**Questions?** See `SYSTEM_OPTIMIZATIONS.md` or contact Receiving Lens worker.
