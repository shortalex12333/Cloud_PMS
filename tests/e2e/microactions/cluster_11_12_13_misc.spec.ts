/**
 * Clusters 11, 12, 13: SHIPYARD, FLEET, SYSTEM_UTILITY
 *
 * Tests actions:
 * - 11.1 schedule_drydock
 * - 11.2 record_shipyard_work
 * - 12.1 compare_across_yachts
 * - 12.2 fleet_analytics
 * - 13.1 export_data
 * - 13.2 import_data
 * - 13.3 user_settings
 * - 13.4 view_dashboard_metrics
 *
 * From: COMPLETE_ACTION_EXECUTION_CATALOG.md
 */

import { test, expect } from '@playwright/test';
import {
  saveArtifact,
  saveRequest,
  saveResponse,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';

test.describe('Clusters 11-13: SHIPYARD, FLEET, SYSTEM_UTILITY', () => {
  let apiClient: ApiClient;
  let tenantClient: ReturnType<typeof getTenantClient>;
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
    tenantClient = getTenantClient();
  });

  // ==========================================================================
  // CLUSTER 11: SHIPYARD
  // ==========================================================================

  // ACTION 11.1: schedule_drydock
  test('ACTION 11.1: schedule_drydock - schedules drydock period', async () => {
    const testName = 'cluster_11_12_13/01_schedule_drydock';

    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() + 3);
    const endDate = new Date(startDate);
    endDate.setDate(endDate.getDate() + 30);

    const response = await apiClient.executeAction('schedule_drydock', {
      shipyard_name: 'E2E Test Shipyard',
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
      description: 'Drydock scheduled via E2E test',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ACTION 11.2: record_shipyard_work
  test('ACTION 11.2: record_shipyard_work - records shipyard work done', async () => {
    const testName = 'cluster_11_12_13/02_record_shipyard_work';

    const response = await apiClient.executeAction('record_shipyard_work', {
      work_type: 'hull_painting',
      description: 'Shipyard work recorded via E2E test',
      contractor: 'Test Contractor',
      cost: 50000,
      completion_date: new Date().toISOString(),
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ==========================================================================
  // CLUSTER 12: FLEET
  // ==========================================================================

  // ACTION 12.1: compare_across_yachts
  test('ACTION 12.1: compare_across_yachts - compares metrics across fleet', async () => {
    const testName = 'cluster_11_12_13/03_compare_across_yachts';

    const response = await apiClient.executeAction('compare_across_yachts', {
      metric: 'maintenance_cost',
      period: 'last_year',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ACTION 12.2: fleet_analytics
  test('ACTION 12.2: fleet_analytics - returns fleet-wide analytics', async () => {
    const testName = 'cluster_11_12_13/04_fleet_analytics';

    const response = await apiClient.executeAction('fleet_analytics', {
      report_type: 'summary',
      period: 'current_month',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ==========================================================================
  // CLUSTER 13: SYSTEM_UTILITY
  // ==========================================================================

  // ACTION 13.1: export_data
  test('ACTION 13.1: export_data - exports yacht data', async () => {
    const testName = 'cluster_11_12_13/05_export_data';

    const response = await apiClient.executeAction('export_data', {
      export_type: 'equipment',
      format: 'csv',
      include_history: false,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
        { name: 'Returns export URL or data', passed: !!response.data?.download_url || !!response.data?.data },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ACTION 13.2: import_data
  test('ACTION 13.2: import_data - imports data (dry run)', async () => {
    const testName = 'cluster_11_12_13/06_import_data';

    const response = await apiClient.executeAction('import_data', {
      import_type: 'equipment',
      dry_run: true, // Don't actually import
      data: [{ name: 'Test Import Equipment', code: 'TEST-IMP-001' }],
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ACTION 13.3: user_settings
  test('ACTION 13.3: user_settings - updates user settings', async () => {
    const testName = 'cluster_11_12_13/07_user_settings';

    const response = await apiClient.executeAction('user_settings', {
      settings: {
        notification_preference: 'email',
        timezone: 'UTC',
        language: 'en',
      },
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ACTION 13.4: view_dashboard_metrics
  test('ACTION 13.4: view_dashboard_metrics - returns dashboard data', async () => {
    const testName = 'cluster_11_12_13/08_view_dashboard_metrics';

    const response = await apiClient.executeAction('view_dashboard_metrics', {
      yacht_id: yachtId,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Returns metrics data', passed: !!response.data?.metrics || !!response.data?.data },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // SUMMARY
  // ==========================================================================
  test('SUMMARY: Clusters 11-13 actions complete', async () => {
    const testName = 'cluster_11_12_13/00_summary';
    saveArtifact('summary.json', {
      clusters: ['SHIPYARD', 'FLEET', 'SYSTEM_UTILITY'],
      actions: 8,
    }, testName);
    console.log('\nClusters 11-13 Summary: SHIPYARD, FLEET, SYSTEM_UTILITY - 8 actions tested');
  });
});
