# 🔐 CelesteOS Security Architecture Map

## **Tables: Auth & User Management**

### **auth_users_profiles** (Primary User Table)
```sql
Columns:
- id (UUID) - matches auth.users.id
- yacht_id (UUID) - which yacht user belongs to
- email (TEXT)
- name (TEXT)
- is_active (BOOLEAN)
- created_at, updated_at

Purpose: Stores user profile + yacht assignment
RLS: Users can view/update own profile
```

### **auth_users_roles** (Role Assignments)
```sql
Columns:
- id (UUID)
- user_id (UUID) - references auth_users_profiles.id
- yacht_id (UUID)
- role (TEXT) - 'captain', 'chief_engineer', 'eto', 'crew', etc.
- is_active (BOOLEAN)
- valid_from (TIMESTAMP)
- valid_until (TIMESTAMP)
- assigned_by (UUID)
- assigned_at (TIMESTAMP)

Purpose: Manages user roles (can have multiple roles over time)
RLS: Users can view own roles, HODs can manage roles
```

---

## **RPC Functions: How They Work**

### **1. get_user_yacht_id() → UUID**
```sql
Location: migration 05
Security: SECURITY DEFINER, STABLE
Queries: auth_users_profiles
Returns: yacht_id for current user (auth.uid())
```

**Used by:** Most RLS policies to enforce yacht isolation

---

### **2. get_user_role() → TEXT** (2 versions)

**Version A: With params**
```sql
get_user_role(p_user_id UUID, p_yacht_id UUID) → TEXT
Queries: auth_users_roles
Returns: Active role for specific user on specific yacht
```

**Version B: No params (current user)**
```sql
get_user_role() → TEXT
Queries: auth_users_profiles JOIN auth_users_roles
Returns: Active role for current user (auth.uid())
```

**Used by:** RLS policies that need role-based access (HOD permissions)

---

### **3. is_hod(p_user_id UUID, p_yacht_id UUID) → BOOLEAN**
```sql
Location: migration 05
Security: SECURITY DEFINER, STABLE
Queries: auth_users_roles
Returns: true if user has HOD role (chief_engineer, captain, manager)
```

**Used by:** RLS policies for HOD-only actions (manage roles, etc.)

---

### **4. get_document_storage_path(p_chunk_id UUID) → TABLE**
```sql
Location: migration 05 (NEEDS UPDATE - migration 10)
Security: SECURITY DEFINER
Currently Missing: SET row_security = off
Queries: auth_users_profiles, search_document_chunks, doc_metadata
Returns: {chunk_id, document_id, storage_path, yacht_id, filename}
```

**Flow:**
1. Gets user's yacht_id from auth_users_profiles
2. Searches for chunk/document matching p_chunk_id AND user's yacht
3. Returns storage path if found

**ISSUE:** Missing `SET row_security = off` → can fail if RLS policies broken

---

### **5. custom_access_token_hook(event JSONB) → JSONB**
```sql
Location: migration 06
Security: SECURITY DEFINER, VOLATILE
Queries: auth_users_profiles, auth_users_roles
Called by: Supabase Auth service (on login/token refresh)
```

**Flow:**
1. Auth service calls this on every JWT generation
2. Function queries auth_users_profiles → gets yacht_id
3. Function queries auth_users_roles → gets role
4. Adds to JWT claims: {yacht_id: "...", user_role: "..."}
5. Returns modified event

**Result:** JWT contains yacht_id + role for faster RLS evaluation

---

### **❌ 6. get_user_auth_info(p_user_id UUID) → MISSING!**

**Expected by:** Frontend AuthContext (line 87)

**Should return:**
```sql
{
  yacht_id: UUID,
  email: TEXT,
  name: TEXT,
  is_active: BOOLEAN,
  role: TEXT  (optional)
}
```

**THIS FUNCTION DOESN'T EXIST!** Frontend may be failing silently.

---

## **RLS Policies: Who Can Access What**

### **Yacht Isolation Pattern** (Most Common)
```sql
USING (yacht_id = public.get_user_yacht_id())
```

**Tables using this:**
- equipment
- faults
- work_orders
- parts
- pms_*
- doc_metadata
- search_document_chunks (BROKEN - references old auth_users table)

### **User-Specific Access**
```sql
USING (id = auth.uid())  -- For user_profiles
USING (user_id = auth.uid())  -- For user_roles, api_tokens
```

### **HOD Permissions**
```sql
USING (
  yacht_id = public.get_user_yacht_id()
  AND public.get_user_role() IN ('chief_engineer', 'captain', 'manager')
)
```

**Used for:**
- Managing roles
- Managing parts inventory
- Advanced operations

### **Storage Bucket RLS** (NEW - migration 08)
```sql
ON storage.objects
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
)
```

**Purpose:** Allows users to access files in `documents/{yacht_id}/*`

---

