/**
 * Playwright Global Setup
 *
 * Runs once before all tests
 */

import * as fs from 'fs';
import * as path from 'path';
import { login, storeAuthState } from './auth';
import { setupMasterDb } from './master-db-setup';

// Import multi-role auth for E2E tests
let loginAsRole: any;
let saveStorageState: any;
let Role: any;

try {
  const rolesAuth = require('../e2e/parts/helpers/roles-auth');
  loginAsRole = rolesAuth.loginAsRole;
  saveStorageState = rolesAuth.saveStorageState;
  Role = rolesAuth.Role;
} catch (error) {
  // roles-auth not available (may be running contract tests only)
  console.log('roles-auth helper not found - skipping multi-role setup');
}

async function globalSetup() {
  console.log('\n========================================');
  console.log('Global Setup: Starting');
  console.log('========================================\n');

  // Ensure test-results directory exists
  const testResultsDir = path.join(process.cwd(), 'test-results');
  fs.mkdirSync(testResultsDir, { recursive: true });
  fs.mkdirSync(path.join(testResultsDir, 'artifacts'), { recursive: true });
  fs.mkdirSync(path.join(testResultsDir, 'screenshots'), { recursive: true });

  // Ensure Playwright storage state directory exists
  const storageStateDir = path.join(process.cwd(), '.playwright', 'storage');
  fs.mkdirSync(storageStateDir, { recursive: true });

  // Setup MASTER DB (ensure fleet_registry and user_accounts exist)
  console.log('Setting up MASTER DB...');
  const setupResult = await setupMasterDb();
  if (!setupResult.success) {
    console.error('MASTER DB setup failed:', setupResult.message);
    console.log('Continuing anyway - tests may fail.\n');
  } else {
    console.log('MASTER DB setup complete.\n');
  }

  // Pre-authenticate to speed up tests (legacy single-user auth)
  console.log('Pre-authenticating default test user...');
  try {
    const tokens = await login();
    storeAuthState(tokens);
    console.log('✓ Default authentication successful.\n');
  } catch (error: any) {
    console.error('Pre-authentication failed:', error.message);
    console.log('Tests will authenticate individually.\n');
  }

  // Pre-authenticate multi-role users for E2E tests
  if (loginAsRole && saveStorageState) {
    console.log('Pre-authenticating multi-role users for E2E tests...');

    const roles: Array<'crew' | 'chief_engineer' | 'captain' | 'manager'> = ['crew', 'chief_engineer', 'captain'];

    for (const role of roles) {
      try {
        console.log(`  - Authenticating as ${role.toUpperCase()}...`);
        const authState = await loginAsRole(role);
        saveStorageState(role, authState);
        console.log(`  ✓ ${role.toUpperCase()} authenticated and storage state saved`);
      } catch (error: any) {
        console.error(`  ✗ ${role.toUpperCase()} authentication failed:`, error.message);
      }
    }

    // Manager role is optional
    try {
      console.log('  - Authenticating as MANAGER (optional)...');
      const managerAuthState = await loginAsRole('manager');
      saveStorageState('manager', managerAuthState);
      console.log('  ✓ MANAGER authenticated and storage state saved');
    } catch (error: any) {
      console.log('  ⚠ MANAGER authentication skipped (account may not exist)');
    }

    console.log('Multi-role authentication complete.\n');

    // Seed test part stock using receive_part to ensure on_hand > 0
    // This allows consume_part, transfer_part, write_off_part actions to appear in suggestions
    console.log('Seeding test part stock...');
    try {
      const TEST_PART_ID = process.env.TEST_PART_ID || 'fa10ad48-5f51-41ee-9ef3-c2127e77b06a';
      const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
      const API_BASE_URL = process.env.PLAYWRIGHT_BASE_URL?.replace('app.', 'pipeline-core.int.') || 'https://pipeline-core.int.celeste7.ai';

      // Get captain JWT for receive_part (requires captain/manager role)
      const captainAuthState = await loginAsRole('captain');
      const accessToken = captainAuthState.tokens.accessToken;

      if (!accessToken) {
        throw new Error('Failed to get captain access token');
      }

      // Call action execution endpoint
      // Format: { action, context: {yacht_id}, payload: {action-specific fields} }
      const response = await fetch(`${API_BASE_URL}/v1/actions/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          action: 'receive_part',
          context: {
            yacht_id: TEST_YACHT_ID
          },
          payload: {
            part_id: TEST_PART_ID,
            to_location_id: 'engine_room',
            quantity: 10,
            idempotency_key: `e2e-setup-${Date.now()}`,
            notes: 'E2E test setup - seeding stock'
          }
        })
      });

      if (response.ok) {
        console.log(`  ✓ Test part stock seeded (on_hand += 10)`);
      } else {
        const errorText = await response.text();
        console.log(`  ⚠ Stock seeding failed (${response.status}): ${errorText}`);
        console.log('  Tests may see limited actions due to on_hand = 0');
      }
    } catch (error: any) {
      console.log('  ⚠ Stock seeding error:', error.message);
      console.log('  Tests may see limited actions due to on_hand = 0');
    }
  }

  console.log('========================================');
  console.log('Global Setup: Complete');
  console.log('========================================\n');
}

export default globalSetup;
