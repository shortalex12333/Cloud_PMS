# 🔍 Test Document RPC - Find the Real Issue

## Run These Tests in Browser Console

After logging in, open browser console (F12) and run:

### Test 1: Check if RPC function exists
```javascript
const { data, error } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: '98afe6f2-bdda-44e8-ad32-0b412816b860'
});

console.log('RPC Result:', { data, error });
```

**Expected if working:**
```javascript
RPC Result: {
  data: [{
    chunk_id: null,
    document_id: "98afe6f2-bdda-44e8-ad32-0b412816b860",
    storage_path: "documents/85fe1119.../Force10_Gourmet_Galley_Range_Manual.pdf",
    yacht_id: "85fe1119-b04c-41ac-80f1-829d23322598",
    filename: "Force10_Gourmet_Galley_Range_Manual.pdf"
  }],
  error: null
}
```

**If error:**
```javascript
RPC Result: {
  data: null,
  error: {
    message: "...",  // ← THIS IS WHAT WE NEED
    code: "...",
    details: "..."
  }
}
```

---

### Test 2: Check your JWT has correct claims
```javascript
const { data: { session } } = await supabase.auth.getSession();
const token = session.access_token;
const payload = JSON.parse(atob(token.split('.')[1]));

console.log('JWT user_id (sub):', payload.sub);
console.log('JWT yacht_id:', payload.yacht_id || 'MISSING!');
console.log('auth.uid():', session.user.id);
```

**Expected:**
```javascript
JWT user_id (sub): "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
JWT yacht_id: "85fe1119-b04c-41ac-80f1-829d23322598" OR "MISSING!"
auth.uid(): "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
```

---

### Test 3: Check auth_users_profiles query
```javascript
const { data, error } = await supabase
  .from('auth_users_profiles')
  .select('id, yacht_id, is_active')
  .eq('id', (await supabase.auth.getSession()).data.session.user.id)
  .single();

console.log('Profile query:', { data, error });
```

**Expected:**
```javascript
Profile query: {
  data: {
    id: "a35cad0b-...",
    yacht_id: "85fe1119-...",
    is_active: true
  },
  error: null
}
```

**If error:**
- `PGRST116`: No rows returned (user not in table!)
- `JWT expired`: Session expired
- `permission denied`: RLS blocking

---

### Test 4: Check doc_metadata query directly
```javascript
const { data, error } = await supabase
  .from('doc_metadata')
  .select('id, storage_path, filename, yacht_id')
  .eq('id', '98afe6f2-bdda-44e8-ad32-0b412816b860')
  .single();

console.log('Doc query:', { data, error });
```

**Expected:**
```javascript
Doc query: {
  data: {
    id: "98afe6f2-...",
    storage_path: "documents/85fe1119.../...",
    filename: "Force10_Gourmet_Galley_Range_Manual.pdf",
    yacht_id: "85fe1119-..."
  },
  error: null
}
```

**If error:**
- `PGRST116`: Document doesn't exist OR RLS blocking
- `JWT expired`: Session expired

---

## What to Report Back

Run ALL 4 tests and tell me:
1. **Test 1 result** - What error message exactly?
2. **Test 2 result** - Does JWT have yacht_id or "MISSING!"?
3. **Test 3 result** - Can you query your own profile?
4. **Test 4 result** - Can you query doc_metadata directly?

This will pinpoint EXACTLY where it's failing.

---

## Common Issues

### Issue: Test 1 fails with "Not authenticated"
**Cause:** auth.uid() returns NULL inside RPC
**Fix:** Session expired, refresh page and login again

### Issue: Test 1 fails with "User not assigned to yacht"
**Cause:** auth_users_profiles query inside RPC returns no yacht_id
**Fix:** Check Test 3 - if that also fails, user not in auth_users_profiles table

### Issue: Test 1 fails with "Document not found or access denied"
**Cause:** RPC found yacht_id but document doesn't exist or wrong yacht
**Fix:** Check Test 4 - can you query the document directly?

### Issue: Test 2 shows "MISSING!" for yacht_id
**Cause:** JWT hook not enabled (expected for now)
**Fix:** This is OK - RPC should still work using DB query fallback

### Issue: Test 3 fails with PGRST116
**Cause:** User not in auth_users_profiles table
**Fix:** Check database - user might not be inserted

### Issue: Test 4 fails with PGRST116
**Cause:** RLS blocking doc_metadata query
**Fix:** Need to fix RLS policies (COALESCE not working)

---

## Run These and Report Back

Paste the results of all 4 tests and I'll tell you exactly what's broken.
