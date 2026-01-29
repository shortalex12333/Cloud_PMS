/**
 * Shopping List Lens - API Health Contract Test
 *
 * Verifies that the Actions API health endpoint returns 200 OK.
 * This is a fast smoke test to ensure the API is accessible.
 */

import { test, expect } from '@playwright/test';
import { saveArtifact } from '../../helpers/artifacts';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://celeste-pipeline-v1.onrender.com';

test.describe('Actions API - Health Check', () => {
  test('Health endpoint returns 200 OK', async () => {
    const testName = 'actions/api-health';

    // Call health endpoint
    const response = await fetch(`${API_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('health_response.json', {
      status: response.status,
      statusText: response.statusText,
      body: data,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data.status).toBe('healthy');
    expect(data).toHaveProperty('handlers_loaded');
    expect(data).toHaveProperty('total_handlers');

    // Ensure Shopping List handlers are loaded
    expect(data.handlers_loaded).toBeGreaterThanOrEqual(5); // At least 5 shopping list actions
    expect(data.total_handlers).toBeGreaterThanOrEqual(data.handlers_loaded);
  });

  test('V1 Actions health endpoint returns 200 OK', async () => {
    const testName = 'actions/api-health-v1';

    // Call v1/actions/health endpoint
    const response = await fetch(`${API_URL}/v1/actions/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('health_v1_response.json', {
      status: response.status,
      statusText: response.statusText,
      body: data,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data.status).toBe('healthy');
  });

  test('0×500 requirement: No 5xx errors on health check', async () => {
    const testName = 'actions/api-health-0x500';

    // Make multiple health check requests to ensure stability
    const requests = 5;
    const responses = await Promise.all(
      Array.from({ length: requests }, () =>
        fetch(`${API_URL}/health`)
      )
    );

    const statuses = responses.map(r => r.status);

    // Save evidence
    saveArtifact('health_0x500_evidence.json', {
      requests,
      statuses,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assert no 5xx errors
    for (const status of statuses) {
      expect(status).toBeLessThan(500); // 0×500 requirement: no 5xx errors
    }
  });
});
