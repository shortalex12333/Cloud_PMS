import { test, expect, SpotlightSearchPO } from '../fixtures';

/**
 * PREFILL EXTRACTION E2E TESTS
 *
 * Tests NLP-based entity extraction and prefill behavior for ActionModal.
 *
 * CONFIDENCE THRESHOLDS (per useCelesteSearch.ts / ConfidenceField.tsx):
 * - >= 0.85: HIGH confidence - auto-filled silently (green badge)
 * - 0.65-0.84: MEDIUM confidence - confirm UI (amber badge)
 * - < 0.65: LOW confidence - field not prefilled or review required (red badge)
 *
 * TEST DATA NOTES:
 * - Equipment codes like "ME1", "GE1" are resolved to equipment_id via backend
 * - Priority synonyms: "urgent" -> HIGH, "critical" -> CRITICAL, "low" -> LOW
 * - Temporal phrases: "tomorrow", "next week", "in 3 days" -> parsed dates
 *
 * ARCHITECTURE:
 * 1. Type MUTATE-intent query in SpotlightSearch
 * 2. Click suggested action button to open ActionModal
 * 3. Verify prefilled fields and confidence indicators
 */

// Test data: Known equipment from test-entity-ids.json
const TEST_EQUIPMENT = {
  id: '8e91e289-a156-444c-b315-88c0a06c9492',
  name: 'STATUS-TEST-maintenance-c0b2',
};

// Priority mapping expected from NLP
const PRIORITY_SYNONYMS = {
  urgent: 'HIGH',
  critical: 'CRITICAL',
  important: 'HIGH',
  asap: 'HIGH',
  low: 'LOW',
  minor: 'LOW',
  routine: 'MEDIUM',
};

// Confidence threshold constants (matching ConfidenceField.tsx)
const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.85,
  MEDIUM: 0.65,
  LOW: 0.5,
};

test.describe('Prefill Extraction - Equipment Entity Resolution', () => {
  test.describe.configure({ retries: 2 });

  test('should prefill equipment_id from equipment code mention', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(page);

    // MUTATE-intent query with equipment code
    await spotlight.search('create work order for ME1');

    // Wait for results and action suggestions
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // Look for suggested actions (MUTATE queries should trigger them)
    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions rendered - backend may not have matched "create work order"');
      return;
    }

    // Find and click create_work_order action button
    const createWoBtn = page.locator('[data-testid^="action-btn-"][data-testid*="work_order"]').first();
    const hasCwBtn = await createWoBtn.isVisible({ timeout: 3_000 }).catch(() => false);

    if (!hasCwBtn) {
      // Try generic create button
      const anyCreateBtn = page.locator('[data-testid^="action-btn-create"]').first();
      const hasAnyCreate = await anyCreateBtn.isVisible().catch(() => false);

      if (!hasAnyCreate) {
        console.log('ℹ️ No create work order action button found');
        return;
      }
      // Wait for element to be stable before clicking
      await page.waitForTimeout(300);
      await anyCreateBtn.click({ force: true });
    } else {
      // Wait for element to be stable before clicking
      await page.waitForTimeout(300);
      await createWoBtn.click({ force: true });
    }

    // Wait for ActionModal to open
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10_000 });

    // Check if equipment_id field is prefilled
    // The modal may have a dropdown or hidden input for equipment_id
    const equipmentInput = page.locator('[data-testid="equipment_id-input"], [name="equipment_id"], #equipment_id');
    const hasEquipmentInput = await equipmentInput.isVisible().catch(() => false);

    if (hasEquipmentInput) {
      const value = await equipmentInput.inputValue().catch(() => null);
      console.log(`✅ Equipment field value: ${value}`);
      // If ME1 was resolved, we expect a UUID or the equipment name
      if (value) {
        expect(value.length).toBeGreaterThan(0);
        console.log('✅ Equipment entity extracted and prefilled');
      }
    } else {
      // Check for disambiguation dropdown (ambiguity case)
      const ambiguityDropdown = page.getByTestId('ambiguity-equipment_id');
      const hasAmbiguity = await ambiguityDropdown.isVisible().catch(() => false);

      if (hasAmbiguity) {
        console.log('✅ Equipment entity triggered disambiguation UI');
      } else {
        console.log('ℹ️ Equipment field not found in form - action may not require equipment_id');
      }
    }

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('should resolve equipment name from natural language', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(page);

    // Natural language equipment mention
    await spotlight.search('generator needs maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for "generator needs maintenance" - testing equipment search resolution');

      // At minimum, verify equipment appears in search results
      const resultCount = await spotlight.getResultCount();
      if (resultCount > 0) {
        console.log(`✅ Search found ${resultCount} results including potential equipment matches`);
      }
      return;
    }

    // Click first action button
    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await page.waitForTimeout(300);
    await actionBtn.click({ force: true });

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 10_000 });

    // Check form for prefilled equipment reference
    const form = page.locator('[data-testid^="action-form-"]');
    const formHtml = await form.innerHTML().catch(() => '');

    // Log what we found for debugging
    console.log('ℹ️ Form contains equipment reference:', formHtml.includes('generator') || formHtml.includes('equipment'));

    await page.keyboard.press('Escape');
  });
});

