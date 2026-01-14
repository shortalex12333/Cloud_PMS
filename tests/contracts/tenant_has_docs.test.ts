/**
 * Contract Test: Tenant Has Documents
 *
 * This test FAILS HARD if the tenant database doesn't have sufficient document chunks.
 * Prevents "green tests" while the product returns empty search.
 *
 * Requirements:
 * - document_chunks table must have >= 10 rows for TEST_YACHT
 * - doc_metadata table must have >= 1 row for TEST_YACHT
 */

import { test, expect } from '@playwright/test';
import { getTenantClient } from '../helpers/supabase_tenant';
import { saveArtifact, createEvidenceBundle } from '../helpers/artifacts';
import { ApiClient } from '../helpers/api-client';

const MIN_DOCUMENT_CHUNKS = 10;
const MIN_DOCUMENTS = 1;

test.describe('CONTRACT: Tenant Has Documents', () => {
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
  let tenantClient: ReturnType<typeof getTenantClient>;

  test.beforeAll(async () => {
    tenantClient = getTenantClient();
  });

  test('CRITICAL: document_chunks table has minimum rows', async () => {
    const testName = 'contracts/tenant_has_docs/chunks_exist';

    const { count, error } = await tenantClient
      .from('document_chunks')
      .select('*', { count: 'exact', head: true })
      .eq('yacht_id', yachtId);

    const chunkCount = count ?? 0;

    // Save evidence
    saveArtifact('db_state.json', {
      timestamp: new Date().toISOString(),
      yacht_id: yachtId,
      document_chunks_count: chunkCount,
      minimum_required: MIN_DOCUMENT_CHUNKS,
      error: error?.message || null
    }, testName);

    createEvidenceBundle(testName, {
      dbAfter: { document_chunks_count: chunkCount },
      assertions: [
        {
          name: `document_chunks >= ${MIN_DOCUMENT_CHUNKS}`,
          passed: chunkCount >= MIN_DOCUMENT_CHUNKS,
          message: `Found ${chunkCount} chunks for yacht ${yachtId}`
        }
      ]
    });

    // FAIL HARD if not enough chunks
    expect(
      chunkCount,
      `CRITICAL: Tenant DB must have at least ${MIN_DOCUMENT_CHUNKS} document chunks for yacht ${yachtId}. Found: ${chunkCount}. This means document processing/indexing has not run.`
    ).toBeGreaterThanOrEqual(MIN_DOCUMENT_CHUNKS);
  });

  test('CRITICAL: doc_metadata table has minimum rows', async () => {
    const testName = 'contracts/tenant_has_docs/metadata_exists';

    const { count, error } = await tenantClient
      .from('doc_metadata')
      .select('*', { count: 'exact', head: true })
      .eq('yacht_id', yachtId);

    const docCount = count ?? 0;

    // Save evidence
    saveArtifact('db_state.json', {
      timestamp: new Date().toISOString(),
      yacht_id: yachtId,
      doc_metadata_count: docCount,
      minimum_required: MIN_DOCUMENTS,
      error: error?.message || null
    }, testName);

    createEvidenceBundle(testName, {
      dbAfter: { doc_metadata_count: docCount },
      assertions: [
        {
          name: `doc_metadata >= ${MIN_DOCUMENTS}`,
          passed: docCount >= MIN_DOCUMENTS,
          message: `Found ${docCount} documents for yacht ${yachtId}`
        }
      ]
    });

    // FAIL HARD if no documents
    expect(
      docCount,
      `CRITICAL: Tenant DB must have at least ${MIN_DOCUMENTS} document in doc_metadata for yacht ${yachtId}. Found: ${docCount}. This means no documents have been uploaded.`
    ).toBeGreaterThanOrEqual(MIN_DOCUMENTS);
  });

  test('CRITICAL: search returns results for common queries', async () => {
    const testName = 'contracts/tenant_has_docs/search_returns_results';

    const apiClient = new ApiClient();
    await apiClient.ensureAuth();

    // Test multiple common queries
    const queries = ['manual', 'maintenance', 'generator', 'safety'];
    const results: Array<{ query: string; count: number }> = [];
    let totalResults = 0;

    for (const query of queries) {
      const response = await apiClient.search(query, 10, yachtId);
      const count = response.data?.results?.length || 0;
      results.push({ query, count });
      totalResults += count;
    }

    // Save evidence
    saveArtifact('search_results.json', {
      timestamp: new Date().toISOString(),
      yacht_id: yachtId,
      queries: results,
      total_results: totalResults
    }, testName);

    createEvidenceBundle(testName, {
      response: { queries: results, total_results: totalResults },
      assertions: [
        {
          name: 'At least one query returns results',
          passed: totalResults > 0,
          message: `Total results across ${queries.length} queries: ${totalResults}`
        }
      ]
    });

    // FAIL HARD if all queries return 0 results
    expect(
      totalResults,
      `CRITICAL: Search returned 0 results for ALL common queries (${queries.join(', ')}). This indicates search is broken or no data exists.`
    ).toBeGreaterThan(0);
  });
});
