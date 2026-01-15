/**
 * Integration Test Setup
 *
 * Provides utilities for integration tests that connect to real Supabase.
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Test environment configuration
export const TEST_CONFIG = {
  SUPABASE_URL: 'https://vzsohavtuotocgrfkfyd.supabase.co',
  SUPABASE_SERVICE_KEY: process.env.SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY',
  TEST_YACHT_ID: '85fe1119-b04c-41ac-80f1-829d23322598',
  TEST_USER_ID: '00000000-0000-0000-0000-000000000001', // Test user UUID
};

// Singleton Supabase client for tests
let testClient: SupabaseClient | null = null;

/**
 * Get the test Supabase client (singleton)
 */
export function getTestClient(): SupabaseClient {
  if (!testClient) {
    testClient = createClient(
      TEST_CONFIG.SUPABASE_URL,
      TEST_CONFIG.SUPABASE_SERVICE_KEY
    );
  }
  return testClient;
}

/**
 * Clean up test data created during tests
 */
export async function cleanupTestData(
  tableName: string,
  ids: string[]
): Promise<void> {
  if (ids.length === 0) return;

  const client = getTestClient();
  await client.from(tableName).delete().in('id', ids);
}

/**
 * Generate a test-specific UUID (for isolation)
 */
export function generateTestId(): string {
  return crypto.randomUUID();
}

/**
 * Wait for async operations (used in tests)
 */
export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Test user context for integration tests
 */
export const TEST_USER_CONTEXT = {
  user_id: TEST_CONFIG.TEST_USER_ID,
  yacht_id: TEST_CONFIG.TEST_YACHT_ID,
  role: 'Engineer',
};

/**
 * Test user context for manager role
 */
export const TEST_MANAGER_CONTEXT = {
  user_id: TEST_CONFIG.TEST_USER_ID,
  yacht_id: TEST_CONFIG.TEST_YACHT_ID,
  role: 'Manager',
};
