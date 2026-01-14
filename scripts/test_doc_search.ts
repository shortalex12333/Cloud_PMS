/**
 * Test document-specific search to verify RAG pipeline works
 */
import { ApiClient } from '../tests/helpers/api-client';
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';

dotenv.config({ path: '.env.e2e.local' });

async function testDocSearch() {
  console.log('Initializing API client...');
  const apiClient = new ApiClient();
  await apiClient.ensureAuth();

  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

  // Test queries that should hit document chunks
  const queries = [
    'manual',
    'maintenance procedure',
    'safety guidelines',
    'generator operation',
    'pump filter'
  ];

  const results: Record<string, any> = {
    timestamp: new Date().toISOString(),
    yacht_id: yachtId,
    tests: []
  };

  for (const query of queries) {
    console.log(`\n--- Testing query: "${query}" ---`);
    const response = await apiClient.search(query, 10, yachtId);

    const testResult = {
      query,
      status: response.status,
      success: response.data?.success,
      result_count: response.data?.results?.length || 0,
      total_count: response.data?.total_count,
      result_types: response.data?.results?.map((r: any) => r.type) || [],
      has_documents: response.data?.results?.some((r: any) =>
        r.type === 'document' || r.source_table === 'doc_metadata' || r.type === 'doc_metadata'
      ) || false
    };

    results.tests.push(testResult);

    console.log('  Status:', testResult.status);
    console.log('  Results:', testResult.result_count);
    console.log('  Types:', [...new Set(testResult.result_types)]);
    console.log('  Has documents:', testResult.has_documents);
  }

  // Save artifact
  const artifactDir = 'test-results/artifacts/doc_search_tests';
  fs.mkdirSync(artifactDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  fs.writeFileSync(
    path.join(artifactDir, `${timestamp}.json`),
    JSON.stringify(results, null, 2)
  );

  console.log('\n=== SUMMARY ===');
  const passCount = results.tests.filter((t: any) => t.result_count > 0).length;
  console.log(`Queries with results: ${passCount}/${queries.length}`);

  const docsFound = results.tests.filter((t: any) => t.has_documents).length;
  console.log(`Queries returning documents: ${docsFound}/${queries.length}`);

  console.log('\nArtifact saved to:', path.join(artifactDir, `${timestamp}.json`));
}

testDocSearch().catch(console.error);
