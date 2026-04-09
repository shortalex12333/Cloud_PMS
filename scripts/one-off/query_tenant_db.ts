/**
 * Query tenant DB to verify document chunks exist
 */
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { getTenantClient } from '../tests/helpers/supabase_tenant';

dotenv.config({ path: '.env.e2e.local' });

async function queryTenantDb() {
  console.log('Connecting to tenant DB...');
  const tenant = getTenantClient();

  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
  console.log('Test yacht_id:', yachtId);

  const results: Record<string, any> = {
    timestamp: new Date().toISOString(),
    yacht_id_tested: yachtId,
    queries: {}
  };

  // 1. Count all document_chunks
  console.log('\n--- Query 1: Total document_chunks ---');
  const { count: totalChunks, error: err1 } = await tenant
    .from('document_chunks')
    .select('*', { count: 'exact', head: true });

  results.queries.total_document_chunks = totalChunks ?? 0;
  console.log('Total document_chunks:', totalChunks ?? 0, err1 ? `Error: ${err1.message}` : '');

  // 2. Count document_chunks for test yacht
  console.log('\n--- Query 2: document_chunks for yacht_id ---');
  const { count: yachtChunks, error: err2 } = await tenant
    .from('document_chunks')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', yachtId);

  results.queries.yacht_document_chunks = yachtChunks ?? 0;
  console.log(`Chunks for yacht ${yachtId}:`, yachtChunks ?? 0, err2 ? `Error: ${err2.message}` : '');

  // 3. Distinct yacht_ids in document_chunks
  console.log('\n--- Query 3: Distinct yacht_ids in document_chunks ---');
  const { data: distinctYachts, error: err3 } = await tenant
    .from('document_chunks')
    .select('yacht_id')
    .limit(50);

  const uniqueYachts = distinctYachts ? [...new Set(distinctYachts.map(r => r.yacht_id))] : [];
  results.queries.distinct_yacht_ids = uniqueYachts;
  console.log('Distinct yacht_ids:', uniqueYachts, err3 ? `Error: ${err3.message}` : '');

  // 4. Count doc_metadata
  console.log('\n--- Query 4: Total doc_metadata ---');
  const { count: totalDocs, error: err4 } = await tenant
    .from('doc_metadata')
    .select('*', { count: 'exact', head: true });

  results.queries.total_doc_metadata = totalDocs ?? 0;
  console.log('Total doc_metadata:', totalDocs ?? 0, err4 ? `Error: ${err4.message}` : '');

  // 5. Count doc_metadata for test yacht
  console.log('\n--- Query 5: doc_metadata for yacht_id ---');
  const { count: yachtDocs, error: err5 } = await tenant
    .from('doc_metadata')
    .select('*', { count: 'exact', head: true })
    .eq('yacht_id', yachtId);

  results.queries.yacht_doc_metadata = yachtDocs ?? 0;
  console.log(`Docs for yacht ${yachtId}:`, yachtDocs ?? 0, err5 ? `Error: ${err5.message}` : '');

  // 6. Sample chunks
  console.log('\n--- Query 6: Sample document_chunks ---');
  const { data: sampleChunks, error: err6 } = await tenant
    .from('document_chunks')
    .select('id, yacht_id, doc_id, chunk_index, content')
    .limit(5);

  results.queries.sample_chunks = sampleChunks?.map(c => ({
    id: c.id,
    yacht_id: c.yacht_id,
    doc_id: c.doc_id,
    chunk_index: c.chunk_index,
    content_preview: c.content?.substring(0, 100) + '...'
  })) || [];
  console.log('Sample chunks:', results.queries.sample_chunks.length);

  // Save results
  const artifactDir = 'test-results/artifacts/search_db_truth';
  fs.mkdirSync(artifactDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  fs.writeFileSync(
    path.join(artifactDir, `${timestamp}.json`),
    JSON.stringify(results, null, 2)
  );

  console.log('\n=== SUMMARY ===');
  console.log('Total document_chunks:', results.queries.total_document_chunks);
  console.log('Chunks for test yacht:', results.queries.yacht_document_chunks);
  console.log('Total doc_metadata:', results.queries.total_doc_metadata);
  console.log('Docs for test yacht:', results.queries.yacht_doc_metadata);
  console.log('Distinct yacht_ids:', results.queries.distinct_yacht_ids);
  console.log('\nArtifact saved to:', path.join(artifactDir, `${timestamp}.json`));

  // Diagnosis
  if (results.queries.total_document_chunks === 0) {
    console.log('\n⚠️ ROOT CAUSE: NO DOCUMENT CHUNKS IN TENANT DB');
    console.log('   Documents have not been processed/chunked.');
  } else if (results.queries.yacht_document_chunks === 0) {
    console.log('\n⚠️ ROOT CAUSE: YACHT_ID MISMATCH');
    console.log('   Chunks exist but not for test yacht_id:', yachtId);
    console.log('   Chunks exist for yacht_ids:', results.queries.distinct_yacht_ids);
  } else {
    console.log('\n✅ Document chunks exist for test yacht');
  }
}

queryTenantDb().catch(console.error);
