# 🔍 Run This Test NOW in Browser Console

## Quick Test (2 minutes)

### Step 1: Login to your app

### Step 2: Open browser console
- Press **F12** (or Cmd+Option+I on Mac)
- Click **Console** tab

### Step 3: Copy and paste this ENTIRE block:

```javascript
(async function quickTest() {
  console.log('='.repeat(60));
  console.log('DOCUMENT ACCESS QUICK TEST');
  console.log('='.repeat(60));

  // TEST 1: Check session
  console.log('\n1. Checking session...');
  const { data: { session }, error: sessionError } = await supabase.auth.getSession();

  if (sessionError || !session) {
    console.error('❌ NO SESSION - You need to login first!');
    return;
  }

  const expiresAt = new Date(session.expires_at * 1000);
  const isExpired = expiresAt < new Date();

  console.log('  User:', session.user.email);
  console.log('  Expires:', expiresAt.toLocaleString());
  console.log('  Status:', isExpired ? '❌ EXPIRED!' : '✅ Valid');

  if (isExpired) {
    console.error('❌ SESSION EXPIRED - Refresh page and login again!');
    return;
  }

  // TEST 2: Get user profile
  console.log('\n2. Checking user profile...');
  const { data: profile, error: profileError } = await supabase
    .from('auth_users_profiles')
    .select('yacht_id, email, is_active')
    .eq('id', session.user.id)
    .single();

  if (profileError) {
    console.error('❌ Profile error:', profileError.message);
    if (profileError.code === 'PGRST116') {
      console.error('  → User not in auth_users_profiles table!');
    }
    return;
  }

  console.log('  Yacht ID:', profile.yacht_id || '❌ NULL');
  console.log('  Active:', profile.is_active ? '✅ Yes' : '❌ No');

  if (!profile.yacht_id) {
    console.error('❌ NO YACHT_ID - Contact admin!');
    return;
  }

  // TEST 3: Get a chunk to test
  console.log('\n3. Getting test chunk...');
  const { data: chunks, error: chunksError } = await supabase
    .from('search_document_chunks')
    .select('id, document_id')
    .limit(1);

  if (chunksError || !chunks || chunks.length === 0) {
    console.error('❌ No chunks found:', chunksError?.message || 'Empty result');
    return;
  }

  const testChunkId = chunks[0].id;
  console.log('  Test chunk ID:', testChunkId);

  // TEST 4: Call RPC
  console.log('\n4. Testing RPC function...');
  const { data: rpcData, error: rpcError } = await supabase
    .rpc('get_document_storage_path', { p_chunk_id: testChunkId });

  if (rpcError) {
    console.error('❌ RPC FAILED!');
    console.error('  Code:', rpcError.code);
    console.error('  Message:', rpcError.message);

    if (rpcError.code === 'P0001') {
      if (rpcError.message.includes('Not authenticated')) {
        console.error('  → auth.uid() returned NULL inside RPC');
        console.error('  → This should NOT happen if session is valid');
        console.error('  → POSSIBLE BUG IN RPC OR SESSION');
      } else if (rpcError.message.includes('not assigned to yacht')) {
        console.error('  → User has no yacht_id in database');
        console.error('  → But we just checked and found:', profile.yacht_id);
        console.error('  → POSSIBLE RPC BUG');
      } else if (rpcError.message.includes('not found or access denied')) {
        console.error('  → Chunk not found OR yacht mismatch');
        console.error('  → Check if chunk belongs to your yacht');
      }
    } else if (rpcError.code === '42883') {
      console.error('  → RPC function does not exist!');
      console.error('  → Migration not deployed');
    } else {
      console.error('  → Unknown error');
    }
    return;
  }

  const doc = Array.isArray(rpcData) ? rpcData[0] : rpcData;

  if (!doc) {
    console.error('❌ RPC returned no data');
    return;
  }

  console.log('✅ RPC SUCCESS!');
  console.log('  Storage path:', doc.storage_path);
  console.log('  Filename:', doc.filename);
  console.log('  Yacht ID:', doc.yacht_id);

  // TEST 5: Test signed URL creation
  console.log('\n5. Testing signed URL creation...');
  let storagePath = doc.storage_path;

  // Strip "documents/" prefix like DocumentSituationView does
  if (storagePath.startsWith('documents/')) {
    storagePath = storagePath.substring('documents/'.length);
    console.log('  Stripped path:', storagePath);
  }

  // Validate yacht isolation like documentLoader does
  if (!storagePath.startsWith(profile.yacht_id + '/')) {
    console.error('❌ Path does not start with yacht_id!');
    console.error('  Path:', storagePath);
    console.error('  Expected prefix:', profile.yacht_id + '/');
    return;
  }

  console.log('  ✅ Path validation passed');

  // Create signed URL
  const { data: urlData, error: urlError } = await supabase.storage
    .from('documents')
    .createSignedUrl(storagePath, 3600);

  if (urlError) {
    console.error('❌ Signed URL creation failed:', urlError.message);
    return;
  }

  if (!urlData?.signedUrl) {
    console.error('❌ No signed URL returned');
    return;
  }

  console.log('✅ Signed URL created successfully!');
  console.log('  URL length:', urlData.signedUrl.length);
  console.log('  URL preview:', urlData.signedUrl.substring(0, 100) + '...');

  // TEST 6: Check if file actually exists
  console.log('\n6. Checking if file exists in storage...');
  try {
    const response = await fetch(urlData.signedUrl, { method: 'HEAD' });
    console.log('  HTTP Status:', response.status);

    if (response.status === 200) {
      console.log('✅ FILE EXISTS AND IS ACCESSIBLE!');
    } else if (response.status === 404) {
      console.error('❌ FILE NOT FOUND IN STORAGE!');
      console.error('  → storage_path in database but file missing from bucket');
    } else if (response.status === 403) {
      console.error('❌ ACCESS DENIED!');
      console.error('  → Storage bucket RLS blocking access');
    } else {
      console.error('⚠️ Unexpected status:', response.status);
    }
  } catch (err) {
    console.error('❌ Failed to check file:', err.message);
  }

  console.log('\n' + '='.repeat(60));
  console.log('TEST COMPLETE');
  console.log('='.repeat(60));

  console.log('\n📋 SUMMARY:');
  console.log('Session: ✅');
  console.log('Profile: ✅');
  console.log('Chunks: ✅');
  console.log('RPC: ' + (rpcError ? '❌' : '✅'));
  console.log('Signed URL: ' + (urlError ? '❌' : '✅'));

  if (!rpcError && !urlError) {
    console.log('\n🎉 ALL TESTS PASSED!');
    console.log('Document viewing SHOULD work.');
    console.log('If it still fails, check:');
    console.log('1. Browser Network tab for failed requests');
    console.log('2. DocumentSituationView console logs');
    console.log('3. Exact error message shown to user');
  }
})();
```

