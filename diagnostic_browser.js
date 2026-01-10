/**
 * ================================================================================
 * DIAGNOSTIC SCRIPT 2: Frontend/Browser Console Checks
 * ================================================================================
 *
 * How to run:
 * 1. Login to your app
 * 2. Open browser console (F12 or Cmd+Option+I)
 * 3. Copy and paste this ENTIRE script
 * 4. Press Enter
 * 5. Copy all output and share for diagnosis
 *
 * ================================================================================
 */

(async function runDiagnostics() {
  console.log('🔍 Starting Document Access Diagnostics...\n');

  const results = {
    checks: [],
    errors: [],
    warnings: [],
  };

  // ============================================================================
  // CHECK 1: Supabase Client & Session
  // ============================================================================
  console.log('=== CHECK 1: Supabase Client & Session ===');

  try {
    if (typeof supabase === 'undefined') {
      results.errors.push('❌ Supabase client not found in global scope');
      console.error('❌ Supabase client not available. Are you logged in?');
      return results;
    }

    const { data: { session }, error: sessionError } = await supabase.auth.getSession();

    if (sessionError) {
      results.errors.push(`❌ Session error: ${sessionError.message}`);
      console.error('❌ Session error:', sessionError);
      return results;
    }

    if (!session) {
      results.errors.push('❌ No active session - user not logged in');
      console.error('❌ No active session. Please login first.');
      return results;
    }

    const user = session.user;
    const expiresAt = new Date(session.expires_at * 1000);
    const isExpired = expiresAt < new Date();

    console.log('✅ Session found');
    console.log('  User ID:', user.id);
    console.log('  Email:', user.email);
    console.log('  Expires:', expiresAt.toLocaleString());
    console.log('  Status:', isExpired ? '❌ EXPIRED' : '✅ Valid');

    results.checks.push({
      check: '1.1 Session Valid',
      status: isExpired ? 'FAIL' : 'PASS',
      data: { user_id: user.id, email: user.email, expires_at: expiresAt },
    });

    if (isExpired) {
      results.errors.push('❌ Session expired - refresh and login again');
      return results;
    }

    // Decode JWT
    const token = session.access_token;
    const payload = JSON.parse(atob(token.split('.')[1]));

    console.log('\n📋 JWT Payload:');
    console.log('  sub (user_id):', payload.sub);
    console.log('  email:', payload.email);
    console.log('  role:', payload.role);
    console.log('  yacht_id:', payload.yacht_id || '⚠️  MISSING (JWT hook not enabled)');

    results.checks.push({
      check: '1.2 JWT Claims',
      status: 'PASS',
      data: {
        has_yacht_id: !!payload.yacht_id,
        yacht_id: payload.yacht_id || null,
        role: payload.role,
      },
    });

    if (!payload.yacht_id) {
      results.warnings.push('⚠️  JWT missing yacht_id - will use DB fallback (slower)');
    }

  } catch (error) {
    results.errors.push(`❌ Session check failed: ${error.message}`);
    console.error('❌ Error checking session:', error);
    return results;
  }

  // ============================================================================
  // CHECK 2: User Profile & Yacht Assignment
  // ============================================================================
  console.log('\n=== CHECK 2: User Profile & Yacht Assignment ===');

  try {
    const { data: { session } } = await supabase.auth.getSession();
    const userId = session.user.id;

    // Query auth_users_profiles
    const { data: profile, error: profileError } = await supabase
      .from('auth_users_profiles')
      .select('id, email, yacht_id, is_active, name')
      .eq('id', userId)
      .single();

    if (profileError) {
      results.errors.push(`❌ Profile query error: ${profileError.message}`);
      console.error('❌ Profile error:', profileError);

      if (profileError.code === 'PGRST116') {
        console.error('  → User not found in auth_users_profiles table!');
        results.errors.push('❌ User not in auth_users_profiles table');
      }
    } else if (!profile) {
      results.errors.push('❌ No profile returned');
      console.error('❌ No profile found');
    } else {
      console.log('✅ Profile found');
      console.log('  ID:', profile.id);
      console.log('  Email:', profile.email);
      console.log('  Yacht ID:', profile.yacht_id || '❌ NULL');
      console.log('  Active:', profile.is_active ? '✅ Yes' : '❌ No');
      console.log('  Name:', profile.name || 'N/A');

      results.checks.push({
        check: '2.1 User Profile',
        status: profile.yacht_id && profile.is_active ? 'PASS' : 'FAIL',
        data: profile,
      });

      if (!profile.yacht_id) {
        results.errors.push('❌ User has no yacht_id assigned');
      }

      if (!profile.is_active) {
        results.errors.push('❌ User is not active');
      }
    }
  } catch (error) {
    results.errors.push(`❌ Profile check failed: ${error.message}`);
    console.error('❌ Error checking profile:', error);
  }

  // ============================================================================
  // CHECK 3: Document Data (search_document_chunks)
  // ============================================================================
  console.log('\n=== CHECK 3: Document Chunks Data ===');

  try {
    // Try to query search_document_chunks (RLS should filter by yacht)
    const { data: chunks, error: chunksError } = await supabase
      .from('search_document_chunks')
      .select('id, document_id, yacht_id')
      .limit(5);

    if (chunksError) {
      results.errors.push(`❌ Chunks query error: ${chunksError.message}`);
      console.error('❌ Chunks error:', chunksError);

      if (chunksError.code === 'PGRST116') {
        console.warn('  → No chunks found (RLS filtering or no data)');
        results.warnings.push('⚠️  No chunks found for your yacht');
      }
    } else if (!chunks || chunks.length === 0) {
      results.warnings.push('⚠️  No chunks returned - no documents indexed?');
      console.warn('⚠️  No chunks found for your yacht');
      console.warn('  → Documents may not be indexed yet');
    } else {
      console.log(`✅ Found ${chunks.length} chunks`);
      console.log('  Sample chunk IDs:');
      chunks.forEach((chunk, i) => {
        console.log(`    ${i + 1}. ${chunk.id}`);
      });

      results.checks.push({
        check: '3.1 Document Chunks Exist',
        status: 'PASS',
        data: { count: chunks.length, sample_chunk_id: chunks[0].id },
      });

      // Store first chunk_id for testing
      results.testChunkId = chunks[0].id;
    }
  } catch (error) {
    results.errors.push(`❌ Chunks check failed: ${error.message}`);
    console.error('❌ Error checking chunks:', error);
  }

  // ============================================================================
  // CHECK 4: Document Metadata
  // ============================================================================
  console.log('\n=== CHECK 4: Document Metadata ===');

  try {
    const { data: docs, error: docsError } = await supabase
      .from('doc_metadata')
      .select('id, filename, storage_path, yacht_id')
      .limit(5);

    if (docsError) {
      results.errors.push(`❌ Doc metadata query error: ${docsError.message}`);
      console.error('❌ Doc metadata error:', docsError);
    } else if (!docs || docs.length === 0) {
      results.warnings.push('⚠️  No documents in doc_metadata');
      console.warn('⚠️  No documents found in doc_metadata');
    } else {
      console.log(`✅ Found ${docs.length} documents`);
      console.log('  Sample documents:');
      docs.forEach((doc, i) => {
        const pathStatus = doc.storage_path ? '✅' : '❌ NULL';
        console.log(`    ${i + 1}. ${doc.filename} (${pathStatus})`);
      });

      const docsWithoutPath = docs.filter(d => !d.storage_path).length;
      if (docsWithoutPath > 0) {
        results.warnings.push(`⚠️  ${docsWithoutPath} documents missing storage_path`);
      }

      results.checks.push({
        check: '4.1 Document Metadata Exists',
        status: 'PASS',
        data: { count: docs.length, missing_paths: docsWithoutPath },
      });
    }
  } catch (error) {
    results.errors.push(`❌ Metadata check failed: ${error.message}`);
    console.error('❌ Error checking metadata:', error);
  }

  // ============================================================================
  // CHECK 5: Test RPC Function
  // ============================================================================
  console.log('\n=== CHECK 5: Test RPC Function ===');

  if (results.testChunkId) {
    console.log(`Testing RPC with chunk_id: ${results.testChunkId}`);

    try {
      const { data: rpcData, error: rpcError } = await supabase
        .rpc('get_document_storage_path', { p_chunk_id: results.testChunkId });

      if (rpcError) {
        results.errors.push(`❌ RPC error: ${rpcError.message}`);
        console.error('❌ RPC failed:', rpcError);
        console.error('  Code:', rpcError.code);
        console.error('  Message:', rpcError.message);

        if (rpcError.code === 'P0001') {
          console.error('  → This is a custom exception from the RPC function');
          if (rpcError.message.includes('Not authenticated')) {
            console.error('  → auth.uid() returned NULL inside RPC');
            results.errors.push('❌ RPC: Not authenticated (auth.uid() is NULL)');
          } else if (rpcError.message.includes('not assigned to yacht')) {
            console.error('  → User has no yacht_id in auth_users_profiles');
            results.errors.push('❌ RPC: User not assigned to yacht');
          } else if (rpcError.message.includes('not found or access denied')) {
            console.error('  → Document not found OR yacht_id mismatch');
            results.errors.push('❌ RPC: Document not found or access denied');
          }
        } else if (rpcError.code === '400' || rpcError.code === 'PGRST202') {
          console.error('  → RLS may be blocking queries inside RPC');
          results.errors.push('❌ RPC: Possible RLS blocking (check row_security = off)');
        }
      } else if (!rpcData || rpcData.length === 0) {
        results.warnings.push('⚠️  RPC returned no data');
        console.warn('⚠️  RPC returned no data');
      } else {
        const doc = Array.isArray(rpcData) ? rpcData[0] : rpcData;
        console.log('✅ RPC succeeded!');
        console.log('  Storage path:', doc.storage_path);
        console.log('  Filename:', doc.filename);
        console.log('  Yacht ID:', doc.yacht_id);

        results.checks.push({
          check: '5.1 RPC Function Works',
          status: 'PASS',
          data: doc,
        });
      }
    } catch (error) {
      results.errors.push(`❌ RPC test failed: ${error.message}`);
      console.error('❌ Error testing RPC:', error);
    }
  } else {
    console.warn('⚠️  No chunk_id available to test RPC');
    results.warnings.push('⚠️  No chunk_id to test RPC - no documents found');
  }

  // ============================================================================
  // CHECK 6: Test documentLoader
  // ============================================================================
  console.log('\n=== CHECK 6: Test documentLoader ===');

  // Note: Can't easily test this without importing the module
  console.log('⚠️  documentLoader test requires module import - skip for now');
  console.log('   To test manually:');
  console.log('   1. Open DocumentSituationView component');
  console.log('   2. Check console logs for documentLoader errors');

  // ============================================================================
  // FINAL SUMMARY
  // ============================================================================
  console.log('\n' + '='.repeat(80));
  console.log('📊 DIAGNOSTIC SUMMARY');
  console.log('='.repeat(80));

  console.log('\n✅ PASSED CHECKS:');
  const passed = results.checks.filter(c => c.status === 'PASS');
  if (passed.length === 0) {
    console.log('  None');
  } else {
    passed.forEach(c => console.log(`  ✅ ${c.check}`));
  }

  console.log('\n⚠️  WARNINGS:');
  if (results.warnings.length === 0) {
    console.log('  None');
  } else {
    results.warnings.forEach(w => console.log(`  ${w}`));
  }

  console.log('\n❌ ERRORS:');
  if (results.errors.length === 0) {
    console.log('  None - Everything looks good! 🎉');
  } else {
    results.errors.forEach(e => console.log(`  ${e}`));
  }

  console.log('\n' + '='.repeat(80));

  // Recommendation
  console.log('\n💡 RECOMMENDATION:');

  if (results.errors.length === 0) {
    console.log('✅ All checks passed! Document viewing should work.');
  } else if (results.errors.some(e => e.includes('Session expired'))) {
    console.log('🔄 Session expired - refresh page and login again');
  } else if (results.errors.some(e => e.includes('not in auth_users_profiles'))) {
    console.log('🔧 User not configured - contact admin to add user to auth_users_profiles');
  } else if (results.errors.some(e => e.includes('no yacht_id'))) {
    console.log('🔧 User has no yacht assigned - contact admin to set yacht_id');
  } else if (results.errors.some(e => e.includes('RLS blocking'))) {
    console.log('🔧 RLS blocking RPC - check if migration with "SET row_security = off" was applied');
  } else if (results.errors.some(e => e.includes('not found or access denied'))) {
    console.log('🔍 Document not found OR wrong yacht - check SQL diagnostics');
  } else {
    console.log('🔍 Multiple issues detected - review errors above and run SQL diagnostics');
  }

  console.log('\n📋 NEXT STEPS:');
  console.log('1. Copy this entire console output');
  console.log('2. Run diagnostic_sql.sql in Supabase SQL Editor');
  console.log('3. Share both outputs for complete diagnosis');

  console.log('\n' + '='.repeat(80));

  return results;
})();
