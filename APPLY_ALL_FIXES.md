# ⚡ Apply All Document Viewing Fixes

## **Found 4 Issues - Need to Apply 4 Migrations**

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| 08 | Missing storage RLS policy | Add policy to storage.objects | ✅ APPLIED |
| 09 | Broken search_document_chunks RLS | Fix table reference | ⏳ APPLY NOW |
| 10 | Missing row_security = off in RPC | Add to get_document_storage_path() | ⏳ APPLY NOW |
| 11 | Missing get_user_auth_info() RPC | Create function | ⏳ APPLY NOW |

---

## **Apply These 3 Migrations**

Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new

---

### **Migration 09: Fix search_document_chunks RLS**

```sql
-- Drop the broken policy
DROP POLICY IF EXISTS "chunks_yacht_isolation" ON public.search_document_chunks;

-- Create corrected policy using auth_users_profiles
CREATE POLICY "chunks_yacht_isolation"
ON public.search_document_chunks
FOR SELECT
TO authenticated, anon
USING (
  yacht_id IN (
    SELECT yacht_id
    FROM public.auth_users_profiles
    WHERE id = auth.uid()
  )
);
```

---

### **Migration 10: Add row_security = off to RPC**

```sql
-- Recreate function with row_security = off
CREATE OR REPLACE FUNCTION get_document_storage_path(p_chunk_id UUID)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  storage_path TEXT,
  yacht_id UUID,
  filename TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
SET row_security = off  -- NEW: Bypass RLS within this function
AS $$
DECLARE
  v_user_id UUID;
  v_user_yacht_id UUID;
  v_found BOOLEAN := FALSE;
BEGIN
  -- Get current user ID from JWT
  v_user_id := auth.uid();

  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  -- Get user's yacht_id from auth_users_profiles
  SELECT up.yacht_id INTO v_user_yacht_id
  FROM auth_users_profiles up
  WHERE up.id = v_user_id
    AND up.is_active = true;

  IF v_user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not assigned to yacht';
  END IF;

  -- STRATEGY 1: Try as chunk_id first (most specific)
  RETURN QUERY
  SELECT
    sdc.id as chunk_id,
    sdc.document_id,
    dm.storage_path,
    sdc.yacht_id,
    dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id;

  IF FOUND THEN
    v_found := TRUE;
    RETURN;
  END IF;

  -- STRATEGY 2: Try as document_id
  RETURN QUERY
  SELECT
    sdc.id as chunk_id,
    sdc.document_id,
    dm.storage_path,
    sdc.yacht_id,
    dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.document_id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id
  LIMIT 1;

  IF FOUND THEN
    v_found := TRUE;
    RETURN;
  END IF;

  -- STRATEGY 3: Try as doc_metadata.id directly
  RETURN QUERY
  SELECT
    NULL::UUID as chunk_id,
    dm.id as document_id,
    dm.storage_path,
    dm.yacht_id,
    dm.filename
  FROM doc_metadata dm
  WHERE dm.id = p_chunk_id
    AND dm.yacht_id = v_user_yacht_id;

  IF FOUND THEN
    v_found := TRUE;
    RETURN;
  END IF;

  -- Nothing found
  IF NOT v_found THEN
    RAISE EXCEPTION 'Document not found or access denied';
  END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION get_document_storage_path(UUID) TO authenticated;
```

---

### **Migration 11: Create get_user_auth_info() RPC**

```sql
-- Create RPC function for frontend authentication
CREATE OR REPLACE FUNCTION get_user_auth_info(p_user_id UUID)
RETURNS TABLE (
  yacht_id UUID,
  email TEXT,
  name TEXT,
  is_active BOOLEAN,
  role TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.yacht_id,
    p.email,
    p.name,
    p.is_active,
    (
      SELECT r.role
      FROM auth_users_roles r
      WHERE r.user_id = p.id
        AND r.yacht_id = p.yacht_id
        AND r.is_active = true
        AND r.valid_from <= NOW()
        AND (r.valid_until IS NULL OR r.valid_until > NOW())
      ORDER BY r.assigned_at DESC
      LIMIT 1
    ) as role
  FROM auth_users_profiles p
  WHERE p.id = p_user_id;
END;
$$;

GRANT EXECUTE ON FUNCTION get_user_auth_info(UUID) TO authenticated;
```

---

## **After Applying: Test Document Viewing**

1. Login to your app
2. Search for a document
3. Click "View"
4. PDF should open ✅

---

## **What Each Migration Fixes**

| Migration | What It Does |
|-----------|--------------|
| 09 | Fixes RLS policy on search_document_chunks to reference correct table (auth_users_profiles instead of auth_users) |
| 10 | Adds `SET row_security = off` to get_document_storage_path() so it bypasses broken RLS policies |
| 11 | Creates missing get_user_auth_info() RPC that frontend needs to load user data on login |

---

## **Full Architecture Documentation**

See: `SECURITY_ARCHITECTURE_MAP.md` for complete details on:
- All RLS policies
- All RPC functions
- How tables cross-reference
- Authentication flow
- Document access flow