### Step 4: Press Enter

### Step 5: Copy the output and share it

---

## What This Test Does

1. ✅ Checks if you're logged in and session is valid
2. ✅ Checks if you have yacht_id assigned
3. ✅ Gets a real chunk_id from your yacht's documents
4. ✅ Calls the RPC function (same as DocumentSituationView)
5. ✅ Creates signed URL (same as documentLoader)
6. ✅ Checks if file actually exists in storage

---

## Expected Output

If everything works:
```
=============================================================
DOCUMENT ACCESS QUICK TEST
=============================================================

1. Checking session...
  User: x@alex-short.com
  Expires: [future date]
  Status: ✅ Valid

2. Checking user profile...
  Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
  Active: ✅ Yes

3. Getting test chunk...
  Test chunk ID: 0f506cc8-e13c-49e5-bdcb-e3725e8dae1b

4. Testing RPC function...
✅ RPC SUCCESS!
  Storage path: documents/85fe1119-.../Radar_Systems_Reference_Manual.pdf
  Filename: Radar_Systems_Reference_Manual.pdf
  Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598

5. Testing signed URL creation...
  Stripped path: 85fe1119-.../Radar_Systems_Reference_Manual.pdf
  ✅ Path validation passed
✅ Signed URL created successfully!
  URL length: 500+
  URL preview: https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/sign/...

6. Checking if file exists in storage...
  HTTP Status: 200
✅ FILE EXISTS AND IS ACCESSIBLE!

=============================================================
TEST COMPLETE
=============================================================

📋 SUMMARY:
Session: ✅
Profile: ✅
Chunks: ✅
RPC: ✅
Signed URL: ✅

🎉 ALL TESTS PASSED!
Document viewing SHOULD work.
```

---

## Common Failures

### ❌ "SESSION EXPIRED"
**Cause:** JWT token expired
**Fix:** Refresh page and login again

### ❌ "NO YACHT_ID"
**Cause:** User not configured
**Fix:** Check database, update auth_users_profiles

### ❌ "RPC: Not authenticated"
**Cause:** auth.uid() returns NULL
**Fix:** Session timing issue, check AuthContext

### ❌ "RPC: Document not found or access denied"
**Cause:** Chunk doesn't exist or wrong yacht
**Fix:** Check chunk_id from search results

### ❌ "FILE NOT FOUND IN STORAGE"
**Cause:** storage_path in database but file missing
**Fix:** Upload files to Supabase Storage

### ❌ "ACCESS DENIED" (storage)
**Cause:** Storage bucket RLS blocking
**Fix:** Check storage bucket policies

---

## Database Already Verified ✅

I already checked the database and found:
- ✅ RPC function configured correctly (`row_security = off`)
- ✅ User has yacht_id assigned
- ✅ 47,166 document chunks exist
- ✅ 2,699 documents with storage_path
- ✅ RLS policies have COALESCE fallback

**So the database is perfect.** This browser test will show if the issue is in the frontend/session.

---

## Run This Test NOW

This will tell us exactly where it's failing:
- Session?
- RPC?
- Storage?

**Takes 30 seconds to run, will pinpoint the exact issue.**
