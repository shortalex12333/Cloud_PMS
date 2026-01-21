const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY || process.env.TENANT_SUPABASE_SERVICE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

async function checkEmailWatchers() {
  console.log('Querying email_watchers table...');

  const { data: watchers, error } = await supabase
    .from('email_watchers')
    .select('*')
    .limit(10);

  if (error) {
    console.log('Error:', error.message);
    console.log('Full error:', JSON.stringify(error, null, 2));
    return;
  }

  console.log('Email watcher records found:', watchers?.length || 0);
  console.log('\nEmail watchers:');
  console.log(JSON.stringify(watchers, null, 2));

  // Write to evidence file
  fs.writeFileSync(
    '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/OAUTH_email_watchers.json',
    JSON.stringify(watchers, null, 2)
  );
  console.log('\nEvidence written to OAUTH_email_watchers.json');
}

checkEmailWatchers();
