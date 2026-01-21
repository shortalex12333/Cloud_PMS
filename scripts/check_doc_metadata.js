const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');

const TENANT_SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

if (!TENANT_SERVICE_KEY) {
  console.log('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

async function checkDocMetadata() {
  console.log('=== Checking doc_metadata table ===\n');

  const { data: docs, error, count } = await supabase
    .from('doc_metadata')
    .select('*', { count: 'exact' })
    .eq('yacht_id', '85fe1119-b04c-41ac-80f1-829d23322598')
    .limit(10);

  if (error) {
    console.log('Error:', error.message);
    // Try documents table instead
    const { data: altDocs, error: altError } = await supabase
      .from('documents')
      .select('*')
      .eq('yacht_id', '85fe1119-b04c-41ac-80f1-829d23322598')
      .limit(10);

    if (altDocs) {
      console.log('Found documents table instead');
      console.log('Sample:', JSON.stringify(altDocs[0], null, 2));
    }
    return;
  }

  console.log('Total doc_metadata records for yacht:', count);
  console.log('\nSample documents:');
  docs?.forEach(d => {
    console.log(`  ID: ${d.id}`);
    console.log(`  Filename: ${d.filename}`);
    console.log(`  Storage Path: ${d.storage_path}`);
    console.log(`  Content Type: ${d.content_type}`);
    console.log('  ---');
  });

  // Write evidence
  fs.writeFileSync(
    '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/verification_handoff/evidence/DOC_metadata_sample.json',
    JSON.stringify(docs?.slice(0, 5), null, 2)
  );
  console.log('\nEvidence written to DOC_metadata_sample.json');
}

checkDocMetadata();
