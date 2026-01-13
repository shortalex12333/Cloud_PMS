/**
 * CHECK JWT - Run in browser console while logged in
 */
(async function checkJWT() {
  console.log('🔍 CHECKING JWT AND YACHT_ID\n');
  console.log('='.repeat(80));

  // Get current session
  const { data: { session }, error } = await supabase.auth.getSession();

  if (error || !session) {
    console.error('❌ No session found!', error);
    return;
  }

  console.log('✅ Session found');
  console.log('\n📋 User Info:');
  console.log('   User ID:', session.user.id);
  console.log('   Email:', session.user.email);

  console.log('\n🎫 JWT Claims:');
  console.log('   aud:', session.user.aud);
  console.log('   role:', session.user.role);

  // Check for yacht_id in JWT claims (should be added by custom_access_token_hook)
  const yachtIdInJWT = session.user.user_metadata?.yacht_id ||
                        session.user.app_metadata?.yacht_id ||
                        (session.access_token && parseJWT(session.access_token).yacht_id);

  console.log('   yacht_id in JWT:', yachtIdInJWT || '❌ NOT FOUND');
  console.log('   user_role in JWT:', session.user.user_metadata?.role || '❌ NOT FOUND');

  console.log('\n🔍 Querying auth_users_profiles for actual yacht_id...');

  const { data: profile, error: profileError } = await supabase
    .from('auth_users_profiles')
    .select('yacht_id, name, is_active')
    .eq('id', session.user.id)
    .single();

  if (profileError) {
    console.error('❌ Profile query failed:', profileError);
  } else {
    console.log('✅ Profile found:');
    console.log('   Name:', profile.name);
    console.log('   Yacht ID:', profile.yacht_id);
    console.log('   Active:', profile.is_active);
  }

  console.log('\n' + '='.repeat(80));
  console.log('DIAGNOSIS:');

  if (!yachtIdInJWT && profile?.yacht_id) {
    console.log('⚠️ yacht_id is in database but NOT in JWT');
    console.log('   → custom_access_token_hook may not be enabled');
    console.log('   → RLS policies will use database lookup (slower but works)');
  } else if (yachtIdInJWT && profile?.yacht_id && yachtIdInJWT === profile.yacht_id) {
    console.log('✅ yacht_id matches in JWT and database');
  } else {
    console.log('❌ Mismatch or missing yacht_id');
  }

  console.log('='.repeat(80));

  function parseJWT(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      return JSON.parse(jsonPayload);
    } catch (e) {
      return {};
    }
  }
})();
