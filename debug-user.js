#!/usr/bin/env node
/**
 * Debug user x@alex-short.com across all auth tables
 */

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

const USER_EMAIL = 'x@alex-short.com';

async function debugUser() {
  console.log('🔍 DEBUGGING USER:', USER_EMAIL);
  console.log('='.repeat(80));

  // Check 1: auth_users table
  console.log('\n📋 CHECK 1: auth_users');
  console.log('-'.repeat(80));

  const r1 = await fetch(`${SUPABASE_URL}/rest/v1/auth_users?email=eq.${USER_EMAIL}`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });

  const data1 = await r1.json();
  console.log('Found:', data1.length, 'rows');
  if (data1.length > 0) {
    console.log(JSON.stringify(data1[0], null, 2));
  }

  // Check 2: auth_users_yacht table
  console.log('\n📋 CHECK 2: auth_users_yacht');
  console.log('-'.repeat(80));

  const r2 = await fetch(`${SUPABASE_URL}/rest/v1/auth_users_yacht?email=eq.${USER_EMAIL}`, {
    headers: {
      'apikey': SERVICE_KEY,
      'Authorization': `Bearer ${SERVICE_KEY}`,
    }
  });

  const data2 = await r2.json();
  console.log('Found:', data2.length, 'rows');
  if (data2.length > 0) {
    console.log(JSON.stringify(data2[0], null, 2));
  }

  // Check 3: Supabase auth.users (internal)
  console.log('\n📋 CHECK 3: Check if user_id from auth_users_yacht exists');
  console.log('-'.repeat(80));

  if (data2.length > 0) {
    const userId = data2[0].user_id;
    console.log('user_id from auth_users_yacht:', userId);

    // Check if this user_id exists in auth_users
    const r3 = await fetch(`${SUPABASE_URL}/rest/v1/auth_users?id=eq.${userId}`, {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`,
      }
    });

    const data3 = await r3.json();
    console.log('Matching auth_users by id:', data3.length, 'rows');
    if (data3.length > 0) {
      console.log(JSON.stringify(data3[0], null, 2));
    }

    // Check if auth_user_id matches
    const r4 = await fetch(`${SUPABASE_URL}/rest/v1/auth_users?auth_user_id=eq.${userId}`, {
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': `Bearer ${SERVICE_KEY}`,
      }
    });

    const data4 = await r4.json();
    console.log('Matching auth_users by auth_user_id:', data4.length, 'rows');
    if (data4.length > 0) {
      console.log(JSON.stringify(data4[0], null, 2));
    }
  }

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('📊 SUMMARY');
  console.log('='.repeat(80));

  if (data1.length > 0 && data2.length > 0) {
    const auth_users_id = data1[0].id;
    const auth_users_auth_user_id = data1[0].auth_user_id;
    const auth_users_yacht_id = data1[0].yacht_id;

    const auth_users_yacht_user_id = data2[0].user_id;
    const auth_users_yacht_yacht_id = data2[0].yacht_id;

    console.log('\nauth_users table:');
    console.log('  id:', auth_users_id);
    console.log('  auth_user_id:', auth_users_auth_user_id);
    console.log('  yacht_id:', auth_users_yacht_id);

    console.log('\nauth_users_yacht table:');
    console.log('  user_id:', auth_users_yacht_user_id);
    console.log('  yacht_id:', auth_users_yacht_yacht_id);

    console.log('\n🔍 ANALYSIS:');
    console.log('-'.repeat(80));

    // Check get_user_yacht_id() logic
    console.log('\nget_user_yacht_id() function does:');
    console.log('  SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()');
    console.log('\nWhen user logs in:');
    console.log('  auth.uid() returns:', auth_users_auth_user_id);
    console.log('  Looks for: auth_users.auth_user_id =', auth_users_auth_user_id);
    console.log('  Should find yacht_id:', auth_users_yacht_id);

    if (!auth_users_yacht_id) {
      console.log('\n❌ PROBLEM: auth_users.yacht_id is NULL!');
      console.log('   The user exists in auth_users but has no yacht_id assigned');
    } else if (auth_users_yacht_id !== auth_users_yacht_yacht_id) {
      console.log('\n⚠️  WARNING: Mismatched yacht_ids!');
      console.log('   auth_users.yacht_id:', auth_users_yacht_id);
      console.log('   auth_users_yacht.yacht_id:', auth_users_yacht_yacht_id);
    } else {
      console.log('\n✅ Yacht IDs match!');
      console.log('   But get_user_yacht_id() returned NULL...');
      console.log('   This means auth.uid() might not be returning the expected value');
    }
  }

  console.log('\n');
}

debugUser().catch(console.error);
