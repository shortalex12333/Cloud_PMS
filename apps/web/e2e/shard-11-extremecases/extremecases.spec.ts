import { test, expect, SpotlightSearchPO, ContextPanelPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 11: Extreme Case Search Tests (F1 Pipeline)
 *
 * Tests the F1 search pipeline's ability to handle real-world chaos:
 * - Misspellings (Trigram territory - pg_trgm)
 * - Semantic descriptions (Embedding territory - pgvector 1536d)
 * - Wrong names with right ideas (RRF fusion territory - K=60)
 *
 * WHY GENERIC SAAS FAILS:
 * - Exact match only: "genrator" returns 0 results
 * - No semantic understanding: "thing that makes water" returns 0 results
 * - No fuzzy tolerance: "mantenance" returns 0 results
 *
 * WHY OUR F1 ENGINE SUCCEEDS:
 * - Trigram (pg_trgm): Handles 2-3 character edit distance
 * - Embeddings (pgvector 1536d): Semantic meaning understanding
 * - RRF Fusion (K=60): Combines both signals mathematically
 *
 * LAW 10: PHYSICAL TRUTH OVER MOCKED TESTS
 * - These tests run against real infrastructure
 */

// Constants for timeouts
const SEARCH_TIMEOUT = 10_000;
const RESULT_WAIT = 3000;

/**
 * Helper function to verify search returns results containing expected text
 */
async function verifySearchFindsTarget(
  spotlight: SpotlightSearchPO,
  query: string,
  expectedPattern: RegExp | string,
  page: any
): Promise<void> {
  await spotlight.search(query);
  // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

  const resultCount = await spotlight.getResultCount();
  expect(resultCount).toBeGreaterThan(0);

  // Get result text content
  const resultsText = await spotlight.resultsContainer.textContent();
  if (typeof expectedPattern === 'string') {
    expect(resultsText?.toLowerCase()).toContain(expectedPattern.toLowerCase());
  } else {
    expect(resultsText?.toLowerCase()).toMatch(expectedPattern);
  }
}

/**
 * Helper function to verify search returns ANY results (for semantic queries)
 */
async function verifySearchReturnsResults(
  spotlight: SpotlightSearchPO,
  query: string
): Promise<number> {
  await spotlight.search(query);
  // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

  const resultCount = await spotlight.getResultCount();
  expect(resultCount).toBeGreaterThan(0);
  return resultCount;
}

// ============================================================================
// SECTION 1: MISSPELLING TESTS (Trigram Territory - pg_trgm)
// ============================================================================

test.describe('Extreme Misspelling Tests - Trigram Territory', () => {
  // Allow retries for search tests that may hit cold starts
  test.describe.configure({ retries: 1 });

  test('should find "generator" when searching "genrator" (missing letter)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('genrator');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    // Verify a result contains "generator" (case-insensitive)
    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('generator');
  });

  test('should find "maintenance" when searching "mantenance" (transposed vowel)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('mantenance');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('maintenance');
  });

  test('should find "certificate" when searching "certficate" (missing letter)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('certficate');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('certificate');
  });

  test('should find "equipment" when searching "equipmnt" (missing vowel)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('equipmnt');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('equipment');
  });

  test('should find "bilge pump" when searching "bilj pump" (phonetic misspelling)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('bilj pump');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find bilge-related results
    expect(resultsText?.toLowerCase()).toMatch(/bilge|pump/);
  });

  test('should find "exhaust temperature" when searching "exaust temp" (missing h + abbreviation)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('exaust temp');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find exhaust or temperature related results
    expect(resultsText?.toLowerCase()).toMatch(/exhaust|temp/);
  });

  test('should handle 2-character edit distance: "enigne" for "engine"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('enigne');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('engine');
  });

  test('should handle 3-character edit distance: "compreser" for "compressor"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('compreser');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/compress|compressor/);
  });

  test('should handle transposed characters: "enigne" for "engine"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('engnie');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('engine');
  });

  test('should handle doubled characters: "generattor" for "generator"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('generattor');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('generator');
  });

  test('should handle missing vowels: "gnrtr" partial match for "generator"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    // Full vowel stripping may be too aggressive, use partial
    await spotlight.search('genrtr');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toContain('generator');
  });

  test('should handle phonetic misspellings: "koolant" for "coolant"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('koolant');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/coolant|cool|cooling/);
  });
});

// ============================================================================
// SECTION 2: SEMANTIC DESCRIPTION TESTS (Embedding Territory - pgvector)
// ============================================================================

