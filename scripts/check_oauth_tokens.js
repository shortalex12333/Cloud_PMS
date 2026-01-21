const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY || process.env.TENANT_SUPABASE_SERVICE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

async function checkTokens() {
  console.log('Querying auth_microsoft_tokens table...');

  const { data: tokens, error } = await supabase
    .from('auth_microsoft_tokens')
    .select('*')
    .limit(10);

  if (error) {
    console.log('Error:', error.message);
    console.log('Full error:', JSON.stringify(error, null, 2));
    return;
  }

  console.log('Token records found:', tokens?.length || 0);

  const sanitized = (tokens || []).map(t => ({
    id: t.id,
    user_id: t.user_id,
    yacht_id: t.yacht_id,
    provider: t.provider,
    token_purpose: t.token_purpose,
    has_access_token: !!(t.microsoft_access_token || t.access_token),
    has_refresh_token: !!(t.microsoft_refresh_token || t.refresh_token),
    expires_at: t.token_expires_at || t.expires_at,
    is_revoked: t.is_revoked,
    created_at: t.created_at,
  }));

  console.log('\nSanitized tokens:');
  console.log(JSON.stringify(sanitized, null, 2));

  // Write to evidence file
  fs.writeFileSync(
    '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/OAUTH_03_db_tokens_select.json',
    JSON.stringify(sanitized, null, 2)
  );
  console.log('\nEvidence written to OAUTH_03_db_tokens_select.json');
}

checkTokens();
