/**
 * IMMEDIATE CONNECTION TEST
 *
 * Run this in browser console (F12) while on your app
 * This will test if the app can actually reach Supabase
 */

(async function testConnection() {
  console.log('🔍 Testing Supabase Connection...\n');

  // Check if supabase client exists
  if (typeof supabase === 'undefined') {
    console.error('❌ FATAL: Supabase client not initialized in browser');
    console.error('   → Check NEXT_PUBLIC_SUPABASE_URL in Vercel env vars');
    return;
  }

  console.log('✅ Supabase client exists');

  // Try to get session (tests auth service connection)
  try {
    console.log('Testing auth service...');
    const { data: { session }, error } = await supabase.auth.getSession();

    if (error) {
      console.error('❌ Auth service ERROR:', error);
      console.error('   → Supabase might be unreachable or credentials wrong');
      return;
    }

    if (!session) {
      console.warn('⚠️  No session (not logged in, but auth service IS reachable)');
    } else {
      console.log('✅ Auth service reachable, user:', session.user.email);
    }
  } catch (err) {
    console.error('❌ FATAL: Cannot reach Supabase auth service');
    console.error('   Error:', err.message);
    console.error('   → Check if Supabase project is paused/deleted');
    return;
  }

  // Try a simple database query
  try {
    console.log('\nTesting database connection...');
    const { data, error } = await supabase
      .from('auth_users_profiles')
      .select('id')
      .limit(1);

    if (error) {
      console.error('❌ Database query ERROR:', error);
      console.error('   Code:', error.code);
      console.error('   Message:', error.message);

      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        console.error('   → NETWORK ERROR: Cannot reach Supabase database');
        console.error('   → Check if Supabase project exists and is not paused');
      } else if (error.code === '42P01') {
        console.error('   → Table does not exist (but database IS reachable)');
      } else if (error.code === 'PGRST116') {
        console.error('   → No rows (RLS filtering, but database IS reachable)');
      }
    } else {
      console.log('✅ Database reachable and queryable');
      console.log('   → Connection working!');
    }
  } catch (err) {
    console.error('❌ FATAL: Database connection failed');
    console.error('   Error:', err.message);
    console.error('   → Supabase project may be down or deleted');
  }

  // Check RPC function exists
  try {
    console.log('\nTesting RPC function...');
    // Use a fake UUID to test if function exists (will fail with P0001 but that's OK)
    const { data, error } = await supabase
      .rpc('get_document_storage_path', {
        p_chunk_id: '00000000-0000-0000-0000-000000000000'
      });

    if (error) {
      if (error.code === 'P0001') {
        console.log('✅ RPC function exists (returned expected error)');
        console.log('   Error:', error.message);
      } else if (error.code === '42883' || error.message.includes('does not exist')) {
        console.error('❌ RPC function NOT FOUND');
        console.error('   → Migration not deployed');
      } else {
        console.error('⚠️  RPC error:', error.code, error.message);
      }
    } else {
      console.log('✅ RPC function exists and returned data');
    }
  } catch (err) {
    console.error('❌ RPC test failed:', err.message);
  }

  console.log('\n' + '='.repeat(60));
  console.log('TEST COMPLETE');
  console.log('='.repeat(60));
})();
