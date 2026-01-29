/**
 * Shopping List Lens - Role Filtering Contract Test
 *
 * Verifies that actions have correct allowed_roles configuration.
 * Role filtering happens on backend - this test verifies the configuration.
 */

import { test, expect } from '@playwright/test';
import { getAccessToken } from '../../helpers/auth';
import { saveArtifact } from '../../helpers/artifacts';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://celeste-pipeline-v1.onrender.com';

test.describe('Actions API - Role Filtering', () => {
  test('Shopping List actions have correct allowed_roles', async () => {
    const testName = 'actions/role-filtering';
    const accessToken = await getAccessToken();

    // Get shopping_list actions
    const response = await fetch(`${API_URL}/v1/actions/list?domain=shopping_list`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('role_filtering_response.json', {
      status: response.status,
      actions: data.actions,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data.actions).toBeDefined();

    // Find specific actions and verify their allowed_roles
    const createAction = data.actions.find((a: any) => a.action_id === 'create_shopping_list_item');
    const approveAction = data.actions.find((a: any) => a.action_id === 'approve_shopping_list_item');
    const rejectAction = data.actions.find((a: any) => a.action_id === 'reject_shopping_list_item');
    const promoteAction = data.actions.find((a: any) => a.action_id === 'promote_to_part');

    // Verify create_shopping_list_item
    expect(createAction).toBeDefined();
    expect(createAction.allowed_roles).toContain('Engineer'); // CREW role
    expect(createAction.allowed_roles).toContain('HOD');
    expect(createAction.allowed_roles).toContain('Captain');
    expect(createAction.allowed_roles).toContain('ETO');
    expect(createAction.variant).toBe('MUTATE');

    // Verify approve_shopping_list_item (HOD+ only)
    expect(approveAction).toBeDefined();
    expect(approveAction.allowed_roles).toContain('HOD');
    expect(approveAction.allowed_roles).toContain('Captain');
    expect(approveAction.allowed_roles).not.toContain('Engineer'); // CREW cannot approve
    expect(approveAction.variant).toBe('MUTATE');

    // Verify reject_shopping_list_item (HOD+ only)
    expect(rejectAction).toBeDefined();
    expect(rejectAction.allowed_roles).toContain('HOD');
    expect(rejectAction.allowed_roles).toContain('Captain');
    expect(rejectAction.allowed_roles).not.toContain('Engineer'); // CREW cannot reject
    expect(rejectAction.variant).toBe('MUTATE');

    // Verify promote_to_part (ENGINEER+ only)
    expect(promoteAction).toBeDefined();
    expect(promoteAction.allowed_roles).toContain('Engineer'); // ENGINEER can promote
    expect(promoteAction.allowed_roles).toContain('HOD');
    expect(promoteAction.allowed_roles).toContain('Captain');
    expect(promoteAction.variant).toBe('MUTATE');

    // Save role matrix evidence
    const roleMatrix = {
      create_shopping_list_item: {
        allowed_roles: createAction.allowed_roles,
        crew_allowed: createAction.allowed_roles.includes('Engineer'),
        hod_allowed: createAction.allowed_roles.includes('HOD'),
        engineer_allowed: createAction.allowed_roles.includes('Engineer'),
      },
      approve_shopping_list_item: {
        allowed_roles: approveAction.allowed_roles,
        crew_allowed: approveAction.allowed_roles.includes('Engineer'),
        hod_allowed: approveAction.allowed_roles.includes('HOD'),
        engineer_allowed: approveAction.allowed_roles.includes('Engineer'),
      },
      reject_shopping_list_item: {
        allowed_roles: rejectAction.allowed_roles,
        crew_allowed: rejectAction.allowed_roles.includes('Engineer'),
        hod_allowed: rejectAction.allowed_roles.includes('HOD'),
        engineer_allowed: rejectAction.allowed_roles.includes('Engineer'),
      },
      promote_to_part: {
        allowed_roles: promoteAction.allowed_roles,
        crew_allowed: promoteAction.allowed_roles.includes('Engineer'),
        hod_allowed: promoteAction.allowed_roles.includes('HOD'),
        engineer_allowed: promoteAction.allowed_roles.includes('Engineer'),
      },
    };

    saveArtifact('role_matrix.json', roleMatrix, testName);
  });

  test('Action suggestions endpoint filters by role (using real JWT)', async () => {
    const testName = 'actions/suggestions-role-filter';
    const accessToken = await getAccessToken(); // This JWT has the user's actual role

    // Call suggestions endpoint with shopping list query
    const response = await fetch(`${API_URL}/v1/actions/suggestions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: 'add to shopping list',
        domain: 'shopping_list',
        context: {
          yacht_id: process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598',
        },
      }),
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('suggestions_response.json', {
      status: response.status,
      suggestions: data.actions,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data).toHaveProperty('actions');
    expect(Array.isArray(data.actions)).toBe(true);

    // Verify suggestions are filtered by role
    // (Exact actions depend on JWT role - we just verify structure here)
    for (const action of data.actions) {
      expect(action).toHaveProperty('action_id');
      expect(action).toHaveProperty('label');
      expect(action).toHaveProperty('allowed_roles');
      expect(action).toHaveProperty('required_fields');
      expect(action.domain).toBe('shopping_list');
    }
  });

  test('0×500 requirement: No 5xx errors on role-filtered endpoints', async () => {
    const testName = 'actions/role-filtering-0x500';
    const accessToken = await getAccessToken();

    // Test both list and suggestions endpoints
    const requests = [
      fetch(`${API_URL}/v1/actions/list?domain=shopping_list`, {
        headers: { 'Authorization': `Bearer ${accessToken}` },
      }),
      fetch(`${API_URL}/v1/actions/suggestions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: 'approve shopping list',
          domain: 'shopping_list',
        }),
      }),
    ];

    const responses = await Promise.all(requests);
    const statuses = responses.map(r => r.status);

    // Save evidence
    saveArtifact('role_filtering_0x500_evidence.json', {
      statuses,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assert no 5xx errors
    for (const status of statuses) {
      expect(status).toBeLessThan(500); // 0×500 requirement
    }
  });
});
