/**
 * Playwright Global Setup
 *
 * Runs once before all tests
 */

import * as fs from 'fs';
import * as path from 'path';
import { login, storeAuthState } from './auth';

async function globalSetup() {
  console.log('\n========================================');
  console.log('Global Setup: Starting');
  console.log('========================================\n');

  // Ensure test-results directory exists
  const testResultsDir = path.join(process.cwd(), 'test-results');
  fs.mkdirSync(testResultsDir, { recursive: true });
  fs.mkdirSync(path.join(testResultsDir, 'artifacts'), { recursive: true });
  fs.mkdirSync(path.join(testResultsDir, 'screenshots'), { recursive: true });

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
