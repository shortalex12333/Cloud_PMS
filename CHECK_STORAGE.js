/**
 * CHECK SUPABASE STORAGE - Run in browser console
 *
 * This will check if files actually exist in the storage bucket
 */

(async function checkStorage() {
  console.log('🔍 Checking Supabase Storage...\n');

  // Get yacht ID
  const { data: { session } } = await supabase.auth.getSession();
  const userId = session.user.id;

  const { data: profile } = await supabase
    .from('auth_users_profiles')
    .select('yacht_id')
    .eq('id', userId)
    .single();

  const yachtId = profile.yacht_id;
  console.log('Yacht ID:', yachtId);

  // Try to list files in yacht folder
  console.log('\n1. Listing files in yacht folder...');
  const { data: files, error: listError } = await supabase.storage
    .from('documents')
    .list(yachtId, { limit: 10 });

  if (listError) {
    console.error('❌ List error:', listError);
  } else if (!files || files.length === 0) {
    console.error('❌ NO FILES FOUND in storage bucket!');
    console.error('   → Files exist in doc_metadata but not uploaded to storage');
  } else {
    console.log(`✅ Found ${files.length} folders/files:`);
    files.forEach(f => console.log(`   - ${f.name}`));
  }

  // Try to get a specific file
  console.log('\n2. Checking specific file from doc_metadata...');
  const { data: doc } = await supabase
    .from('doc_metadata')
    .select('storage_path, filename')
    .eq('yacht_id', yachtId)
    .limit(1)
    .single();

  if (doc) {
    console.log('Sample doc from database:', doc.filename);
    console.log('Storage path:', doc.storage_path);

    // Strip "documents/" prefix
    let path = doc.storage_path;
    if (path.startsWith('documents/')) {
      path = path.substring('documents/'.length);
    }

    console.log('\n3. Checking if file exists in storage...');
    const { data: urlData, error: urlError } = await supabase.storage
      .from('documents')
      .createSignedUrl(path, 60);

    if (urlError) {
      console.error('❌ File does NOT exist in storage!');
      console.error('   Error:', urlError.message);
      console.error('   → Database has path but file not uploaded');
    } else {
      console.log('✅ File exists! URL:', urlData.signedUrl.substring(0, 100) + '...');
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('DIAGNOSIS:');
  console.log('='.repeat(60));

  if (listError || !files || files.length === 0) {
    console.log('❌ PROBLEM: Files NOT uploaded to Supabase Storage');
    console.log('\n📋 NEXT STEPS:');
    console.log('1. Check Supabase dashboard: Storage → documents bucket');
    console.log('2. Verify files exist in bucket under:', yachtId);
    console.log('3. If empty, need to upload PDFs to storage');
    console.log('4. Run backend indexing pipeline to populate storage');
  } else {
    console.log('✅ Files exist in storage');
    console.log('⚠️  But specific file might be missing');
    console.log('   Check if indexing is incomplete');
  }
})();
