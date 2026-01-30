/**
 * Shopping List Lens - List Actions Contract Test
 *
 * Verifies that /v1/actions/list?domain=shopping_list returns 200 OK
 * with correct Shopping List actions.
 */

import { test, expect } from '@playwright/test';
import { getAccessToken } from '../../helpers/auth';
import { saveArtifact } from '../../helpers/artifacts';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

test.describe('Actions API - Shopping List Domain', () => {
  test('List endpoint returns shopping_list actions', async () => {
    const testName = 'actions/list-shopping-list';
    const accessToken = await getAccessToken();

    // Call /v1/actions/list?domain=shopping_list
    const response = await fetch(`${API_URL}/v1/actions/list?domain=shopping_list`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('list_shopping_list_response.json', {
      status: response.status,
      statusText: response.statusText,
      body: data,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data).toHaveProperty('actions');
    expect(Array.isArray(data.actions)).toBe(true);
    expect(data.actions.length).toBeGreaterThan(0);

    // Verify expected actions exist
    const actionIds = data.actions.map((a: any) => a.action_id);
    expect(actionIds).toContain('create_shopping_list_item');
    expect(actionIds).toContain('approve_shopping_list_item');
    expect(actionIds).toContain('reject_shopping_list_item');
    // Note: promote_candidate_to_part pending backend implementation

    // Verify action structure
    const firstAction = data.actions[0];
    expect(firstAction).toHaveProperty('action_id');
    expect(firstAction).toHaveProperty('label');
    expect(firstAction).toHaveProperty('domain');
    expect(firstAction).toHaveProperty('variant');
    expect(firstAction).toHaveProperty('allowed_roles');
    expect(firstAction).toHaveProperty('required_fields');

    // Verify domain is shopping_list
    for (const action of data.actions) {
      expect(action.domain).toBe('shopping_list');
    }
  });

  test('List endpoint with no domain returns all actions (including shopping_list)', async () => {
    const testName = 'actions/list-all';
    const accessToken = await getAccessToken();

    // Call /v1/actions/list (no domain filter)
    const response = await fetch(`${API_URL}/v1/actions/list`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('list_all_response.json', {
      status: response.status,
      statusText: response.statusText,
      actionCount: data.actions?.length || 0,
      domains: [...new Set(data.actions?.map((a: any) => a.domain) || [])],
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data).toHaveProperty('actions');
    expect(Array.isArray(data.actions)).toBe(true);

    // Verify shopping_list domain is included
    const domains = data.actions.map((a: any) => a.domain);
    expect(domains).toContain('shopping_list');

    // Verify at least 4 shopping_list actions
    const shoppingListActions = data.actions.filter((a: any) => a.domain === 'shopping_list');
    expect(shoppingListActions.length).toBeGreaterThanOrEqual(4);
  });

  test('0×500 requirement: No 5xx errors on list endpoint', async () => {
    const testName = 'actions/list-0x500';
    const accessToken = await getAccessToken();

    // Make multiple requests to ensure stability
    const requests = 10;
    const responses = await Promise.all(
      Array.from({ length: requests }, () =>
        fetch(`${API_URL}/v1/actions/list?domain=shopping_list`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        })
      )
    );

    const statuses = responses.map(r => r.status);

    // Save evidence
    saveArtifact('list_0x500_evidence.json', {
      requests,
      statuses,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assert no 5xx errors
    for (const status of statuses) {
      expect(status).toBeLessThan(500); // 0×500 requirement
    }
  });

  test('Unauthorized request returns 401 or 403 (not 5xx)', async () => {
    const testName = 'actions/list-unauthorized';

    // Call without auth header
    const response = await fetch(`${API_URL}/v1/actions/list?domain=shopping_list`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const status = response.status;

    // Save evidence
    saveArtifact('list_unauthorized_response.json', {
      status,
      statusText: response.statusText,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assert 4xx error (401 or 403), not 5xx
    expect(status).toBeGreaterThanOrEqual(400);
    expect(status).toBeLessThan(500); // Not a server error
  });
});