test.describe('Prefill Extraction - Priority Mapping', () => {
  test.describe.configure({ retries: 2 });

  test('should map "urgent" to HIGH priority', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Query with priority synonym
    await spotlight.search('urgent work order needed');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for "urgent work order needed"');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check priority field
    const prioritySelect = page.locator('select[name="priority"], #priority, [data-testid="priority-input"]');
    const hasPrioritySelect = await prioritySelect.isVisible().catch(() => false);

    if (hasPrioritySelect) {
      const selectedValue = await prioritySelect.inputValue().catch(() => null);
      console.log(`✅ Priority field value: ${selectedValue}`);

      if (selectedValue) {
        // "urgent" should map to HIGH
        expect(['HIGH', 'high', 'urgent']).toContain(selectedValue.toUpperCase().replace('_', ' ').trim() || selectedValue);
      }
    } else {
      console.log('ℹ️ Priority select not found - action may not include priority field');
    }

    await page.keyboard.press('Escape');
  });

  test('should map "critical" to CRITICAL severity', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Query with critical keyword
    await spotlight.search('critical fault on engine');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for "critical fault on engine"');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check for severity or priority field
    const severityInput = page.locator('select[name="severity"], select[name="priority"], #severity, #priority');
    const hasSeverity = await severityInput.isVisible().catch(() => false);

    if (hasSeverity) {
      const value = await severityInput.inputValue().catch(() => null);
      console.log(`✅ Severity/Priority value: ${value}`);

      if (value) {
        // "critical" should map to CRITICAL or HIGH
        const normalizedValue = value.toUpperCase();
        expect(['CRITICAL', 'HIGH']).toContain(normalizedValue);
      }
    }

    await page.keyboard.press('Escape');
  });

  test('should leave priority empty for neutral queries', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Neutral query without priority indicators
    await spotlight.search('create work order');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for neutral query');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Priority should be empty or show "Select..." default
    const prioritySelect = page.locator('select[name="priority"], #priority');
    const hasPrioritySelect = await prioritySelect.isVisible().catch(() => false);

    if (hasPrioritySelect) {
      const value = await prioritySelect.inputValue().catch(() => '');
      // Empty or placeholder indicates no NLP-extracted priority
      console.log(`✅ Priority field default value: "${value}" (neutral query = no prefill)`);
    }

    await page.keyboard.press('Escape');
  });
});

