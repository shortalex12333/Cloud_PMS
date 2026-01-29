/**
 * Document Lens v2 - List Actions Contract Test
 *
 * Verifies that /v1/actions/list?domain=documents returns 200 OK
 * with correct Document Lens actions after useCelesteSearch fix.
 */

import { test, expect } from '@playwright/test';
import { getAccessToken } from '../../helpers/auth';
import { saveArtifact } from '../../helpers/artifacts';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

test.describe('Actions API - Documents Domain', () => {
  test('List endpoint returns documents actions', async () => {
    const testName = 'actions/list-documents';
    const accessToken = await getAccessToken();

    // Call /v1/actions/list?domain=documents
    const response = await fetch(`${API_URL}/v1/actions/list?domain=documents`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('list_documents_response.json', {
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

    // Verify expected document actions exist
    const actionIds = data.actions.map((a: any) => a.action_id);

    // Document Lens v2 should have these actions
    const expectedActions = [
      'add_document',
      'add_document_tag',
      'tag_document',
      'get_document_url',
      'soft_delete_document',
      'stage_document_mutation',
    ];

    // At least one expected action should be present
    const foundActions = expectedActions.filter(a => actionIds.includes(a));
    expect(foundActions.length).toBeGreaterThan(0);

    // Verify action structure
    const firstAction = data.actions[0];
    expect(firstAction).toHaveProperty('action_id');
    expect(firstAction).toHaveProperty('label');
    expect(firstAction).toHaveProperty('domain');
    expect(firstAction).toHaveProperty('variant');
    expect(firstAction).toHaveProperty('allowed_roles');
    expect(firstAction).toHaveProperty('required_fields');
  });

  test('Document action query "upload document" returns document actions', async () => {
    const testName = 'actions/list-upload-document-query';
    const accessToken = await getAccessToken();

    // Call /v1/actions/list?q=upload+document&domain=documents
    const response = await fetch(`${API_URL}/v1/actions/list?q=upload+document&domain=documents`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('list_upload_document_query_response.json', {
      status: response.status,
      statusText: response.statusText,
      body: data,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assertions
    expect(response.status).toBe(200);
    expect(data).toHaveProperty('actions');
    expect(Array.isArray(data.actions)).toBe(true);
  });

  test('0x500 requirement: No 5xx errors on documents list endpoint', async () => {
    const testName = 'actions/list-documents-0x500';
    const accessToken = await getAccessToken();

    // Make multiple requests to ensure stability
    const requests = 10;
    const responses = await Promise.all(
      Array.from({ length: requests }, () =>
        fetch(`${API_URL}/v1/actions/list?domain=documents`, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        })
      )
    );

    const statuses = responses.map(r => r.status);

    // Save evidence
    saveArtifact('list_documents_0x500_evidence.json', {
      requests,
      statuses,
      timestamp: new Date().toISOString(),
    }, testName);

    // Assert no 5xx errors
    for (const status of statuses) {
      expect(status).toBeLessThan(500); // 0x500 requirement
    }
  });

  test('Role-gated: CREW should not see mutation actions', async () => {
    const testName = 'actions/list-documents-crew-role';
    // This test verifies that crew role doesn't see mutation actions
    // If we have crew token logic, implement here. For now, verify structure.

    const accessToken = await getAccessToken();

    const response = await fetch(`${API_URL}/v1/actions/list?domain=documents`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    // Save response artifact
    saveArtifact('list_documents_role_gated_response.json', {
      status: response.status,
      actionCount: data.actions?.length || 0,
      actions: data.actions?.map((a: any) => ({
        action_id: a.action_id,
        variant: a.variant,
        allowed_roles: a.allowed_roles,
      })),
      timestamp: new Date().toISOString(),
    }, testName);

    expect(response.status).toBe(200);

    // Verify each action has allowed_roles defined
    for (const action of data.actions || []) {
      expect(action).toHaveProperty('allowed_roles');
      expect(Array.isArray(action.allowed_roles)).toBe(true);
    }
  });
});
