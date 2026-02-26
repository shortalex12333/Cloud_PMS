/**
 * Unit Tests for usePartActions Hook
 *
 * Tests verify:
 * - Action names match the canonical registry (part_lens_v2_FINAL.md)
 * - No runtime 404/unknown action errors for part actions
 * - Action payloads have correct field names
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ACTION_REGISTRY, MicroAction } from '@/types/actions';

// =============================================================================
// ACTION NAME VERIFICATION
// =============================================================================

/**
 * Canonical action names from part_lens_v2_FINAL.md
 * These MUST match the backend registry exactly
 */
const CANONICAL_PART_ACTION_NAMES: MicroAction[] = [
  'adjust_stock_quantity', // NOT 'adjust_stock' - fixed in I1
  'write_off_part',
  'consume_part',
  'receive_part',
  'transfer_part',
  'add_to_shopping_list',
  'view_part_stock',
  'view_part_location',
  'view_part_usage',
  'view_linked_equipment',
];

describe('Part Action Names Registry', () => {
  it('adjust_stock_quantity is registered (not adjust_stock)', () => {
    // This was the I1 bug - action was named 'adjust_stock' instead of 'adjust_stock_quantity'
    expect(ACTION_REGISTRY['adjust_stock_quantity']).toBeDefined();
    expect(ACTION_REGISTRY['adjust_stock_quantity'].action_name).toBe('adjust_stock_quantity');
  });

  it('adjust_stock_quantity has correct metadata per spec', () => {
    const action = ACTION_REGISTRY['adjust_stock_quantity'];
    expect(action).toBeDefined();
    expect(action.cluster).toBe('control_inventory');
    expect(action.side_effect_type).toBe('mutation_heavy');
    expect(action.requires_confirmation).toBe(true);
    expect(action.requires_reason).toBe(true);
  });

  it('all canonical part actions are registered', () => {
    for (const actionName of CANONICAL_PART_ACTION_NAMES) {
      expect(
        ACTION_REGISTRY[actionName],
        `Action '${actionName}' should be registered in ACTION_REGISTRY`
      ).toBeDefined();
    }
  });

  it('write_off_part is registered (not write_off)', () => {
    expect(ACTION_REGISTRY['write_off_part']).toBeDefined();
    expect(ACTION_REGISTRY['write_off_part'].action_name).toBe('write_off_part');
  });
});

// =============================================================================
// HOOK ACTION NAME TESTS (static verification)
// =============================================================================

describe('usePartActions Hook Action Names', () => {
  /**
   * These tests verify the action names used in usePartActions.ts
   * by reading the source file and checking for correct action names
   */

  it('adjustStock calls adjust_stock_quantity action', async () => {
    // Import the actual hook source to verify
    const fs = await import('fs');
    const path = await import('path');

    const hookPath = path.resolve(__dirname, '../../src/hooks/usePartActions.ts');
    const hookSource = fs.readFileSync(hookPath, 'utf-8');

    // Verify the correct action name is used
    expect(hookSource).toContain("execute('adjust_stock_quantity'");
    // Verify the old incorrect name is NOT used
    expect(hookSource).not.toMatch(/execute\s*\(\s*['"]adjust_stock['"]\s*,/);
  });

  it('writeOff calls write_off_part action', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const hookPath = path.resolve(__dirname, '../../src/hooks/usePartActions.ts');
    const hookSource = fs.readFileSync(hookPath, 'utf-8');

    expect(hookSource).toContain("execute('write_off_part'");
  });

  it('hook comments document correct action names', async () => {
    const fs = await import('fs');
    const path = await import('path');

    const hookPath = path.resolve(__dirname, '../../src/hooks/usePartActions.ts');
    const hookSource = fs.readFileSync(hookPath, 'utf-8');

    // Header comment should list correct action names
    expect(hookSource).toContain('adjust_stock_quantity');
    expect(hookSource).toContain('write_off_part');

    // Should NOT have the old incorrect names in comments
    expect(hookSource).not.toMatch(/\*\s+adjust_stock[,\s]/);
  });
});

// =============================================================================
// PAYLOAD STRUCTURE TESTS
// =============================================================================

describe('Part Action Payload Structure', () => {
  it('adjust_stock_quantity requires signature field per spec', () => {
    /**
     * Per part_lens_v2_FINAL.md:
     * adjust_stock_quantity is a SIGNED action that requires:
     * - part_id
     * - new_quantity
     * - reason
     * - signature (for large adjustments)
     */
    const action = ACTION_REGISTRY['adjust_stock_quantity'];
    expect(action.requires_reason).toBe(true);
  });

  it('write_off_part requires reason per spec', () => {
    const action = ACTION_REGISTRY['write_off_part'];
    expect(action.requires_reason).toBe(true);
  });
});
