import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

const TEST_YACHT_ID = process.env.TEST_YACHT_ID!;
const TEST_USER_ID = process.env.TEST_USER_ID!;

test('create_work_order - 400 validation test', async () => {
  const apiClient = new ApiClient(process.env.RENDER_API_URL);
  await apiClient.authenticate(
    process.env.TEST_USER_EMAIL!,
    process.env.TEST_USER_PASSWORD!
  );

  // Test: missing title (required field)
  const response = await apiClient.request('POST', '/v1/actions/execute', {
    action: 'create_work_order',
    context: {
      yacht_id: TEST_YACHT_ID,
      user_id: TEST_USER_ID,
      role: 'engineer'
    },
    payload: {
      description: 'No title provided'
    }
  });

  console.log('400 Test Response:', JSON.stringify(response, null, 2));
});
