/**
 * Playwright Global Setup
 *
 * Runs once before all tests
 */

import * as fs from 'fs';
import * as path from 'path';
import { login, storeAuthState } from './auth';
import { setupMasterDb } from './master-db-setup';

async function globalSetup() {
  console.log('\n========================================');
  console.log('Global Setup: Starting');
  console.log('========================================\n');

  // Ensure test-results directory exists
  const testResultsDir = path.join(process.cwd(), 'test-results');
  fs.mkdirSync(testResultsDir, { recursive: true });
  fs.mkdirSync(path.join(testResultsDir, 'artifacts'), { recursive: true });
  fs.mkdirSync(path.join(testResultsDir, 'screenshots'), { recursive: true });

  // Setup MASTER DB (ensure fleet_registry and user_accounts exist)
  console.log('Setting up MASTER DB...');
  const setupResult = await setupMasterDb();
  if (!setupResult.success) {
    console.error('MASTER DB setup failed:', setupResult.message);
    console.log('Continuing anyway - tests may fail.\n');
  } else {
    console.log('MASTER DB setup complete.\n');
  }

  // Pre-authenticate to speed up tests
  console.log('Pre-authenticating test user...');
  try {
    const tokens = await login();
    storeAuthState(tokens);
    console.log('Authentication successful, token cached.\n');
  } catch (error: any) {
    console.error('Pre-authentication failed:', error.message);
    console.log('Tests will authenticate individually.\n');
  }

  console.log('========================================');
  console.log('Global Setup: Complete');
  console.log('========================================\n');
}

export default globalSetup;
