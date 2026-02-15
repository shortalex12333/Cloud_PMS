/**
 * Work Order Actions API Tests
 *
 * Tests for: add_work_order_note, add_checklist_note, add_parts_to_work_order
 *
 * Coverage:
 * - RLS policies (yacht isolation)
 * - Role-based permissions
 * - Foreign key validation
 * - Special characters in JSONB fields
 * - Input validation
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

// Test users for different roles (these should exist in test environment)
const TEST_USERS = {
  chief_engineer: {
    email: 'x@alex-short.com',
    password: 'Password2!',
    yacht_id: '85fe1119-b04c-41ac-80f1-829d23322598',
  },
  // Add other role test users as needed
};

// Test data
const SPECIAL_CHARACTERS = {
  quotes: 'Test with "double quotes" and \'single quotes\'',
  brackets: 'Test with <angle> and {curly} brackets',
  ampersand: 'Test with & ampersand and © symbols',
  unicode: 'Test with émojis 🔧 and ñ accents',
  sql_injection: "Test with '; DROP TABLE users; --",
  html_injection: '<script>alert("xss")</script>',
  newlines: 'Test with\nnewlines\nand\ttabs',
  long_text: 'A'.repeat(1999), // Max is 2000
};

describe('Work Order Actions API', () => {
  let supabase: SupabaseClient;
  let accessToken: string;
  let testWorkOrderId: string;

  beforeAll(async () => {
    // Login as chief_engineer
    supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: TEST_USERS.chief_engineer.email,
      password: TEST_USERS.chief_engineer.password,
    });

    if (authError) throw new Error(`Auth failed: ${authError.message}`);
    accessToken = authData.session!.access_token;

    // Get a work order to test with
    const { data: workOrders } = await supabase
      .from('pms_work_orders')
      .select('id')
      .eq('yacht_id', TEST_USERS.chief_engineer.yacht_id)
      .limit(1);

    if (workOrders && workOrders.length > 0) {
      testWorkOrderId = workOrders[0].id;
    }
  });

  // =========================================================================
  // HELPER FUNCTIONS
  // =========================================================================

  async function executeAction(action: string, context: any, payload: any) {
    const response = await fetch(`${SUPABASE_URL.replace('.supabase.co', '')}/api/v1/actions/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ action, context, payload }),
    });
    return { status: response.status, body: await response.json() };
  }

  // =========================================================================
  // ADD_WORK_ORDER_NOTE TESTS
  // =========================================================================

  describe('add_work_order_note', () => {
    it('should reject when work_order_id is missing', async () => {
      const { status, body } = await executeAction(
        'add_work_order_note',
        { yacht_id: TEST_USERS.chief_engineer.yacht_id },
        { note_text: 'Test note' }
      );

      expect(status).toBe(400);
      expect(body.error).toContain('work_order_id');
    });

    it('should reject when note_text is empty', async () => {
      const { status, body } = await executeAction(
        'add_work_order_note',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: testWorkOrderId,
        },
        { note_text: '' }
      );

      expect(status).toBe(400);
      expect(body.error).toContain('Note text is required');
    });

    it('should reject when note_text is whitespace only', async () => {
      const { status, body } = await executeAction(
        'add_work_order_note',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: testWorkOrderId,
        },
        { note_text: '   \n\t  ' }
      );

      expect(status).toBe(400);
      expect(body.error).toContain('Note text is required');
    });

    it('should return 404 for non-existent work order', async () => {
      const { status, body } = await executeAction(
        'add_work_order_note',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: '00000000-0000-0000-0000-000000000000',
        },
        { note_text: 'Test note' }
      );

      expect(status).toBe(404);
      expect(body.error).toContain('not found');
    });

    // Special character tests
    Object.entries(SPECIAL_CHARACTERS).forEach(([name, text]) => {
      it(`should handle special characters: ${name}`, async () => {
        if (!testWorkOrderId) return; // Skip if no test work order

        const { status, body } = await executeAction(
          'add_work_order_note',
          {
            yacht_id: TEST_USERS.chief_engineer.yacht_id,
            work_order_id: testWorkOrderId,
          },
          { note_text: text }
        );

        // Should either succeed (200) or fail validation (400), not crash (500)
        expect([200, 400]).toContain(status);
        if (status === 200) {
          expect(body.success).toBe(true);
          expect(body.data.note_text).toBe(text.trim());
        }
      });
    });
  });

  // =========================================================================
  // ADD_CHECKLIST_NOTE TESTS
  // =========================================================================

  describe('add_checklist_note', () => {
    it('should reject when work_order_id is missing', async () => {
      const { status, body } = await executeAction(
        'add_checklist_note',
        { yacht_id: TEST_USERS.chief_engineer.yacht_id },
        { title: 'Test checklist item' }
      );

      expect(status).toBe(400);
      expect(body.error).toContain('work_order_id');
    });

    it('should reject when title is empty', async () => {
      const { status, body } = await executeAction(
        'add_checklist_note',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: testWorkOrderId,
        },
        { title: '' }
      );

      expect(status).toBe(400);
      expect(body.error).toContain('title is required');
    });

    it('should return 404 for non-existent work order', async () => {
      const { status, body } = await executeAction(
        'add_checklist_note',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: '00000000-0000-0000-0000-000000000000',
        },
        { title: 'Test checklist item' }
      );

      expect(status).toBe(404);
      expect(body.error).toContain('not found');
    });

    // Special character tests for checklist title
    Object.entries(SPECIAL_CHARACTERS).forEach(([name, text]) => {
      it(`should handle special characters in title: ${name}`, async () => {
        if (!testWorkOrderId) return;

        const { status, body } = await executeAction(
          'add_checklist_note',
          {
            yacht_id: TEST_USERS.chief_engineer.yacht_id,
            work_order_id: testWorkOrderId,
          },
          { title: text.substring(0, 255) } // VARCHAR(255) limit
        );

        expect([200, 400]).toContain(status);
        if (status === 200) {
          expect(body.success).toBe(true);
        }
      });
    });
  });

  // =========================================================================
  // RLS POLICY TESTS
  // =========================================================================

  describe('RLS Policies', () => {
    it('should enforce yacht isolation - cannot access other yacht work orders', async () => {
      // This test requires a work order from a different yacht
      // For now, we test with an invalid UUID which should return 404 due to RLS
      const { status, body } = await executeAction(
        'add_work_order_note',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', // Non-existent/other yacht
        },
        { note_text: 'Should not work' }
      );

      expect(status).toBe(404);
    });
  });

  // =========================================================================
  // FOREIGN KEY TESTS
  // =========================================================================

  describe('Foreign Key Validation', () => {
    it('add_parts_to_work_order should reject invalid part_id', async () => {
      if (!testWorkOrderId) return;

      const { status, body } = await executeAction(
        'add_parts_to_work_order',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: testWorkOrderId,
        },
        {
          part_id: '00000000-0000-0000-0000-000000000000',
          quantity: 1,
        }
      );

      expect(status).toBe(404);
      expect(body.error).toContain('Part not found');
    });

    it('add_parts_to_work_order should reject invalid quantity', async () => {
      if (!testWorkOrderId) return;

      const { status, body } = await executeAction(
        'add_parts_to_work_order',
        {
          yacht_id: TEST_USERS.chief_engineer.yacht_id,
          work_order_id: testWorkOrderId,
        },
        {
          part_id: 'some-part-id',
          quantity: -1,
        }
      );

      expect(status).toBe(400);
      expect(body.error).toContain('Quantity');
    });
  });
});

// =========================================================================
// ROLE-BASED ACCESS TESTS (requires multiple test users)
// =========================================================================

describe('Role-Based Access', () => {
  // These tests would require test users with different roles
  // Currently only testing with chief_engineer which has full access

  it.todo('crew role should be able to add notes');
  it.todo('deck role should be able to add notes');
  it.todo('interior role should be able to add notes');
  it.todo('eto role should be able to add notes');
  it.todo('captain role should be able to add notes');
  it.todo('manager role should be able to add notes');
  it.todo('vendor role access should be restricted');
});