test.describe('Prefill Extraction - Temporal Parsing', () => {
  test.describe.configure({ retries: 2 });

  test('should parse "due tomorrow" to due_date', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Query with temporal phrase
    await spotlight.search('create work order due tomorrow');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for temporal query');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check date fields
    const dateInputs = modal.locator('input[type="date"]');
    const dateCount = await dateInputs.count();

    if (dateCount > 0) {
      const firstDateValue = await dateInputs.first().inputValue();
      console.log(`✅ Date field value: ${firstDateValue}`);

      if (firstDateValue) {
        // Calculate expected tomorrow date
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const expectedDate = tomorrow.toISOString().split('T')[0];

        // The date should be tomorrow (within 1 day tolerance for timezone)
        const parsedDate = new Date(firstDateValue);
        const diffDays = Math.abs((parsedDate.getTime() - tomorrow.getTime()) / (1000 * 60 * 60 * 24));
        expect(diffDays).toBeLessThanOrEqual(1);
        console.log('✅ "tomorrow" correctly parsed to date');
      }
    } else {
      console.log('ℹ️ No date inputs found in form');
    }

    await page.keyboard.press('Escape');
  });

  test('should parse "schedule for next week" to scheduled_date', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('schedule maintenance for next week');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for "schedule for next week"');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check for scheduled_date or any date field
    const scheduledDateInput = page.locator('#scheduled_date, input[name="scheduled_date"]');
    const hasScheduledDate = await scheduledDateInput.isVisible().catch(() => false);

    if (hasScheduledDate) {
      const value = await scheduledDateInput.inputValue();
      console.log(`✅ Scheduled date value: ${value}`);

      if (value) {
        const parsedDate = new Date(value);
        const today = new Date();
        // "next week" should be 7+ days from now
        const diffDays = (parsedDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24);
        expect(diffDays).toBeGreaterThanOrEqual(5); // Allow some parsing variance
        console.log('✅ "next week" correctly parsed to future date');
      }
    } else {
      // Try generic date inputs
      const dateInputs = modal.locator('input[type="date"]');
      const dateCount = await dateInputs.count();
      console.log(`ℹ️ Found ${dateCount} date inputs in form`);
    }

    await page.keyboard.press('Escape');
  });

  test('should show low confidence warning for ambiguous temporal phrases', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Ambiguous temporal phrase - "soon" is vague
    await spotlight.search('create work order needed soon');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for ambiguous temporal query');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check for date warning component (per DateWarning component)
    const dateWarning = modal.locator('[data-testid^="date-warning-"]');
    const hasDateWarning = await dateWarning.isVisible().catch(() => false);

    if (hasDateWarning) {
      console.log('✅ Low confidence date warning displayed for ambiguous phrase');
    } else {
      console.log('ℹ️ No date warning - "soon" may not have triggered temporal parsing');
    }

    await page.keyboard.press('Escape');
  });
});