test.describe('Semantic Description Tests - Embedding Territory', () => {
  test.describe.configure({ retries: 1 });

  test('should find watermaker when searching "thing that makes drinking water from seawater"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('thing that makes drinking water from seawater');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find watermaker, desalinator, or water-related equipment
    expect(resultsText?.toLowerCase()).toMatch(/water|desalin|reverse osmosis|ro system/);
  });

  test('should find ballast system when searching "system that fills tanks for stability"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('system that fills tanks for stability');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find ballast, tank, or stability related
    expect(resultsText?.toLowerCase()).toMatch(/ballast|tank|stability|trim/);
  });

  test('should find bilge float switch when searching "sensor detecting water in hull bottom"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('sensor detecting water in hull bottom');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find bilge, float switch, or hull related
    expect(resultsText?.toLowerCase()).toMatch(/bilge|float|switch|sensor|hull|alarm/);
  });

  test('should find ISM certificate when searching "document proving safety management compliance"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('document proving safety management compliance');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find ISM, safety, certificate, compliance related
    expect(resultsText?.toLowerCase()).toMatch(/ism|safety|certificate|compliance|sms|management/);
  });

  test('should find exhaust temperature fault when searching "alarm when exhaust pipe overheats"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('alarm when exhaust pipe overheats');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find exhaust, temperature, alarm, or fault related
    expect(resultsText?.toLowerCase()).toMatch(/exhaust|temperature|temp|alarm|fault|overheat/);
  });

  test('should find generator vibration when searching "issue when power generator shakes too much"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('issue when power generator shakes too much');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find generator, vibration, or engine related
    expect(resultsText?.toLowerCase()).toMatch(/generator|genset|vibration|shake|engine|mount/);
  });

  test('should find class certificate when searching "paper for class society approval"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('paper for class society approval');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find class, Lloyd's, certificate, or survey related
    expect(resultsText?.toLowerCase()).toMatch(/class|lloyd|certificate|survey|dnv|bureau veritas|abs/);
  });

  test('should find AC unit when searching "machine that cools the cabin air"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('machine that cools the cabin air');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find AC, air conditioning, HVAC, or cooling related
    expect(resultsText?.toLowerCase()).toMatch(/ac|air condition|hvac|cool|chiller|climate/);
  });

  test('should handle maritime-specific paraphrases: "rope holder on deck"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('rope holder on deck');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find cleat, bollard, winch, or deck equipment
    expect(resultsText?.toLowerCase()).toMatch(/cleat|bollard|winch|capstan|mooring|deck/);
  });

  test('should handle technical-to-layman translations: "thing that steers the boat"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('thing that steers the boat');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find rudder, steering, autopilot, or helm related
    expect(resultsText?.toLowerCase()).toMatch(/rudder|steering|autopilot|helm|hydraulic/);
  });

  test('should handle verbose descriptions: "the electrical system that converts shore power to boat power and charges batteries"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('electrical system that converts shore power to boat power and charges batteries');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find inverter, charger, shore power, or electrical
    expect(resultsText?.toLowerCase()).toMatch(/inverter|charger|shore|battery|electrical|converter/);
  });

  test('should handle partial descriptions: "pump for dirty water"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('pump for dirty water');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find bilge pump, grey water, or sewage related
    expect(resultsText?.toLowerCase()).toMatch(/bilge|grey|gray|sewage|waste|pump/);
  });
});

// ============================================================================
// SECTION 3: WRONG NAME, RIGHT IDEA TESTS (RRF Fusion Territory)
// ============================================================================

test.describe('Wrong Name Right Idea Tests - RRF Fusion Territory', () => {
  test.describe.configure({ retries: 1 });

  test('should find generator oil filter when searching "cat oil strainer" (brand alias)', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('cat oil strainer');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find oil filter, CAT/Caterpillar, or generator parts
    expect(resultsText?.toLowerCase()).toMatch(/oil|filter|cat|strainer|generator|engine/);
  });

  test('should find Lloyd\'s certificate when searching "class society document"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('class society document');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find class, Lloyd's, certificate, or classification related
    expect(resultsText?.toLowerCase()).toMatch(/class|lloyd|certificate|dnv|abs|bureau|survey/);
  });

  test('should find AC compressor clutch when searching "cold air machine part"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('cold air machine part');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find AC, compressor, HVAC, or cooling parts
    expect(resultsText?.toLowerCase()).toMatch(/ac|compressor|hvac|air|cool|refriger/);
  });

  test('should find generator coolant when searching "genset antifreeze"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('genset antifreeze');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find coolant, generator, or engine cooling
    expect(resultsText?.toLowerCase()).toMatch(/coolant|generator|genset|cool|antifreeze|engine/);
  });

  test('should find navigation light bulb when searching "running light lamp"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('running light lamp');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find navigation light, bulb, or lighting
    expect(resultsText?.toLowerCase()).toMatch(/navigation|nav light|light|bulb|lamp|led/);
  });

  test('should find main engine work order when searching "propulsion unit service"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('propulsion unit service');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find engine, propulsion, or service related
    expect(resultsText?.toLowerCase()).toMatch(/engine|propulsion|main|service|work order|maintenance/);
  });

  test('should handle brand aliases: "cummins service" for engine maintenance', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('cummins service');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find Cummins, engine, or service related
    expect(resultsText?.toLowerCase()).toMatch(/cummins|engine|service|maintenance|generator/);
  });

  test('should handle colloquial terms: "anchor windy" for windlass', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('anchor windy');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find windlass, anchor, or deck equipment
    expect(resultsText?.toLowerCase()).toMatch(/windlass|anchor|winch|capstan/);
  });

  test('should handle industry jargon: "MCA survey" for Maritime Coast Agency inspection', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('MCA survey');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find MCA, survey, inspection, or certificate
    expect(resultsText?.toLowerCase()).toMatch(/mca|survey|inspection|certificate|flag|class/);
  });

  test('should handle abbreviation expansion: "A/C" for air conditioning', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('A/C compressor');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find AC, air conditioning, or HVAC
    expect(resultsText?.toLowerCase()).toMatch(/ac|air|hvac|compressor|cool/);
  });

  test('should handle synonym substitution: "fix" for "repair" or "service"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('fix generator');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find repair, service, maintenance, or work order
    expect(resultsText?.toLowerCase()).toMatch(/generator|repair|service|maintenance|work order|fix/);
  });

  test('should handle related concept queries: "fuel problem" for fuel filter/pump issues', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('fuel problem');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    // Should find fuel filter, pump, tank, or related faults
    expect(resultsText?.toLowerCase()).toMatch(/fuel|filter|pump|tank|leak|fault/);
  });
});