## **Authentication Flow**

### **1. User Login**
```
User enters email/password
  ↓
supabase.auth.signInWithPassword()
  ↓
Supabase Auth validates credentials
  ↓
Calls custom_access_token_hook(event)
    ↓ Queries auth_users_profiles
    ↓ Queries auth_users_roles
    ↓ Adds yacht_id + role to JWT
  ↓
Returns JWT with claims: {
  sub: user_id,
  email: "...",
  yacht_id: "...",  ← Added by hook
  user_role: "captain"  ← Added by hook
}
  ↓
Frontend receives session
  ↓
Frontend calls get_user_auth_info(user_id) ← MISSING RPC!
  ↓
Frontend builds CelesteUser object
  ↓
User authenticated ✅
```

---

## **Document Access Flow**

### **Full Flow**
```
User searches documents
  ↓
Backend returns search results with chunk_id
  ↓
Frontend calls get_document_storage_path(chunk_id)
  ↓
RPC Function:
  1. Gets user's yacht_id from auth_users_profiles
  2. Queries search_document_chunks WHERE id = chunk_id AND yacht_id = user's yacht
     ↓ Uses RLS policy (BROKEN - references auth_users table)
  3. Joins doc_metadata to get storage_path
  4. Returns {storage_path, filename, yacht_id}
  ↓
Frontend strips "documents/" prefix
  ↓
Frontend calls supabase.storage.from('documents').createSignedUrl(path)
  ↓
Storage checks RLS policy on storage.objects
  ↓ USING (bucket_id = 'documents' AND folder = user's yacht_id)
  ↓
Returns signed URL if allowed
  ↓
PDF opens ✅
```

---

## **Cross-References: Where Tables Connect**

### **auth_users_profiles ← auth_users_roles**
```sql
JOIN auth_users_roles r ON r.user_id = p.id AND r.yacht_id = p.yacht_id
```
**Used by:**
- get_user_role()
- custom_access_token_hook()

### **auth_users_profiles → All Data Tables**
```sql
-- Via yacht_id lookup
WHERE yacht_id = (SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid())
```
**Used by:**
- All RLS policies
- get_user_yacht_id()

### **search_document_chunks → doc_metadata**
```sql
JOIN doc_metadata dm ON sdc.document_id = dm.id
```
**Used by:**
- get_document_storage_path()

### **storage.objects ← auth_users_profiles**
```sql
-- Via folder path matching
WHERE (storage.foldername(name))[1] = (
  SELECT yacht_id::text FROM auth_users_profiles WHERE id = auth.uid()
)
```
**Used by:**
- Storage RLS policy (migration 08)

---

## **BUGS FOUND**

### **🔴 CRITICAL**

1. **Missing RPC: get_user_auth_info()**
   - Frontend expects it (AuthContext.tsx:87)
   - Doesn't exist in database
   - Frontend may be failing to load user data

2. **Broken RLS on search_document_chunks**
   - References `auth_users` table (deleted in migration 05)
   - Should reference `auth_users_profiles`
   - Fix: migration 09

3. **Missing SET row_security = off in get_document_storage_path()**
   - SECURITY DEFINER alone doesn't bypass RLS
   - Can fail if RLS policies have issues
   - Fix: migration 10

### **⚠️ WARNINGS**

4. **No validation that custom_access_token_hook is enabled**
   - Hook must be configured in Supabase Dashboard
   - No way to verify it's running from SQL
   - Could be silently failing

---

## **Recommended Fixes**

### **Priority 1: Create get_user_auth_info() RPC**
```sql
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

### **Priority 2: Apply migrations 09 & 10**
- Fix search_document_chunks RLS table reference
- Add row_security = off to get_document_storage_path()

---

## **Summary**

| Component | Table | Purpose | Status |
|-----------|-------|---------|--------|
| User Profiles | auth_users_profiles | Yacht assignment, profile data | ✅ Working |
| User Roles | auth_users_roles | Role management, time-based roles | ✅ Working |
| JWT Hook | custom_access_token_hook() | Add yacht_id+role to JWT | ✅ Working |
| Yacht Isolation | get_user_yacht_id() | RLS helper | ✅ Working |
| Role Check | get_user_role() | RLS helper | ✅ Working |
| HOD Check | is_hod() | RLS helper | ✅ Working |
| Document Path | get_document_storage_path() | Get file path | ⚠️ Needs row_security=off |
| Frontend Auth | get_user_auth_info() | Load user data | ❌ MISSING |
| Search RLS | chunks_yacht_isolation | Enforce yacht access | ❌ BROKEN |
| Storage RLS | Users read yacht documents | File access | ✅ Working |

**Next Steps:**
1. Create get_user_auth_info() RPC (migration 11)
2. Apply migration 09 (fix search_document_chunks RLS)
3. Apply migration 10 (add row_security = off)
4. Test document viewing end-to-end
