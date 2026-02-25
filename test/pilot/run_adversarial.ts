#!/usr/bin/env node
/**
 * Adversarial Test Runner: Human Chaos Validation
 *
 * Tests F1 search resilience against:
 * 1. Severe misspellings (trigram territory)
 * 2. Semantic descriptions (vector territory)
 * 3. Wrong name, right idea (both signals)
 *
 * Key Output: Which signal (trigram vs vector) contributed most to each match.
 *
 * THE PHYSICS:
 * - Trigram (pg_trgm): Bridges lexical distance via character n-gram overlap
 * - Vector (1536-d): Bridges semantic distance via cosine similarity in embedding space
 * - RRF (K=60): Fuses evidence without weighting bias: 1/(60+rank_trigram) + 1/(60+rank_vector)
 *
 * NO MAGIC. NO BIAS. PURE MATH.
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { createClient } from '@supabase/supabase-js';

// ESM compatibility
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const TRUTH_SET_PATH = path.join(__dirname, 'truthset_adversarial.jsonl');
const SEARCH_ENDPOINT = 'https://pipeline-core.int.celeste7.ai/api/f1/search/stream';
const DELAY_MS = 150; // Slightly longer delay for adversarial tests

// Supabase configuration
const MASTER_SUPABASE_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw';

// Test user credentials
const TEST_USER_EMAIL = 'crew.test@alex-short.com';
const TEST_USER_PASSWORD = 'Password2!';

// Map truth set entity_type to database object_type(s)
const ENTITY_TO_DB_TYPES: Record<string, string[]> = {
  'certificate': ['certificate'],
  'document': ['document'],
  'fault': ['fault'],
  'inventory': ['inventory', 'part'],
  'part': ['part', 'inventory'],
  'receiving': ['receiving'],
  'shopping_list': ['shopping_item'],
  'work_order_note': ['work_order_note'],
  'work_order': ['work_order']
};

interface AdversarialItem {
  title: string;
  adversarial_category: 'severe_misspelling' | 'semantic_description' | 'wrong_name_right_idea';
  canonical: {
    target_type: string;
    target_id: string;
  };
  queries: Array<{
    query: string;
    intent_type: string;
    expected_signal: 'trigram' | 'vector' | 'both';
    expected_target_id: string;
  }>;
}

interface SearchResultItem {
  id: string;
  object_type: string;
  fused_score: number;
  ranks: {
    trigram?: number;
    semantic?: number;
    fts?: number;
    popularity?: number;
  };
  components?: {
    trigram?: number;
    semantic?: number;
    fts?: number;
  };
}

interface SignalAttribution {
  winning_signal: 'trigram' | 'vector' | 'fts' | 'tie' | 'unknown';
  trigram_rank: number | null;
  vector_rank: number | null;
  fts_rank: number | null;
  trigram_score: number | null;
  vector_score: number | null;
  fts_score: number | null;
  analysis: string;
}

interface TestResult {
  title: string;
  category: string;
  query: string;
  expected_signal: string;
  expected_id: string;
  hit: boolean;
  hit_rank: number | null;
  latency_ms: number;
  attribution: SignalAttribution | null;
  error?: string;
}

// Global auth state
let authToken: string | null = null;

// Authenticate with Supabase
async function authenticate(): Promise<string> {
  console.log('Authenticating with Supabase...');

  const supabase = createClient(MASTER_SUPABASE_URL, MASTER_SUPABASE_ANON_KEY);

  const { data, error } = await supabase.auth.signInWithPassword({
    email: TEST_USER_EMAIL,
    password: TEST_USER_PASSWORD,
  });

  if (error || !data.session) {
    throw new Error(`Authentication failed: ${error?.message || 'No session'}`);
  }

  console.log(`Authentication successful: ${TEST_USER_EMAIL}\n`);
  return data.session.access_token;
}

// Sleep utility
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Parse SSE stream and extract results with full ranking data
async function parseSSEStream(response: Response): Promise<SearchResultItem[]> {
  const results: SearchResultItem[] = [];

  if (!response.body) {
    return results;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.substring(5).trim();
          if (jsonStr && jsonStr !== '[DONE]') {
            try {
              const event = JSON.parse(jsonStr);

              // F1 streaming sends result_batch events with items array
              if (event.items && Array.isArray(event.items)) {
                for (const item of event.items) {
                  if (item.object_id && item.object_type) {
                    results.push({
                      id: item.object_id,
                      object_type: item.object_type,
                      fused_score: item.fused_score || 0,
                      ranks: item.ranks || {},
                      components: item.components || {},
                    });
                  }
                }
              }

              // Also handle exact_match_win events
              if (event.object_id && event.object_type && !event.items) {
                results.push({
                  id: event.object_id,
                  object_type: event.object_type,
                  fused_score: event.fused_score || 0,
                  ranks: event.ranks || {},
                  components: event.components || {},
                });
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  return results;
}

// Analyze which signal contributed most to a match
function analyzeSignalAttribution(result: SearchResultItem): SignalAttribution {
  const ranks = result.ranks || {};
  const components = result.components || {};

  const trigramRank = ranks.trigram ?? null;
  const vectorRank = ranks.semantic ?? null;
  const ftsRank = ranks.fts ?? null;

  const trigramScore = components.trigram ?? null;
  const vectorScore = components.semantic ?? null;
  const ftsScore = components.fts ?? null;

  // Determine winning signal based on rank (lower is better)
  let winningSignal: 'trigram' | 'vector' | 'fts' | 'tie' | 'unknown' = 'unknown';
  let analysis = '';

  // Filter out null ranks
  const validRanks: Array<{ name: 'trigram' | 'vector' | 'fts'; rank: number }> = [];
  if (trigramRank !== null) validRanks.push({ name: 'trigram', rank: trigramRank });
  if (vectorRank !== null) validRanks.push({ name: 'vector', rank: vectorRank });
  if (ftsRank !== null) validRanks.push({ name: 'fts', rank: ftsRank });

  if (validRanks.length === 0) {
    winningSignal = 'unknown';
    analysis = 'No ranking signals available';
  } else {
    // Sort by rank (ascending - lower is better)
    validRanks.sort((a, b) => a.rank - b.rank);

    if (validRanks.length >= 2 && validRanks[0].rank === validRanks[1].rank) {
      winningSignal = 'tie';
      analysis = `TIE: ${validRanks[0].name} and ${validRanks[1].name} both ranked ${validRanks[0].rank}`;
    } else {
      winningSignal = validRanks[0].name;
      const scoreStr = winningSignal === 'trigram' ? trigramScore?.toFixed(3) :
                       winningSignal === 'vector' ? vectorScore?.toFixed(3) :
                       ftsScore?.toFixed(3);
      analysis = `${winningSignal.toUpperCase()} won with rank ${validRanks[0].rank}` +
                 (scoreStr ? ` (score: ${scoreStr})` : '');
    }
  }

  return {
    winning_signal: winningSignal,
    trigram_rank: trigramRank,
    vector_rank: vectorRank,
    fts_rank: ftsRank,
    trigram_score: trigramScore,
    vector_score: vectorScore,
    fts_score: ftsScore,
    analysis,
  };
}

// Call F1 search streaming endpoint
async function searchQuery(query: string): Promise<{ results: SearchResultItem[]; latency_ms: number }> {
  const startTime = Date.now();

  if (!authToken) {
    throw new Error('Not authenticated');
  }

  try {
    const params = new URLSearchParams({ q: query });
    const url = `${SEARCH_ENDPOINT}?${params.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Accept': 'text/event-stream',
      },
    });

    const latency_ms = Date.now() - startTime;

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
    }

    const results = await parseSSEStream(response);
    return { results, latency_ms };
  } catch (error) {
    const latency_ms = Date.now() - startTime;
    throw { error: error instanceof Error ? error.message : String(error), latency_ms };
  }
}

// Load adversarial truth set
function loadAdversarialItems(): AdversarialItem[] {
  if (!fs.existsSync(TRUTH_SET_PATH)) {
    throw new Error(`Adversarial truth set not found: ${TRUTH_SET_PATH}`);
  }

  const lines = fs.readFileSync(TRUTH_SET_PATH, 'utf-8').trim().split('\n');
  return lines.map((line, i) => {
    try {
      return JSON.parse(line);
    } catch {
      throw new Error(`Failed to parse line ${i + 1} in adversarial truth set`);
    }
  });
}

// Display results summary
function displayResults(results: TestResult[]): void {
  const categories = {
    severe_misspelling: { hits: 0, total: 0, trigram_wins: 0, vector_wins: 0 },
    semantic_description: { hits: 0, total: 0, trigram_wins: 0, vector_wins: 0 },
    wrong_name_right_idea: { hits: 0, total: 0, trigram_wins: 0, vector_wins: 0 },
  };

  for (const result of results) {
    const cat = categories[result.category as keyof typeof categories];
    if (cat) {
      cat.total++;
      if (result.hit) {
        cat.hits++;
        if (result.attribution?.winning_signal === 'trigram') cat.trigram_wins++;
        if (result.attribution?.winning_signal === 'vector') cat.vector_wins++;
      }
    }
  }

  const totalHits = results.filter(r => r.hit).length;
  const totalQueries = results.length;
  const recall = ((totalHits / totalQueries) * 100).toFixed(2);
  const avgLatency = results.reduce((sum, r) => sum + r.latency_ms, 0) / totalQueries;

  console.log('\n' + '='.repeat(80));
  console.log('ADVERSARIAL TEST RESULTS - F1 Cortex Human Chaos Validation');
  console.log('='.repeat(80));
  console.log(`\nOverall Recall@3: ${recall}% (${totalHits}/${totalQueries} hits)`);
  console.log(`Average Latency: ${avgLatency.toFixed(0)}ms`);

  console.log('\n' + '-'.repeat(80));
  console.log('BREAKDOWN BY ADVERSARIAL CATEGORY');
  console.log('-'.repeat(80));

  console.log('\n1. SEVERE MISSPELLINGS (Testing Trigram Resilience)');
  console.log(`   Recall: ${categories.severe_misspelling.total > 0 ?
    ((categories.severe_misspelling.hits / categories.severe_misspelling.total) * 100).toFixed(1) : 0}% ` +
    `(${categories.severe_misspelling.hits}/${categories.severe_misspelling.total})`);
  console.log(`   Trigram Wins: ${categories.severe_misspelling.trigram_wins}`);
  console.log(`   Vector Wins: ${categories.severe_misspelling.vector_wins}`);
  console.log(`   Expected: Trigram should dominate (lexical distance bridging)`);

  console.log('\n2. SEMANTIC DESCRIPTIONS (Testing Vector Resilience)');
  console.log(`   Recall: ${categories.semantic_description.total > 0 ?
    ((categories.semantic_description.hits / categories.semantic_description.total) * 100).toFixed(1) : 0}% ` +
    `(${categories.semantic_description.hits}/${categories.semantic_description.total})`);
  console.log(`   Trigram Wins: ${categories.semantic_description.trigram_wins}`);
  console.log(`   Vector Wins: ${categories.semantic_description.vector_wins}`);
  console.log(`   Expected: Vector should dominate (semantic proximity in 1536-d space)`);

  console.log('\n3. WRONG NAME, RIGHT IDEA (Testing RRF Fusion)');
  console.log(`   Recall: ${categories.wrong_name_right_idea.total > 0 ?
    ((categories.wrong_name_right_idea.hits / categories.wrong_name_right_idea.total) * 100).toFixed(1) : 0}% ` +
    `(${categories.wrong_name_right_idea.hits}/${categories.wrong_name_right_idea.total})`);
  console.log(`   Trigram Wins: ${categories.wrong_name_right_idea.trigram_wins}`);
  console.log(`   Vector Wins: ${categories.wrong_name_right_idea.vector_wins}`);
  console.log(`   Expected: Mixed - RRF fusion should combine both signals`);

  console.log('\n' + '-'.repeat(80));
  console.log('SIGNAL ATTRIBUTION ANALYSIS');
  console.log('-'.repeat(80));

  // Show individual results with signal attribution
  for (const result of results) {
    const status = result.hit ? 'HIT' : 'MISS';
    const statusIcon = result.hit ? '.' : '!';

    console.log(`\n[${statusIcon}] ${result.title}`);
    console.log(`    Category: ${result.category}`);
    console.log(`    Query: "${result.query}"`);
    console.log(`    Expected Signal: ${result.expected_signal.toUpperCase()}`);
    console.log(`    Status: ${status}${result.hit_rank !== null ? ` (rank ${result.hit_rank})` : ''}`);

    if (result.attribution) {
      console.log(`    Attribution: ${result.attribution.analysis}`);
      if (result.attribution.trigram_rank !== null) {
        console.log(`      - Trigram: rank ${result.attribution.trigram_rank}` +
          (result.attribution.trigram_score !== null ? ` (score: ${result.attribution.trigram_score.toFixed(3)})` : ''));
      }
      if (result.attribution.vector_rank !== null) {
        console.log(`      - Vector: rank ${result.attribution.vector_rank}` +
          (result.attribution.vector_score !== null ? ` (score: ${result.attribution.vector_score.toFixed(3)})` : ''));
      }
      if (result.attribution.fts_rank !== null) {
        console.log(`      - FTS: rank ${result.attribution.fts_rank}` +
          (result.attribution.fts_score !== null ? ` (score: ${result.attribution.fts_score.toFixed(3)})` : ''));
      }
    }

    if (result.error) {
      console.log(`    Error: ${result.error}`);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log('F1 CORTEX ADVERSARIAL VALIDATION COMPLETE');
  console.log('='.repeat(80));
  console.log('\nKey Findings:');

  // Analyze if signals matched expectations
  const misspellingTrigramRate = categories.severe_misspelling.hits > 0 ?
    categories.severe_misspelling.trigram_wins / categories.severe_misspelling.hits : 0;
  const semanticVectorRate = categories.semantic_description.hits > 0 ?
    categories.semantic_description.vector_wins / categories.semantic_description.hits : 0;

  if (misspellingTrigramRate >= 0.6) {
    console.log('  Trigram correctly bridges lexical distance for misspellings');
  } else {
    console.log('  WARNING: Trigram underperforming on misspellings');
  }

  if (semanticVectorRate >= 0.6) {
    console.log('  Vector correctly bridges semantic distance for descriptions');
  } else {
    console.log('  WARNING: Vector underperforming on semantic descriptions');
  }

  if (parseFloat(recall) >= 50) {
    console.log('  RRF fusion is handling human chaos gracefully');
  } else {
    console.log('  ALERT: Human chaos resilience below threshold - review required');
  }

  console.log('\nMathematical Truth: Vague Input = Vague Output. We do not fake results.');
}

// Main execution
async function runAdversarialTest(): Promise<void> {
  console.log('='.repeat(80));
  console.log('F1 CORTEX ADVERSARIAL TEST SUITE');
  console.log('Testing Resilience Against Human Chaos');
  console.log('='.repeat(80));
  console.log('\nEndpoint:', SEARCH_ENDPOINT);
  console.log('Truth Set:', TRUTH_SET_PATH);
  console.log('');

  // Authenticate
  try {
    authToken = await authenticate();
  } catch (error) {
    console.error('FATAL: Authentication failed:', error);
    process.exit(1);
  }

  // Load adversarial items
  const items = loadAdversarialItems();
  console.log(`Loaded ${items.length} adversarial test cases\n`);

  const results: TestResult[] = [];
  let completed = 0;
  const total = items.reduce((sum, item) => sum + item.queries.length, 0);

  // Execute tests
  for (const item of items) {
    console.log(`Testing: ${item.title}`);
    console.log(`  Category: ${item.adversarial_category}`);

    for (const queryObj of item.queries) {
      completed++;
      process.stdout.write(`  Query: "${queryObj.query.substring(0, 50)}..." `);

      try {
        const { results: searchResults, latency_ms } = await searchQuery(queryObj.query);

        // Group results by object_type for category-aware Recall@3
        const resultsByCategory: Record<string, SearchResultItem[]> = {};
        for (const result of searchResults) {
          if (!resultsByCategory[result.object_type]) {
            resultsByCategory[result.object_type] = [];
          }
          resultsByCategory[result.object_type].push(result);
        }

        // Check if expected_id is in top 3 of its mapped DB categories
        const dbTypes = ENTITY_TO_DB_TYPES[item.canonical.target_type] || [item.canonical.target_type];
        let categoryResults: SearchResultItem[] = [];
        for (const dbType of dbTypes) {
          categoryResults = categoryResults.concat(resultsByCategory[dbType] || []);
        }

        const top3 = categoryResults.slice(0, 3);
        const hitIndex = top3.findIndex(r => r.id === queryObj.expected_target_id);
        const hit = hitIndex !== -1;
        const hitResult = hit ? top3[hitIndex] : (searchResults.find(r => r.id === queryObj.expected_target_id) || null);
        const attribution = hitResult ? analyzeSignalAttribution(hitResult) : null;

        results.push({
          title: item.title,
          category: item.adversarial_category,
          query: queryObj.query,
          expected_signal: queryObj.expected_signal,
          expected_id: queryObj.expected_target_id,
          hit,
          hit_rank: hit ? hitIndex + 1 : null,
          latency_ms,
          attribution,
        });

        console.log(`${hit ? 'HIT' : 'MISS'} ${latency_ms}ms [${completed}/${total}]`);
      } catch (err: any) {
        results.push({
          title: item.title,
          category: item.adversarial_category,
          query: queryObj.query,
          expected_signal: queryObj.expected_signal,
          expected_id: queryObj.expected_target_id,
          hit: false,
          hit_rank: null,
          latency_ms: err.latency_ms || 0,
          attribution: null,
          error: err.error || String(err),
        });

        console.log(`ERROR: ${err.error || err} [${completed}/${total}]`);
      }

      // Delay between requests
      if (completed < total) {
        await sleep(DELAY_MS);
      }
    }
    console.log('');
  }

  // Display results
  displayResults(results);

  // Save results
  const outputPath = path.join(__dirname, 'adversarial_results.json');
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to: ${outputPath}`);
}

// Run the test
runAdversarialTest().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
