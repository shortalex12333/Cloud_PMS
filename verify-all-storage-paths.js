#!/usr/bin/env node

const SUPABASE_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

async function verifyAll() {
  console.log('='.repeat(80));
  console.log('VERIFYING ALL 2,699 STORAGE PATHS');
  console.log('='.repeat(80));

  // Fetch ALL doc_metadata records
  console.log('\nFetching all doc_metadata records...');

  let allDocs = [];
  let offset = 0;
  const limit = 1000;

  while (true) {
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/doc_metadata?select=id,storage_path&limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${SERVICE_KEY}`,
          'apikey': SERVICE_KEY,
        }
      }
    );

    const docs = await response.json();
    if (docs.length === 0) break;

    allDocs = allDocs.concat(docs);
    offset += limit;

    process.stdout.write(`\rFetched ${allDocs.length} records...`);
  }

  console.log(`\n✅ Fetched ${allDocs.length} total documents\n`);

  // Now verify each one
  console.log('Verifying each storage path (this will take a few minutes)...\n');

  const results = {
    exists: [],
    missing: [],
    errors: []
  };

  for (let i = 0; i < allDocs.length; i++) {
    const doc = allDocs[i];
    let path = doc.storage_path;

    // Strip "documents/" prefix
    if (path.startsWith('documents/')) {
      path = path.substring('documents/'.length);
    }

    // Try to create signed URL (fastest way to check existence)
    try {
      const response = await fetch(
        `${SUPABASE_URL}/storage/v1/object/sign/documents/${path}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${SERVICE_KEY}`,
            'apikey': SERVICE_KEY,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ expiresIn: 60 })
        }
      );

      if (response.ok) {
        results.exists.push(doc.id);
      } else {
        results.missing.push({ id: doc.id, path: doc.storage_path });
      }
    } catch (error) {
      results.errors.push({ id: doc.id, path: doc.storage_path, error: error.message });
    }

    // Progress indicator
    if ((i + 1) % 100 === 0 || i === allDocs.length - 1) {
      const pct = ((i + 1) / allDocs.length * 100).toFixed(1);
      process.stdout.write(`\r[${pct}%] Checked ${i + 1}/${allDocs.length} - ✅ ${results.exists.length} exist, ❌ ${results.missing.length} missing`);
    }
  }

  console.log('\n\n' + '='.repeat(80));
  console.log('RESULTS');
  console.log('='.repeat(80));

  const totalChecked = results.exists.length + results.missing.length + results.errors.length;
  const successRate = (results.exists.length / totalChecked * 100).toFixed(1);

  console.log(`\nTotal documents: ${totalChecked}`);
  console.log(`✅ Files exist: ${results.exists.length} (${successRate}%)`);
  console.log(`❌ Files missing: ${results.missing.length} (${(100 - successRate).toFixed(1)}%)`);
  console.log(`⚠️  Errors: ${results.errors.length}`);

  if (results.missing.length > 0) {
    console.log('\n\nSample of missing files (first 20):');
    console.log('-'.repeat(80));

    results.missing.slice(0, 20).forEach((item, i) => {
      console.log(`${i + 1}. ${item.path.substring(0, 100)}...`);
    });

    // Analyze patterns in missing files
    console.log('\n\nAnalyzing patterns in missing files...');
    const patterns = {};

    results.missing.forEach(item => {
      const match = item.path.match(/documents\/[^/]+\/([^/]+)\//);
      if (match) {
        const category = match[1];
        patterns[category] = (patterns[category] || 0) + 1;
      }
    });

    console.log('\nMissing files by category:');
    Object.entries(patterns)
      .sort((a, b) => b[1] - a[1])
      .forEach(([cat, count]) => {
        console.log(`  ${cat}: ${count} missing`);
      });
  }

  // Save results to file
  const fs = require('fs');
  const outputFile = 'storage-verification-results.json';

  fs.writeFileSync(outputFile, JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: {
      total: totalChecked,
      exists: results.exists.length,
      missing: results.missing.length,
      errors: results.errors.length,
      successRate: successRate + '%'
    },
    missingFiles: results.missing,
    errors: results.errors
  }, null, 2));

  console.log(`\n\n📄 Full results saved to: ${outputFile}`);
  console.log('='.repeat(80));
}

verifyAll().catch(console.error);