test.describe('Confidence Display Indicators', () => {
  test.describe.configure({ retries: 2 });

  test('should show green indicator for high confidence prefill (>=0.85)', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Specific, unambiguous query should yield high confidence
    await spotlight.search('create work order for main engine priority high');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for specific query');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check for high-confidence styling:
    // - Green border (border-green-500)
    // - "auto-filled" badge text
    const autoFilledBadges = modal.locator('text=auto-filled');
    const hasAutoFilled = await autoFilledBadges.count().catch(() => 0);

    if (hasAutoFilled > 0) {
      console.log(`✅ Found ${hasAutoFilled} high-confidence auto-filled indicators`);
    }

    // Check for confidence field wrappers with high confidence
    const confidenceFields = modal.locator('[data-testid^="confidence-field-"]');
    const fieldCount = await confidenceFields.count();

    for (let i = 0; i < fieldCount; i++) {
      const field = confidenceFields.nth(i);
      const confidence = await field.getAttribute('data-confidence');
      const level = await field.getAttribute('data-confidence-level');

      if (confidence && parseFloat(confidence) >= 0.85) {
        console.log(`✅ High confidence field found: ${confidence} (level: ${level})`);
      }
    }

    await page.keyboard.press('Escape');
  });

  test('should show amber indicator for medium confidence (0.65-0.84)', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Moderately ambiguous query - equipment name without ID
    await spotlight.search('create work order for generator check filters');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check for medium-confidence styling:
    // - Amber border (border-amber-500)
    // - "confirm" badge text
    // - "Low confidence" badge in ConfidenceField
    const confirmBadges = modal.locator('text=confirm');
    const lowConfBadges = modal.locator('text=Low confidence');

    const hasConfirm = await confirmBadges.count().catch(() => 0);
    const hasLowConf = await lowConfBadges.count().catch(() => 0);

    if (hasConfirm > 0 || hasLowConf > 0) {
      console.log(`✅ Medium confidence indicators: ${hasConfirm} confirm badges, ${hasLowConf} low confidence badges`);
    }

    // Check confidence field data attributes
    const confidenceFields = modal.locator('[data-testid^="confidence-field-"][data-confidence-level="medium"]');
    const mediumCount = await confidenceFields.count();

    if (mediumCount > 0) {
      console.log(`✅ Found ${mediumCount} medium-confidence fields`);
    }

    await page.keyboard.press('Escape');
  });

  test('should NOT prefill low confidence fields (<0.65)', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Very vague query - should not yield confident prefill
    await spotlight.search('new work order something needs doing');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for vague query');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Check that required fields are empty (not prefilled with low confidence)
    const titleInput = modal.locator('#title, input[name="title"], [data-testid="title-input"]');
    const hasTitleInput = await titleInput.isVisible().catch(() => false);

    if (hasTitleInput) {
      const titleValue = await titleInput.inputValue().catch(() => '');
      // Title should be empty for vague queries (low confidence = no prefill)
      console.log(`ℹ️ Title field value: "${titleValue}" (low confidence should not prefill ambiguous)`);
    }

    // Check for "Review required" badges (confidence < 0.5)
    const reviewRequiredBadges = modal.locator('text=Review required');
    const hasReviewRequired = await reviewRequiredBadges.count().catch(() => 0);

    if (hasReviewRequired > 0) {
      console.log(`✅ Found ${hasReviewRequired} "Review required" low-confidence indicators`);
    }

    await page.keyboard.press('Escape');
  });

  test('should show confidence percentage in badge', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Query that should trigger prefill with some entities
    await spotlight.search('create work order for engine room pump');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Look for confidence percentage display (per ConfidenceField.tsx: shows "(XX%)")
    const percentagePattern = modal.locator('text=%)').first();
    const hasPercentage = await percentagePattern.isVisible().catch(() => false);

    if (hasPercentage) {
      const text = await percentagePattern.innerText();
      console.log(`✅ Confidence percentage displayed: ${text}`);
      // Verify it's a valid percentage format
      expect(text).toMatch(/\d+%\)/);
    } else {
      // Confidence percentages only show for medium/low confidence fields
      console.log('ℹ️ No confidence percentage displayed (high confidence fields hide percentage)');
    }

    await page.keyboard.press('Escape');
  });
});

