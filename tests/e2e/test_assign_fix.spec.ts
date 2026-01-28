import { test, expect } from '@playwright/test';
import { ApiClient } from '../helpers/api-client';

const TEST_YACHT_ID = process.env.TEST_YACHT_ID!;
const TEST_USER_ID = process.env.TEST_USER_ID!;

test('assign fix', async () => {
  const apiClient = new ApiClient(process.env.RENDER_API_URL);
  await apiClient.authenticate(
    process.env.TEST_USER_EMAIL!,
    process.env.TEST_USER_PASSWORD!
  );

  console.log('TEST_USER_ID:', TEST_USER_ID);
  console.log('TEST_YACHT_ID:', TEST_YACHT_ID);

  // Create test WO first
  const createResp = await apiClient.request('POST', '/v1/actions/execute', {
    action: 'create_work_order',
    context: { yacht_id: TEST_YACHT_ID, user_id: TEST_USER_ID, role: 'engineer' },
    payload: { title: 'Test' }
  });
  const woId = createResp.data.work_order_id;
  
  // Assign with literal string UUID
  const assignResp = await apiClient.request('POST', '/v1/actions/execute', {
    action: 'assign_work_order',
    context: { yacht_id: TEST_YACHT_ID, user_id: TEST_USER_ID, role: 'engineer' },
    payload: { 
      work_order_id: woId,
      assigned_to: "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
    }
  });
  
  console.log('Assign response:', JSON.stringify(assignResp.data, null, 2));
  expect(assignResp.status).toBe(200);
});
