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

    const roles: Array<'crew' | 'hod' | 'captain' | 'manager'> = ['crew', 'hod', 'captain'];

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
  }

  console.log('========================================');
  console.log('Global Setup: Complete');
  console.log('========================================\n');
}

export default globalSetup;