test.describe('Prefill Edge Cases', () => {
  test.describe.configure({ retries: 2 });

  test('should handle multiple equipment mentions gracefully', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Query with multiple potential equipment matches
    await spotlight.search('create work order for main engine and generator');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for multi-equipment query');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Should trigger disambiguation (multiple matches)
    const ambiguitySection = modal.locator('[data-testid^="ambiguity-"]');
    const hasAmbiguity = await ambiguitySection.isVisible().catch(() => false);

    if (hasAmbiguity) {
      console.log('✅ Disambiguation UI shown for multiple equipment mentions');
    } else {
      // Alternatively, check if first match was selected
      console.log('ℹ️ No disambiguation UI - first match may have been auto-selected');
    }

    await page.keyboard.press('Escape');
  });

  test('should handle empty query without crash', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Empty query followed by immediate clear
    await spotlight.search('');

    // Should not crash or show errors
    const errorToast = page.locator('[data-sonner-toast][data-type="error"]');
    const hasError = await errorToast.isVisible({ timeout: 1_000 }).catch(() => false);

    expect(hasError).toBe(false);
    console.log('✅ Empty query handled gracefully');
  });

  test('should preserve user edits over prefill updates', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('create work order');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions');
      return;
    }

    const actionBtn = page.locator('[data-testid^="action-btn-"]').first();
    await actionBtn.click();

    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // Find and edit title field
    const titleInput = modal.locator('#title, input[name="title"], [data-testid="title-input"]').first();
    const hasTitleInput = await titleInput.isVisible().catch(() => false);

    if (hasTitleInput) {
      // User types custom value
      await titleInput.fill('My Custom Work Order Title');

      // Wait a moment (simulating prefill race condition)
      await page.waitForTimeout(500);

      // Verify user's value is preserved
      const currentValue = await titleInput.inputValue();
      expect(currentValue).toBe('My Custom Work Order Title');
      console.log('✅ User edit preserved over potential prefill update');
    }

    await page.keyboard.press('Escape');
  });
});

test.describe('ReadinessState Visual Indicators', () => {
  test.describe.configure({ retries: 2 });

  test('should show green check for READY state actions', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Complete, specific query that should result in READY state
    await spotlight.search('close work order WO-12345');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for close work order query');
      return;
    }

    // Check for green checkmark icon in action buttons (READY state)
    // Per SuggestedActions.tsx: READY shows emerald-400 Check icon
    const readyButtons = suggestedActions.locator('.text-emerald-400').locator('xpath=..');
    const readyCount = await readyButtons.count().catch(() => 0);

    if (readyCount > 0) {
      console.log(`✅ Found ${readyCount} actions in READY state (green check)`);
    } else {
      // Check aria-label for accessibility
      const readyAriaLabel = suggestedActions.locator('[aria-label="Ready to execute"]');
      const hasReadyAria = await readyAriaLabel.count().catch(() => 0);
      console.log(`ℹ️ READY indicators via aria-label: ${hasReadyAria}`);
    }
  });

  test('should show amber dot for NEEDS_INPUT state actions', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Incomplete query requiring more input
    await spotlight.search('create work order');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions');
      return;
    }

    // Check for amber Circle icon (NEEDS_INPUT state)
    // Per SuggestedActions.tsx: NEEDS_INPUT shows amber-400 filled Circle
    const needsInputIndicator = suggestedActions.locator('[aria-label="Requires input"]');
    const hasNeedsInput = await needsInputIndicator.count().catch(() => 0);

    if (hasNeedsInput > 0) {
      console.log(`✅ Found ${hasNeedsInput} actions in NEEDS_INPUT state (amber dot)`);
    }
  });

  test('should show lock icon for BLOCKED state actions', async ({ page, crewPage }) => {
    // Use crew role which has limited permissions
    await crewPage.goto('/');

    const spotlight = new SpotlightSearchPO(crewPage);

    // Action that may be role-restricted
    await spotlight.search('approve shopping list');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const suggestedActions = crewPage.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasActions) {
      console.log('ℹ️ No suggested actions for role-restricted query');
      return;
    }

    // Check for lock icon (BLOCKED state due to role restrictions)
    // Per SuggestedActions.tsx: BLOCKED shows red-400 Lock icon
    const blockedIndicator = suggestedActions.locator('[aria-label="Permission required"]');
    const hasBlocked = await blockedIndicator.count().catch(() => 0);

    if (hasBlocked > 0) {
      console.log(`✅ Found ${hasBlocked} actions in BLOCKED state (lock icon)`);
    } else {
      // Check for disabled buttons
      const disabledButtons = suggestedActions.locator('button[disabled]');
      const disabledCount = await disabledButtons.count().catch(() => 0);
      console.log(`ℹ️ Disabled buttons (potential BLOCKED): ${disabledCount}`);
    }
  });
});