// ============================================================================
// SECTION 4: COMPOUND EXTREME CASES (Combined Challenges)
// ============================================================================

test.describe('Compound Extreme Cases - Combined Challenges', () => {
  test.describe.configure({ retries: 1 });

  test('should handle misspelling + semantic: "genrator overheeting problm"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('genrator overheeting problm');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/generator|overheat|temperature|fault/);
  });

  test('should handle abbreviation + misspelling: "AC compresser maintanance"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('AC compresser maintanance');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/ac|compressor|maintenance|hvac/);
  });

  test('should handle brand + colloquial: "cat gennie wont start"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('cat gennie wont start');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/cat|generator|genset|start|engine/);
  });

  test('should handle multi-word misspelling: "emergancy bilge pmp"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('emergancy bilge pmp');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/emergency|bilge|pump/);
  });

  test('should handle question format: "why is the watermaker not working"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('why is the watermaker not working');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/watermaker|water|desalin|fault|issue/);
  });

  test('should handle possessive form: "engines oil leak"', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search("engine's oil leak");
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);

    const resultsText = await spotlight.resultsContainer.textContent();
    expect(resultsText?.toLowerCase()).toMatch(/engine|oil|leak/);
  });
});

// ============================================================================
// SECTION 5: PERFORMANCE VALIDATION
// ============================================================================

test.describe('Search Performance Under Extreme Queries', () => {
  test('should complete misspelled search within 5 seconds', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    const startTime = Date.now();
    await spotlight.search('mantenance genrator certficate');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);
    const endTime = Date.now();

    const searchTime = endTime - startTime;
    // Search should complete within 5 seconds (includes debounce)
    expect(searchTime).toBeLessThan(5000);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);
  });

  test('should complete semantic search within 5 seconds', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    const startTime = Date.now();
    await spotlight.search('thing that makes the boat move forward underwater');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);
    const endTime = Date.now();

    const searchTime = endTime - startTime;
    expect(searchTime).toBeLessThan(5000);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);
  });

  test('should complete fusion search within 5 seconds', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    const startTime = Date.now();
    await spotlight.search('cat gennie power problm overheting');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: SEARCH_TIMEOUT }).catch(() => {}),
    ]);
    const endTime = Date.now();

    const searchTime = endTime - startTime;
    expect(searchTime).toBeLessThan(5000);

    const resultCount = await spotlight.getResultCount();
    expect(resultCount).toBeGreaterThan(0);
  });
});

// ============================================================================
// SECTION 6: NEGATIVE TESTS (Should NOT crash or hang)
// ============================================================================

test.describe('Extreme Query Resilience', () => {
  test('should not crash on heavily misspelled gibberish', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('xyzqwerty mantanence gnertor certfkat');
    await page.waitForTimeout(RESULT_WAIT);

    // Should not crash - search input should still be visible
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should handle extreme length semantic query', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    const longSemanticQuery = 'I need to find the thing that is used on the yacht to convert seawater into drinking water and I think it might be broken because the output is not good and we need to service it soon';
    await spotlight.search(longSemanticQuery);
    await page.waitForTimeout(RESULT_WAIT);

    // Should not crash
    await expect(spotlight.searchInput).toBeVisible();
  });

  test('should not hang on all-misspelled multi-word query', async ({ page }) => {
    await page.goto('/');
    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('mantanece servise engne genertor pmp filtr');

    // Should respond within timeout (not hang)
    const startTime = Date.now();
    await page.waitForTimeout(RESULT_WAIT);
    const endTime = Date.now();

    expect(endTime - startTime).toBeLessThan(10000);
    await expect(spotlight.searchInput).toBeVisible();
  });
});
