import { test } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

const TEST_YACHT_ID = process.env.TEST_YACHT_ID!;
const TEST_USER_ID = process.env.TEST_USER_ID!;

test('assign debug', async () => {
  const apiClient = new ApiClient(process.env.RENDER_API_URL);
  await apiClient.authenticate(
    process.env.TEST_USER_EMAIL!,
    process.env.TEST_USER_PASSWORD!
  );

  // Create test WO first
  const createResp = await apiClient.request('POST', '/v1/actions/execute', {
    action: 'create_work_order',
    context: { yacht_id: TEST_YACHT_ID, user_id: TEST_USER_ID, role: 'engineer' },
    payload: { title: 'Test' }
  });
  const woId = createResp.data.work_order_id;
  console.log('Created WO:', woId);

  // Try to assign
  console.log('\nPayload being sent:');
  const payload = {
    work_order_id: woId,
    assigned_to: TEST_USER_ID
  };
  console.log(JSON.stringify(payload, null, 2));
  
  const assignResp = await apiClient.request('POST', '/v1/actions/execute', {
    action: 'assign_work_order',
    context: { yacht_id: TEST_YACHT_ID, user_id: TEST_USER_ID, role: 'engineer' },
    payload: payload
  });
  
  console.log('\nResponse:', JSON.stringify(assignResp, null, 2));
});
