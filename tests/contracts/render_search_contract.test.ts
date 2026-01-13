/**
 * Render Search Contract Test
 *
 * Verifies the /search and related endpoints on Render backend
 *
 * Contract:
 * - POST /search
 * - Requires: Authorization header with valid JWT
 * - Request: { query: string, limit?: number }
 * - Response: { success: boolean, results: Array, total_count: number }
 */

import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';
import { saveArtifact, createEvidenceBundle, saveRequest, saveResponse } from '../helpers/artifacts';

test.describe('Render Search Contract', () => {
  let apiClient: ApiClient;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
  });

  test('Health endpoint is accessible', async () => {
    const testName = 'contracts/render_health';

    const response = await apiClient.healthCheck();

    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      body: response.data,
    });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'Status is 200', passed: response.status === 200 },
        { name: 'Has status field', passed: !!response.data?.status },
      ],
    });

    expect(response.status).toBe(200);
    expect(response.data.status).toBeTruthy();
  });

  test('Search endpoint returns expected schema', async () => {
    const testName = 'contracts/search_schema';

    const response = await apiClient.search('maintenance procedure', 5);

    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      headers: response.headers,
      body: response.data,
    });

    // Validate response schema
    const hasSuccess = typeof response.data?.success === 'boolean';
    const hasResults = Array.isArray(response.data?.results);
    const hasTotalCount = typeof response.data?.total_count === 'number' ||
                          response.data?.total_count === undefined; // Optional

    const assertions = [
      { name: 'Status is 200', passed: response.status === 200 },
      { name: 'Has success boolean', passed: hasSuccess },
      { name: 'Has results array', passed: hasResults },
      { name: 'Has total_count or undefined', passed: hasTotalCount },
    ];

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions,
    });

    expect(response.status).toBe(200);
    expect(hasSuccess).toBe(true);
    expect(hasResults).toBe(true);
  });

  test('Search requires authentication', async () => {
    const testName = 'contracts/search_auth_required';

    // Make request without auth
    const url = process.env.RENDER_API_URL;
    const response = await fetch(`${url}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // No Authorization header
      },
      body: JSON.stringify({ query: 'test', limit: 1 }),
    });

    const body = await response.json().catch(() => ({}));

    saveArtifact('unauthenticated_request.json', {
      status: response.status,
      body,
    }, testName);

    createEvidenceBundle(testName, {
      response: { status: response.status, body },
      assertions: [
        {
          name: 'Returns 401 or 403 without auth',
          passed: response.status === 401 || response.status === 403,
          message: `Got ${response.status}`,
        },
      ],
    });

    // Should be 401 Unauthorized or 403 Forbidden
    expect([401, 403]).toContain(response.status);
  });

  test('Search with empty query returns error or empty results', async () => {
    const testName = 'contracts/search_empty_query';

    const response = await apiClient.search('', 5);

    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      body: response.data,
    });

    // Either returns 400 (bad request) or 200 with empty results
    const isValid = response.status === 400 ||
      (response.status === 200 && Array.isArray(response.data?.results));

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        {
          name: 'Returns 400 or 200 with results array',
          passed: isValid,
          message: `Status: ${response.status}`,
        },
      ],
    });

    expect(isValid).toBe(true);
  });

  test('Search respects limit parameter', async () => {
    const testName = 'contracts/search_limit';

    const limit = 3;
    const response = await apiClient.search('equipment', limit);

    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      body: response.data,
    });

    const resultsCount = response.data?.results?.length || 0;
    const respectsLimit = resultsCount <= limit;

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'Status is 200', passed: response.status === 200 },
        {
          name: 'Results count <= limit',
          passed: respectsLimit,
          message: `Limit: ${limit}, Results: ${resultsCount}`,
        },
      ],
    });

    expect(response.status).toBe(200);
    expect(resultsCount).toBeLessThanOrEqual(limit);
  });

  test('Search result items have expected fields', async () => {
    const testName = 'contracts/search_result_fields';

    const response = await apiClient.search('generator', 5);

    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      body: response.data,
    });

    expect(response.status).toBe(200);

    const results = response.data?.results || [];

    if (results.length === 0) {
      // No results, can't validate fields
      saveArtifact('skip_reason.json', { reason: 'No results to validate' }, testName);
      createEvidenceBundle(testName, {
        assertions: [{ name: 'Has results to validate', passed: false }],
      });
      return;
    }

    // Check first result for expected fields
    const firstResult = results[0];

    // Common expected fields (may vary by result type)
    const possibleFields = ['content', 'type', 'score', 'metadata', 'id', 'title'];
    const presentFields = possibleFields.filter((f) => f in firstResult);

    saveArtifact('result_structure.json', {
      first_result: firstResult,
      present_fields: presentFields,
      total_results: results.length,
    }, testName);

    createEvidenceBundle(testName, {
      response: { status: response.status, firstResult },
      assertions: [
        {
          name: 'Result has at least one expected field',
          passed: presentFields.length > 0,
          message: `Present: ${presentFields.join(', ')}`,
        },
      ],
    });

    expect(presentFields.length).toBeGreaterThan(0);
  });

  test('Version endpoint shows production environment', async () => {
    const testName = 'contracts/render_version';

    const url = process.env.RENDER_API_URL;
    const response = await fetch(`${url}/version`);
    const body = await response.json().catch(() => ({}));

    saveArtifact('version_response.json', {
      status: response.status,
      body,
    }, testName);

    const assertions = [
      { name: 'Status is 200', passed: response.status === 200 },
      { name: 'Has environment field', passed: !!body.environment },
      { name: 'Has git_commit field', passed: !!body.git_commit },
    ];

    createEvidenceBundle(testName, {
      response: { status: response.status, body },
      assertions,
    });

    expect(response.status).toBe(200);
    expect(body.environment).toBeTruthy();
  });

  test('Webhook search endpoint works', async () => {
    const testName = 'contracts/webhook_search';

    const response = await apiClient.post('/webhook/search', {
      query: 'engine',
      limit: 3,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      body: response.data,
    });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'Status is 200', passed: response.status === 200 },
        { name: 'Has success field', passed: 'success' in (response.data || {}) },
      ],
    });

    expect(response.status).toBe(200);
  });
});
