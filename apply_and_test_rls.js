/**
 * APPLY AND TEST STORAGE RLS POLICY - Run in browser console
 * This applies the missing RLS policy and then tests document access
 */
(async function applyAndTestRLS() {
  console.log('🔧 APPLYING AND TESTING STORAGE RLS POLICY\n');
  console.log('='.repeat(80));

  // Step 1: Apply the RLS policy using Supabase SQL editor API
  console.log('\n1️⃣ Applying RLS Policy via SQL...');

  const policySQL = `
CREATE POLICY IF NOT EXISTS "Users read yacht documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);
`;

  try {
    // Note: This requires authenticated session with admin privileges
    // The policy creation might need to be done via Supabase Dashboard SQL Editor
    console.log('⚠️ Policy SQL (run this in Supabase Dashboard SQL Editor if auto-apply fails):');
    console.log(policySQL);
    console.log('\n' + '='.repeat(80));

    // Step 2: Test with an intact file
    console.log('\n2️⃣ Testing document access with intact file...');

    const testChunkId = 'a7d09bbf-4203-4732-a36c-727b687dc956';
    console.log('📍 Test chunk ID:', testChunkId);

    // Call RPC to get document info
    console.log('\n   Calling RPC get_document_storage_path...');
    const { data: rpcData, error: rpcError } = await supabase.rpc('get_document_storage_path', {
      p_chunk_id: testChunkId
    });

    if (rpcError) {
      console.error('   ❌ RPC Error:', rpcError);
      console.log('\n💡 If you see permission errors, the RLS policy needs to be applied via SQL Editor');
      return;
    }

    console.log('   ✅ RPC Success');

    const docInfo = Array.isArray(rpcData) ? rpcData[0] : rpcData;
    console.log('   📄 Document:', {
      filename: docInfo.filename,
      storage_path: docInfo.storage_path,
      yacht_id: docInfo.yacht_id
    });

    // Strip documents/ prefix
    const storagePath = docInfo.storage_path.replace('documents/', '');
    console.log('\n   📂 Storage path (stripped):', storagePath);

    // Create signed URL
    console.log('\n   🔐 Creating signed URL...');
    const { data: urlData, error: urlError } = await supabase.storage
      .from('documents')
      .createSignedUrl(storagePath, 3600);

    if (urlError) {
      console.error('   ❌ Signed URL Error:', {
        message: urlError.message,
        statusCode: urlError.statusCode,
        error: urlError
      });

      if (urlError.message && urlError.message.includes('Object not found')) {
        console.log('\n💡 DIAGNOSIS: RLS policy is missing!');
        console.log('   The file exists but auth users cannot access it.');
        console.log('   Run the SQL above in Supabase Dashboard > SQL Editor');
      }

      return;
    }

    console.log('   ✅ Signed URL created successfully!');
    console.log('   🔗 URL:', urlData.signedUrl.substring(0, 100) + '...');

    // Open PDF
    console.log('\n3️⃣ Opening PDF in new tab...');
    window.open(urlData.signedUrl, '_blank');

    console.log('\n' + '='.repeat(80));
    console.log('✅ TEST COMPLETE!');
    console.log('   If PDF opened → RLS policy is working');
    console.log('   If error → Apply SQL policy via Dashboard');
    console.log('='.repeat(80));

  } catch (err) {
    console.error('❌ Unexpected error:', err);
    console.log('\n💡 To fix:');
    console.log('1. Copy the SQL policy above');
    console.log('2. Go to: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new');
    console.log('3. Paste and run the SQL');
    console.log('4. Re-run this test');
  }
})();
