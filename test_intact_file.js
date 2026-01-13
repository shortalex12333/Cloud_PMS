/**
 * TEST INTACT FILE - Run in browser console
 * This tests with a known-good file that's 715KB (not corrupt)
 */
(async function testIntactFile() {
  console.log('🧪 Testing document access with intact file...\n');

  // Test with intact file chunk ID
  const testChunkId = 'a7d09bbf-4203-4732-a36c-727b687dc956';
  console.log('📍 Test chunk ID:', testChunkId);

  try {
    // Step 1: Call RPC
    console.log('\n1️⃣ Calling RPC get_document_storage_path...');
    const { data: rpcData, error: rpcError } = await supabase.rpc('get_document_storage_path', {
      p_chunk_id: testChunkId
    });

    if (rpcError) {
      console.error('❌ RPC Error:', rpcError);
      return;
    }

    console.log('✅ RPC Success:', rpcData);

    const docInfo = Array.isArray(rpcData) ? rpcData[0] : rpcData;
    console.log('📄 Document info:', {
      filename: docInfo.filename,
      storage_path: docInfo.storage_path,
      yacht_id: docInfo.yacht_id
    });

    // Step 2: Strip documents/ prefix
    const storagePath = docInfo.storage_path.replace('documents/', '');
    console.log('\n2️⃣ Storage path (stripped):', storagePath);

    // Step 3: Create signed URL
    console.log('\n3️⃣ Creating signed URL...');
    const { data: urlData, error: urlError } = await supabase.storage
      .from('documents')
      .createSignedUrl(storagePath, 3600);

    if (urlError) {
      console.error('❌ Signed URL Error:', {
        message: urlError.message,
        statusCode: urlError.statusCode,
        error: urlError
      });
      return;
    }

    console.log('✅ Signed URL created successfully!');
    console.log('🔗 URL:', urlData.signedUrl);
    console.log('\n👉 Opening PDF in new tab...');

    // Open in new tab
    window.open(urlData.signedUrl, '_blank');

    console.log('\n✅ TEST COMPLETE - If PDF opened, code is working perfectly!');

  } catch (err) {
    console.error('❌ Test failed:', err);
  }
})();
