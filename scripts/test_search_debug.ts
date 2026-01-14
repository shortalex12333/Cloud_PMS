/**
 * Debug script to test search and capture artifacts
 */
import { ApiClient } from '../tests/helpers/api-client';
import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';

dotenv.config({ path: '.env.e2e.local' });

async function testSearch() {
  console.log('Initializing API client...');
  const apiClient = new ApiClient();
  await apiClient.ensureAuth();

  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
  console.log('Using yacht_id:', yachtId);

  // Test search
  console.log('\n--- Testing search endpoint ---');
  const response = await apiClient.search('generator', 10, yachtId);

  // Save artifact
  const artifactDir = 'test-results/artifacts/search_payload';
  fs.mkdirSync(artifactDir, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const artifact = {
    timestamp: new Date().toISOString(),
    request: response.request,
    response: {
      status: response.status,
      body: response.data
    }
  };

  fs.writeFileSync(
    path.join(artifactDir, `${timestamp}.json`),
    JSON.stringify(artifact, null, 2)
  );

  console.log('Status:', response.status);
  console.log('Success:', response.data?.success);
  console.log('Result count:', response.data?.results?.length || 0);
  console.log('Total count:', response.data?.total_count);

  if (response.data?.results?.length > 0) {
    console.log('\nFirst result:', JSON.stringify(response.data.results[0], null, 2));
  } else {
    console.log('\n⚠️ NO RESULTS RETURNED');
  }

  console.log('\nArtifact saved to:', path.join(artifactDir, `${timestamp}.json`));
}

testSearch().catch(console.error);
